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
