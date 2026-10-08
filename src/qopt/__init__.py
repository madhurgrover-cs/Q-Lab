"""Q-Opt Lab: comparing QAOA with classical optimization on Max-Cut."""

from qopt.graphs import generate_random_graph, validate_graph
from qopt.maxcut import MaxCutResult, cut_value

__all__ = ["MaxCutResult", "cut_value", "generate_random_graph", "validate_graph"]
