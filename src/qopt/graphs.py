"""Reproducible random graph generation for Max-Cut experiments."""

import networkx as nx


def generate_random_graph(num_nodes: int, density: float, seed: int) -> nx.Graph:
    """Return an undirected, unweighted Erdos-Renyi random graph G(n, p).

    Each of the n*(n-1)/2 possible edges is included independently with
    probability ``density``. The same (num_nodes, density, seed) always gives
    the same graph. Nodes are labelled 0..num_nodes-1.
    """
    # bool is a subclass of int in Python, so reject it explicitly.
    if not isinstance(num_nodes, int) or isinstance(num_nodes, bool):
        raise TypeError(f"num_nodes must be an int, got {type(num_nodes).__name__}")
    if num_nodes < 1:
        raise ValueError(f"num_nodes must be >= 1, got {num_nodes}")
    if not isinstance(density, (int, float)) or isinstance(density, bool):
        raise TypeError(f"density must be a number, got {type(density).__name__}")
    if not 0.0 <= density <= 1.0:
        raise ValueError(f"density must be in [0, 1], got {density}")
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise TypeError(f"seed must be an int, got {type(seed).__name__}")
    if seed < 0:
        raise ValueError(f"seed must be >= 0, got {seed}")

    return nx.gnp_random_graph(num_nodes, float(density), seed=seed)


def validate_graph(graph: nx.Graph) -> None:
    """Raise ValueError unless ``graph`` is a simple undirected graph on nodes 0..n-1.

    All solvers index nodes by position in a bitstring, so the labels must be
    exactly 0..n-1.
    """
    if not isinstance(graph, nx.Graph) or graph.is_directed() or graph.is_multigraph():
        raise ValueError("graph must be a simple undirected networkx.Graph")
    n = graph.number_of_nodes()
    if n < 1:
        raise ValueError("graph must have at least one node")
    if set(graph.nodes) != set(range(n)):
        raise ValueError("graph nodes must be labelled 0..n-1")
    if nx.number_of_selfloops(graph) > 0:
        raise ValueError("graph must not contain self-loops")
