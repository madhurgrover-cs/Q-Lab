import itertools

import networkx as nx
import pytest

from qopt.classical import (
    MAX_BRUTE_FORCE_NODES,
    brute_force_max_cut,
    greedy_max_cut,
    simulated_annealing,
)
from qopt.graphs import generate_random_graph
from qopt.maxcut import cut_value

# Small random graphs shared by several tests: (nodes, density, seed).
RANDOM_CASES = [(n, d, s) for n in (4, 7, 10) for d in (0.3, 0.6) for s in (0, 1, 2)]


def reference_max_cut(graph: nx.Graph) -> int:
    """Deliberately naive, independent check of the brute-force solver."""
    n = graph.number_of_nodes()
    return max(
        cut_value(graph, "".join(bits)) for bits in itertools.product("01", repeat=n)
    )


# ---------- brute force ----------

@pytest.mark.parametrize(
    ("graph", "expected"),
    [
        (nx.cycle_graph(3), 2),  # odd cycle: can't cut every edge
        (nx.cycle_graph(4), 4),  # even cycle is bipartite: cut everything
        (nx.cycle_graph(5), 4),
        (nx.complete_graph(4), 4),  # K_n: floor(n^2 / 4)
        (nx.complete_graph(5), 6),
        (nx.petersen_graph(), 12),
        (nx.empty_graph(3), 0),
        (nx.empty_graph(1), 0),
    ],
)
def test_brute_force_known_optima(graph: nx.Graph, expected: int) -> None:
    result = brute_force_max_cut(graph)
    assert result.cut_value == expected
    assert cut_value(graph, result.bitstring) == expected


@pytest.mark.parametrize(("n", "density", "seed"), RANDOM_CASES)
def test_brute_force_matches_naive_enumeration(n: int, density: float, seed: int) -> None:
    g = generate_random_graph(n, density, seed)
    assert brute_force_max_cut(g).cut_value == reference_max_cut(g)


def test_brute_force_rejects_large_graphs() -> None:
    with pytest.raises(ValueError):
        brute_force_max_cut(nx.empty_graph(MAX_BRUTE_FORCE_NODES + 1))


# ---------- greedy ----------

@pytest.mark.parametrize(("n", "density", "seed"), RANDOM_CASES)
def test_greedy_is_valid_and_bounded(n: int, density: float, seed: int) -> None:
    g = generate_random_graph(n, density, seed)
    result = greedy_max_cut(g)
    assert cut_value(g, result.bitstring) == result.cut_value
    # Guaranteed: at least half of all edges, never more than the optimum.
    assert 2 * result.cut_value >= g.number_of_edges()
    assert result.cut_value <= brute_force_max_cut(g).cut_value


def test_greedy_is_deterministic() -> None:
    g = generate_random_graph(15, 0.5, seed=3)
    assert greedy_max_cut(g) == greedy_max_cut(g)


# ---------- simulated annealing ----------

@pytest.mark.parametrize(("n", "density", "seed"), RANDOM_CASES)
def test_annealing_is_valid_and_bounded(n: int, density: float, seed: int) -> None:
    g = generate_random_graph(n, density, seed)
    result = simulated_annealing(g, seed=seed, num_steps=2_000)
    assert cut_value(g, result.bitstring) == result.cut_value
    assert result.cut_value <= brute_force_max_cut(g).cut_value


def test_annealing_same_seed_same_result() -> None:
    g = generate_random_graph(15, 0.5, seed=3)
    assert simulated_annealing(g, seed=11) == simulated_annealing(g, seed=11)


def test_annealing_finds_optimum_on_small_graphs() -> None:
    # Not a mathematical guarantee, but on 8-node graphs with 5,000 steps
    # SA should reach the optimum; a failure here signals a real bug.
    for seed in range(5):
        g = generate_random_graph(8, 0.5, seed)
        assert simulated_annealing(g, seed=seed, num_steps=5_000).cut_value == (
            brute_force_max_cut(g).cut_value
        )


@pytest.mark.parametrize(
    "kwargs",
    [{"num_steps": 0}, {"initial_temp": 1.0, "final_temp": 2.0}, {"final_temp": 0.0}],
)
def test_annealing_rejects_bad_parameters(kwargs: dict[str, float]) -> None:
    with pytest.raises(ValueError):
        simulated_annealing(nx.cycle_graph(4), seed=0, **kwargs)
