"""Max-Cut problem definition: bitstrings and cut values.

Convention used everywhere in this project: ``bitstring[i]`` is the side
('0' or '1') that node i is placed on. An edge is "cut" when its two
endpoints are on different sides.
"""

from dataclasses import dataclass

import networkx as nx

from qopt.graphs import validate_graph


@dataclass(frozen=True)
class MaxCutResult:
    """A solver's answer: the partition it chose and how many edges it cuts."""

    bitstring: str
    cut_value: int


def cut_value(graph: nx.Graph, bitstring: str) -> int:
    """Return the number of edges whose endpoints are on different sides."""
    validate_graph(graph)
    if not isinstance(bitstring, str):
        raise TypeError(f"bitstring must be a str, got {type(bitstring).__name__}")
    if len(bitstring) != graph.number_of_nodes():
        raise ValueError(
            f"bitstring length {len(bitstring)} != number of nodes "
            f"{graph.number_of_nodes()}"
        )
    if set(bitstring) - {"0", "1"}:
        raise ValueError(f"bitstring may only contain '0' and '1', got {bitstring!r}")

    return sum(1 for u, v in graph.edges if bitstring[u] != bitstring[v])


@dataclass(frozen=True)
class SampleStats:
    """Metrics for a method that outputs many sampled bitstrings ("shots").

    ``best_*`` is the single best sample. With enough shots on a small graph
    even random guessing hits the optimum, so ``expected_cut`` (the average
    over all shots) is the fairer measure of how good the distribution is.
    Ratios are relative to ``optimal_cut`` (1.0 = optimal).
    """

    shots: int
    counts: dict[str, int]  # bitstring (Phase 1 convention) -> times sampled
    cut_values: dict[str, int]  # bitstring -> its cut value
    best_bitstring: str
    best_cut: int
    expected_cut: float
    best_ratio: float
    expected_ratio: float


def summarize_samples(
    graph: nx.Graph, counts: dict[str, int], optimal_cut: int
) -> SampleStats:
    """Compute best/expected cut and approximation ratios from sample counts."""
    if not counts or any(c < 1 for c in counts.values()):
        raise ValueError("counts must be non-empty with positive values")
    if optimal_cut < 0:
        raise ValueError(f"optimal_cut must be >= 0, got {optimal_cut}")

    cuts = {b: cut_value(graph, b) for b in counts}
    shots = sum(counts.values())
    # Ties broken by smallest bitstring so results don't depend on dict order.
    best = min(cuts, key=lambda b: (-cuts[b], b))
    expected = sum(counts[b] * cuts[b] for b in counts) / shots
    if cuts[best] > optimal_cut:
        raise ValueError(f"a sample cuts {cuts[best]} > optimal_cut={optimal_cut}")

    def ratio(x: float) -> float:
        return x / optimal_cut if optimal_cut else 1.0

    return SampleStats(
        shots=shots,
        counts=dict(counts),
        cut_values=cuts,
        best_bitstring=best,
        best_cut=cuts[best],
        expected_cut=expected,
        best_ratio=ratio(cuts[best]),
        expected_ratio=ratio(expected),
    )
