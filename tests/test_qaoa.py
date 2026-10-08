import networkx as nx
import pytest
from qiskit.circuit import QuantumCircuit

from qopt.classical import brute_force_max_cut, random_sampling
from qopt.graphs import generate_random_graph
from qopt.maxcut import cut_value
from qopt.qaoa import (
    MAX_QAOA_QUBITS,
    build_qaoa_circuit,
    qiskit_to_node_bitstring,
    run_qaoa,
    sample_counts,
)

# Settings small enough to keep the test suite quick on a laptop.
FAST = {"shots": 512, "maxiter": 40}


# ---------- circuit structure ----------

@pytest.mark.parametrize(("n", "density", "p"), [(3, 1.0, 1), (5, 0.5, 2), (6, 0.6, 3)])
def test_circuit_qubits_and_parameters(n: int, density: float, p: int) -> None:
    g = generate_random_graph(n, density, seed=0)
    qc = build_qaoa_circuit(g, p)
    assert qc.num_qubits == n
    assert qc.num_clbits == n
    assert qc.num_parameters == 2 * p  # one gamma and one beta per layer
    ops = qc.count_ops()
    assert ops["h"] == n
    assert ops["cx"] == 2 * g.number_of_edges() * p
    assert ops["rz"] == g.number_of_edges() * p
    assert ops["rx"] == n * p


@pytest.mark.parametrize("p", [0, -1, 1.5, True])
def test_bad_depth_rejected(p: object) -> None:
    with pytest.raises(ValueError):
        build_qaoa_circuit(nx.cycle_graph(3), p)  # type: ignore[arg-type]


def test_too_many_qubits_rejected() -> None:
    with pytest.raises(ValueError):
        build_qaoa_circuit(nx.empty_graph(MAX_QAOA_QUBITS + 1), 1)


# ---------- bitstring order ----------

def test_conversion_reverses_qiskit_order() -> None:
    assert qiskit_to_node_bitstring("001") == "100"
    assert qiskit_to_node_bitstring("0111") == "1110"


def test_conversion_on_real_measurement() -> None:
    # Flip only qubit 0. Qiskit reports "001"; our convention must say "100".
    qc = QuantumCircuit(3)
    qc.x(0)
    qc.measure_all()
    counts = sample_counts(qc, shots=50, simulator_seed=0)
    assert counts == {"100": 50}

    # Asymmetric graph (edges 0-1, 0-2) where the order changes the answer:
    # node 0 alone cuts 2 edges; the un-reversed "001" would cut only 1.
    g = nx.Graph([(0, 1), (0, 2)])
    assert cut_value(g, "100") == 2
    assert cut_value(g, "001") == 1


# ---------- full QAOA runs ----------

def test_same_seeds_same_result() -> None:
    g = generate_random_graph(5, 0.6, seed=1)
    opt = brute_force_max_cut(g).cut_value
    a = run_qaoa(g, 1, opt, seed=3, simulator_seed=7, **FAST)
    b = run_qaoa(g, 1, opt, seed=3, simulator_seed=7, **FAST)
    assert a == b  # runtime is excluded from equality


def test_different_seed_changes_result() -> None:
    g = generate_random_graph(5, 0.6, seed=1)
    opt = brute_force_max_cut(g).cut_value
    a = run_qaoa(g, 1, opt, seed=3, simulator_seed=7, **FAST)
    b = run_qaoa(g, 1, opt, seed=4, simulator_seed=8, **FAST)
    assert a != b


def test_measured_cut_values_match_phase1() -> None:
    g = generate_random_graph(6, 0.5, seed=2)
    opt = brute_force_max_cut(g).cut_value
    s = run_qaoa(g, 1, opt, **FAST).samples
    assert sum(s.counts.values()) == s.shots == FAST["shots"]
    assert set(s.cut_values) == set(s.counts)
    for bitstring, cut in s.cut_values.items():
        assert len(bitstring) == 6
        assert cut == cut_value(g, bitstring)
    assert s.best_cut == max(s.cut_values.values()) <= opt
    expected = sum(s.counts[b] * s.cut_values[b] for b in s.counts) / s.shots
    assert s.expected_cut == pytest.approx(expected)
    assert s.expected_ratio == pytest.approx(expected / opt)


def test_result_fields() -> None:
    g = generate_random_graph(5, 0.6, seed=1)
    opt = brute_force_max_cut(g).cut_value
    r = run_qaoa(g, 2, opt, **FAST)
    assert len(r.gammas) == len(r.betas) == 2
    assert r.optimizer == "COBYLA"
    assert 1 <= r.num_evaluations <= FAST["maxiter"] + 1
    assert r.simulator_runtime_s > 0


@pytest.mark.parametrize(("n", "density", "seed"), [(5, 0.6, 0), (6, 0.5, 1), (7, 0.4, 2)])
def test_qaoa_p1_beats_random_sampling_on_expected_cut(
    n: int, density: float, seed: int
) -> None:
    g = generate_random_graph(n, density, seed)
    opt = brute_force_max_cut(g).cut_value
    qaoa = run_qaoa(g, 1, opt, seed=seed, simulator_seed=seed, **FAST)
    rand = random_sampling(g, shots=FAST["shots"], seed=seed, optimal_cut=opt)
    assert qaoa.samples.expected_cut > rand.expected_cut


# ---------- restarts ----------

def test_one_restart_is_the_default() -> None:
    g = generate_random_graph(5, 0.6, seed=1)
    opt = brute_force_max_cut(g).cut_value
    assert run_qaoa(g, 2, opt, num_restarts=1, **FAST) == run_qaoa(g, 2, opt, **FAST)


def test_more_restarts_never_lower_optimizer_score() -> None:
    g = generate_random_graph(7, 0.5, seed=3)
    opt = brute_force_max_cut(g).cut_value
    one = run_qaoa(g, 2, opt, num_restarts=1, **FAST)
    three = run_qaoa(g, 2, opt, num_restarts=3, **FAST)
    # Restart 0 is identical in both runs, so the best of 3 can't score lower.
    assert three.training_expected_cut >= one.training_expected_cut
    assert three.num_restarts == 3
    assert three.num_evaluations > one.num_evaluations


def test_bad_num_restarts_rejected() -> None:
    with pytest.raises(ValueError):
        run_qaoa(nx.cycle_graph(3), 1, 2, num_restarts=0, **FAST)


# ---------- random-sampling baseline ----------

def test_random_sampling_is_seeded_and_consistent() -> None:
    g = generate_random_graph(6, 0.5, seed=0)
    opt = brute_force_max_cut(g).cut_value
    a = random_sampling(g, shots=300, seed=5, optimal_cut=opt)
    assert a == random_sampling(g, shots=300, seed=5, optimal_cut=opt)
    assert a.shots == sum(a.counts.values()) == 300
    # Each edge is cut with probability 1/2, so expect about |E|/2.
    assert a.expected_cut == pytest.approx(g.number_of_edges() / 2, abs=1.0)
    assert a.best_cut <= opt
