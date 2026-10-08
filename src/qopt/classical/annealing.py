"""Simulated annealing for Max-Cut."""

import math

import networkx as nx
import numpy as np

from qopt.graphs import validate_graph
from qopt.maxcut import MaxCutResult, cut_value


def simulated_annealing(
    graph: nx.Graph,
    seed: int,
    num_steps: int = 10_000,
    initial_temp: float = 2.0,
    final_temp: float = 0.01,
) -> MaxCutResult:
    """Search for a large cut by random single-node flips.

    Start from a random partition. At each step pick a random node and
    consider moving it to the other side, which changes the cut by ``delta``:
    - if delta >= 0 (cut doesn't get worse), always accept;
    - otherwise accept with probability exp(delta / T).
    The temperature T falls geometrically from ``initial_temp`` to
    ``final_temp``, so early on we accept many bad moves (exploration) and
    late on almost none (refinement). Returns the best partition seen.
    The same seed always gives the same result.
    """
    validate_graph(graph)
    if num_steps < 1:
        raise ValueError(f"num_steps must be >= 1, got {num_steps}")
    if not 0 < final_temp <= initial_temp:
        raise ValueError("temperatures must satisfy 0 < final_temp <= initial_temp")

    rng = np.random.default_rng(seed)
    n = graph.number_of_nodes()
    neighbors = [list(graph.neighbors(v)) for v in range(n)]

    sides = rng.integers(0, 2, size=n).tolist()
    current = sum(1 for u, v in graph.edges if sides[u] != sides[v])
    best, best_sides = current, sides.copy()

    cooling = (final_temp / initial_temp) ** (1 / max(num_steps - 1, 1))
    temp = initial_temp
    nodes = rng.integers(0, n, size=num_steps)
    coins = rng.random(size=num_steps)

    for step in range(num_steps):
        v = int(nodes[step])
        # Flipping v turns its cut edges into uncut ones and vice versa.
        cut_at_v = sum(1 for u in neighbors[v] if sides[u] != sides[v])
        delta = len(neighbors[v]) - 2 * cut_at_v
        if delta >= 0 or coins[step] < math.exp(delta / temp):
            sides[v] = 1 - sides[v]
            current += delta
            if current > best:
                best, best_sides = current, sides.copy()
        temp *= cooling

    bitstring = "".join(str(s) for s in best_sides)
    result = MaxCutResult(bitstring, cut_value(graph, bitstring))
    assert result.cut_value == best, "incremental cut tracking went wrong"
    return result
