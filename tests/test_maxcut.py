import networkx as nx
import pytest

from qopt.maxcut import cut_value, summarize_samples


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


def test_summarize_samples_best_and_expected() -> None:
    triangle = nx.cycle_graph(3)  # optimum is 2
    s = summarize_samples(triangle, {"000": 3, "100": 1}, optimal_cut=2)
    assert s.shots == 4
    assert s.cut_values == {"000": 0, "100": 2}
    assert (s.best_bitstring, s.best_cut, s.best_ratio) == ("100", 2, 1.0)
    # Best is optimal, but the average shot is poor: (3*0 + 1*2) / 4 = 0.5.
    assert s.expected_cut == 0.5
    assert s.expected_ratio == 0.25


def test_summarize_samples_rejects_bad_input() -> None:
    triangle = nx.cycle_graph(3)
    with pytest.raises(ValueError):
        summarize_samples(triangle, {}, optimal_cut=2)
    with pytest.raises(ValueError):
        summarize_samples(triangle, {"100": 1}, optimal_cut=1)  # beats the "optimum"
