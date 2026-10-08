import networkx as nx
import numpy as np
import pytest
from qiskit.circuit import QuantumCircuit

from qopt.classical import brute_force_max_cut
from qopt.graphs import generate_random_graph
from qopt.noise import (
    NOISE_LEVELS,
    NoiseLevel,
    build_noise_model,
    check_noise_covers_circuit,
    get_noise_level,
)
from qopt.qaoa import build_qaoa_circuit, run_qaoa, sample_counts

FAST = {"shots": 512, "maxiter": 40}
NOISY_LEVELS = ["low", "medium", "high"]


# ---------- levels and lookup ----------

def test_levels_are_explicit_and_ordered() -> None:
    assert list(NOISE_LEVELS) == ["none", "low", "medium", "high"]
    assert NOISE_LEVELS["none"] == NoiseLevel("none", 0.0, 0.0, 0.0)
    levels = list(NOISE_LEVELS.values())
    for weaker, stronger in zip(levels, levels[1:]):
        assert weaker.one_qubit_error < stronger.one_qubit_error
        assert weaker.two_qubit_error < stronger.two_qubit_error
        assert weaker.readout_error < stronger.readout_error


@pytest.mark.parametrize("bad", ["None", "extreme", "", "HIGH"])
def test_invalid_level_name_raises_clear_error(bad: str) -> None:
    with pytest.raises(ValueError, match="unknown noise level"):
        get_noise_level(bad)
    g = nx.cycle_graph(3)
    with pytest.raises(ValueError, match="unknown noise level"):
        run_qaoa(g, 1, 2, noise=bad, **FAST)


def test_invalid_optimization_mode_raises() -> None:
    with pytest.raises(ValueError, match="optimization_mode"):
        run_qaoa(nx.cycle_graph(3), 1, 2, optimization_mode="both", **FAST)  # type: ignore[arg-type]


def test_none_level_builds_no_model() -> None:
    assert build_noise_model(get_noise_level("none")) is None


@pytest.mark.parametrize("rates", [(0.0, 0.01, 0.01), (0.01, 0.0, 0.01), (0.01, 0.01, 1.0)])
def test_noisy_level_with_zero_or_invalid_rate_rejected(rates: tuple[float, float, float]) -> None:
    with pytest.raises(ValueError, match="needs all rates"):
        build_noise_model(NoiseLevel("custom", *rates))


# ---------- noise really attaches to our gates ----------

@pytest.mark.parametrize("name", NOISY_LEVELS)
def test_noise_model_covers_every_qaoa_instruction(name: str) -> None:
    model = build_noise_model(get_noise_level(name))
    assert model is not None
    circuit = build_qaoa_circuit(generate_random_graph(5, 0.6, seed=0), p=2)
    check_noise_covers_circuit(circuit, model)  # raises if anything is missed
    assert {"h", "rz", "rx", "cx", "measure"} <= set(model.noise_instructions)


def test_coverage_check_catches_uncovered_gate() -> None:
    model = build_noise_model(get_noise_level("low"))
    assert model is not None
    qc = QuantumCircuit(1)
    qc.x(0)  # our noise model has no error on "x"
    qc.measure_all()
    with pytest.raises(ValueError, match="no errors"):
        check_noise_covers_circuit(qc, model)


def _deterministic_circuit(gate: str) -> QuantumCircuit:
    """A circuit that, without noise, always measures all zeros and uses ``gate``."""
    qc = QuantumCircuit(2)
    if gate == "h":
        qc.h(0)
        qc.h(0)
    elif gate == "rz":
        qc.rz(0.7, 0)
    elif gate == "rx":
        qc.rx(0.0, 0)
    elif gate == "cx":
        qc.cx(0, 1)
    qc.measure_all()
    return qc


# Large error on the gate under test; a negligible 1e-9 elsewhere (a rate of
# exactly 0 is rejected because Aer would silently drop it).
TINY = 1e-9


@pytest.mark.parametrize(
    ("gate", "level"),
    [
        ("h", NoiseLevel("test", 0.5, TINY, TINY)),
        ("rz", NoiseLevel("test", 0.5, TINY, TINY)),
        ("rx", NoiseLevel("test", 0.5, TINY, TINY)),
        ("cx", NoiseLevel("test", TINY, 0.5, TINY)),
        ("measure", NoiseLevel("test", TINY, TINY, 0.2)),
    ],
)
def test_each_error_actually_changes_outcomes(gate: str, level: NoiseLevel) -> None:
    qc = _deterministic_circuit(gate)
    assert sample_counts(qc, 1000, simulator_seed=1) == {"00": 1000}
    noisy = sample_counts(qc, 1000, simulator_seed=1, noise_model=build_noise_model(level))
    assert noisy.get("00", 0) < 1000  # some shots were corrupted


# ---------- QAOA under noise ----------

def test_none_matches_ideal_phase2_path() -> None:
    g = generate_random_graph(6, 0.5, seed=2)
    opt = brute_force_max_cut(g).cut_value
    ideal = run_qaoa(g, 2, opt, seed=1, simulator_seed=5, **FAST)  # Phase 2 call
    none = run_qaoa(g, 2, opt, seed=1, simulator_seed=5, noise="none", **FAST)
    none_ideal_mode = run_qaoa(
        g, 2, opt, seed=1, simulator_seed=5, noise="none", optimization_mode="ideal", **FAST
    )
    assert none == ideal
    assert (none_ideal_mode.gammas, none_ideal_mode.samples) == (ideal.gammas, ideal.samples)


@pytest.mark.parametrize("name", NOISY_LEVELS)
def test_each_noisy_level_changes_distribution(name: str) -> None:
    g = generate_random_graph(6, 0.5, seed=2)
    opt = brute_force_max_cut(g).cut_value
    # "ideal" mode: identical angles, so any difference comes from noise alone.
    ideal = run_qaoa(g, 1, opt, noise="none", optimization_mode="ideal", **FAST)
    noisy = run_qaoa(g, 1, opt, noise=name, optimization_mode="ideal", **FAST)
    assert (noisy.gammas, noisy.betas) == (ideal.gammas, ideal.betas)
    assert noisy.samples.counts != ideal.samples.counts


def test_expected_cut_does_not_improve_with_noise() -> None:
    g = generate_random_graph(6, 0.5, seed=4)
    opt = brute_force_max_cut(g).cut_value
    seeds = range(5)
    averages = [
        np.mean([
            run_qaoa(g, 1, opt, seed=s, simulator_seed=s, noise=name, **FAST).samples.expected_cut
            for s in seeds
        ])
        for name in NOISE_LEVELS
    ]
    for less_noise, more_noise in zip(averages, averages[1:]):
        assert more_noise <= less_noise
    assert averages[-1] < averages[0]


def test_same_seeds_same_noisy_result() -> None:
    g = generate_random_graph(5, 0.6, seed=1)
    opt = brute_force_max_cut(g).cut_value
    a = run_qaoa(g, 1, opt, seed=2, simulator_seed=3, noise="medium", **FAST)
    b = run_qaoa(g, 1, opt, seed=2, simulator_seed=3, noise="medium", **FAST)
    assert a == b


def test_result_records_noise_and_mode() -> None:
    g = generate_random_graph(5, 0.6, seed=1)
    opt = brute_force_max_cut(g).cut_value
    r = run_qaoa(g, 1, opt, noise="high", optimization_mode="ideal", **FAST)
    assert r.noise == NOISE_LEVELS["high"]
    assert r.noise.two_qubit_error == 0.08
    assert r.optimization_mode == "ideal"
    assert run_qaoa(g, 1, opt, **FAST).optimization_mode == "noisy"  # default
