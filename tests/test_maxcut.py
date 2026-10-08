import networkx as nx
import pytest

from qopt.maxcut import cut_value


def test_triangle_cut_values() -> None:
    triangle = nx.cycle_graph(3)
    assert cut_value(triangle, "000") == 0
    assert cut_value(triangle, "111") == 0
    assert cut_value(triangle, "100") == 2
    assert cut_value(triangle, "010") == 2


def test_square_alternating_cuts_every_edge() -> None:
    square = nx.cycle_graph(4)  # edges 0-1, 1-2, 2-3, 3-0
    assert cut_value(square, "0101") == 4
    assert cut_value(square, "0011") == 2


def test_flipping_all_sides_keeps_cut_value() -> None:
    g = nx.petersen_graph()
    assert cut_value(g, "0110100101") == cut_value(g, "1001011010")


def test_graph_without_edges_has_zero_cut() -> None:
    g = nx.empty_graph(4)
    assert cut_value(g, "0101") == 0


@pytest.mark.parametrize("bad", ["01", "0101", "01a", "0 1"])
def test_bad_bitstrings_rejected(bad: str) -> None:
    with pytest.raises(ValueError):
        cut_value(nx.cycle_graph(3), bad)


def test_non_string_bitstring_rejected() -> None:
    with pytest.raises(TypeError):
        cut_value(nx.cycle_graph(3), [0, 1, 0])  # type: ignore[arg-type]
