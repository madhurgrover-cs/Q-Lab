"""Q-Opt Lab: comparing QAOA with classical optimization on Max-Cut."""

from qopt.graphs import generate_random_graph, validate_graph
from qopt.maxcut import MaxCutResult, SampleStats, cut_value, summarize_samples

__all__ = [
    "MaxCutResult",
    "SampleStats",
    "cut_value",
    "generate_random_graph",
    "summarize_samples",
    "validate_graph",
]
