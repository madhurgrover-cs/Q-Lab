"""Greedy Max-Cut: place nodes one at a time on the side that cuts more edges."""

import networkx as nx

from qopt.graphs import validate_graph
from qopt.maxcut import MaxCutResult, cut_value


def greedy_max_cut(graph: nx.Graph) -> MaxCutResult:
    """Place nodes 0, 1, 2, ... in order, each on the side that cuts the most
    edges to already-placed neighbours (ties go to side '0').

    Each edge is counted once, when its second endpoint is placed, and at that
    moment we cut at least half of the new edges. So the result always cuts
    at least half of all edges. Deterministic: no randomness involved.
    """
    validate_graph(graph)
    n = graph.number_of_nodes()
    sides: list[str] = []
    for node in range(n):
        placed = [nbr for nbr in graph.neighbors(node) if nbr < node]
        ones = sum(1 for nbr in placed if sides[nbr] == "1")
        zeros = len(placed) - ones
        # Joining side '1' cuts the edges to neighbours on side '0', and vice versa.
        sides.append("1" if zeros > ones else "0")

    bitstring = "".join(sides)
    return MaxCutResult(bitstring, cut_value(graph, bitstring))
