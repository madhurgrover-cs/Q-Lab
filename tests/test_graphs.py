import networkx as nx
import pytest

from qopt.graphs import generate_random_graph, validate_graph


def test_same_seed_gives_same_graph() -> None:
    g1 = generate_random_graph(12, 0.4, seed=7)
    g2 = generate_random_graph(12, 0.4, seed=7)
    assert sorted(g1.edges) == sorted(g2.edges)


def test_different_seeds_give_different_graphs() -> None:
    g1 = generate_random_graph(12, 0.4, seed=1)
    g2 = generate_random_graph(12, 0.4, seed=2)
    assert sorted(g1.edges) != sorted(g2.edges)


def test_nodes_are_labelled_from_zero() -> None:
    g = generate_random_graph(8, 0.5, seed=0)
    assert sorted(g.nodes) == list(range(8))
    validate_graph(g)


def test_density_extremes() -> None:
    assert generate_random_graph(6, 0.0, seed=0).number_of_edges() == 0
    assert generate_random_graph(6, 1.0, seed=0).number_of_edges() == 6 * 5 // 2


@pytest.mark.parametrize(
    ("num_nodes", "density", "seed", "error"),
    [
        (0, 0.5, 0, ValueError),
        (-3, 0.5, 0, ValueError),
        (5.0, 0.5, 0, TypeError),
        (True, 0.5, 0, TypeError),
        (5, -0.1, 0, ValueError),
        (5, 1.5, 0, ValueError),
        (5, "0.5", 0, TypeError),
        (5, 0.5, -1, ValueError),
        (5, 0.5, None, TypeError),
        (5, 0.5, 1.0, TypeError),
    ],
)
def test_invalid_arguments_rejected(
    num_nodes: object, density: object, seed: object, error: type[Exception]
) -> None:
    with pytest.raises(error):
        generate_random_graph(num_nodes, density, seed)  # type: ignore[arg-type]


def test_validate_graph_rejects_bad_labels_and_types() -> None:
    with pytest.raises(ValueError):
        validate_graph(nx.Graph([(1, 2)]))  # no node 0
    with pytest.raises(ValueError):
        validate_graph(nx.DiGraph([(0, 1)]))
    with pytest.raises(ValueError):
        validate_graph(nx.Graph([(0, 0), (0, 1)]))  # self-loop
    with pytest.raises(ValueError):
        validate_graph(nx.Graph())
