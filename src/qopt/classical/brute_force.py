"""Exact Max-Cut by checking every partition. Only feasible for small graphs."""

import networkx as nx
import numpy as np

from qopt.graphs import validate_graph
from qopt.maxcut import MaxCutResult, cut_value

# 2**(20-1) = 524,288 partitions: a few MB of RAM and well under a second.
MAX_BRUTE_FORCE_NODES = 20


def brute_force_max_cut(graph: nx.Graph) -> MaxCutResult:
    """Return an optimal cut, our reference answer for judging other solvers.

    Swapping every node's side gives the same cut, so we fix node 0 on side
    '0' and enumerate the remaining 2**(n-1) partitions. Partition number x
    puts node i on side ``(x >> i) & 1``. All partitions are scored at once
    with NumPy. If several are optimal, the lowest-numbered one is returned.
    """
    validate_graph(graph)
    n = graph.number_of_nodes()
    if n > MAX_BRUTE_FORCE_NODES:
        raise ValueError(
            f"brute force supports at most {MAX_BRUTE_FORCE_NODES} nodes, got {n}"
        )

    # Shift left by 1 so bit 0 (node 0) is always 0.
    partitions = np.arange(2 ** (n - 1), dtype=np.int64) << 1
    cuts = np.zeros(partitions.shape, dtype=np.int64)
    for u, v in graph.edges:
        cuts += ((partitions >> u) ^ (partitions >> v)) & 1

    best = int(partitions[np.argmax(cuts)])
    bitstring = "".join(str((best >> i) & 1) for i in range(n))
    return MaxCutResult(bitstring, cut_value(graph, bitstring))
