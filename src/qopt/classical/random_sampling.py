"""Random-sampling baseline: guess uniformly random bitstrings.

QAOA also outputs a batch of sampled bitstrings, so a fair "no intelligence"
baseline is to draw the same number of completely random ones. Any useful
QAOA must beat this, especially on the expected (average) cut.
"""

from collections import Counter

import networkx as nx
import numpy as np

from qopt.graphs import validate_graph
from qopt.maxcut import SampleStats, summarize_samples


def random_sampling(
    graph: nx.Graph, shots: int, seed: int, optimal_cut: int
) -> SampleStats:
    """Draw ``shots`` uniform random bitstrings and report their statistics.

    Each node is independently '0' or '1' with probability 1/2, so each edge
    is cut with probability 1/2 and the expected cut is |E|/2.
    """
    validate_graph(graph)
    if shots < 1:
        raise ValueError(f"shots must be >= 1, got {shots}")

    rng = np.random.default_rng(seed)
    bits = rng.integers(0, 2, size=(shots, graph.number_of_nodes()))
    counts = Counter("".join(map(str, row)) for row in bits.tolist())
    return summarize_samples(graph, dict(counts), optimal_cut)
