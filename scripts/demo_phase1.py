"""Phase 1 demo: compare greedy and simulated annealing with the exact optimum.

Run from the project root with the venv active:
    python scripts/demo_phase1.py
"""

import time
from collections.abc import Callable

import networkx as nx

from qopt.classical import brute_force_max_cut, greedy_max_cut, simulated_annealing
from qopt.graphs import generate_random_graph
from qopt.maxcut import MaxCutResult

DENSITY = 0.5
SEED = 42
SIZES = [6, 10, 14, 18]


def timed(solver: Callable[[], MaxCutResult]) -> tuple[MaxCutResult, float]:
    start = time.perf_counter()
    result = solver()
    return result, (time.perf_counter() - start) * 1000


def main() -> None:
    print(f"Random graphs: density={DENSITY}, seed={SEED}")
    print("ratio = solver cut / optimal cut (1.000 = found the optimum)\n")
    header = f"{'nodes':>5} {'edges':>5} | {'solver':<10} {'cut':>4} {'ratio':>6} {'time ms':>8}  bitstring"
    print(header)
    print("-" * len(header))

    for n in SIZES:
        g: nx.Graph = generate_random_graph(n, DENSITY, SEED)
        exact, t_exact = timed(lambda: brute_force_max_cut(g))
        rows = [
            ("exact", exact, t_exact),
            ("greedy", *timed(lambda: greedy_max_cut(g))),
            ("annealing", *timed(lambda: simulated_annealing(g, seed=SEED))),
        ]
        for i, (name, result, ms) in enumerate(rows):
            prefix = f"{n:>5} {g.number_of_edges():>5}" if i == 0 else " " * 11
            ratio = result.cut_value / exact.cut_value if exact.cut_value else 1.0
            print(
                f"{prefix} | {name:<10} {result.cut_value:>4} {ratio:>6.3f} "
                f"{ms:>8.2f}  {result.bitstring}"
            )
        print()


if __name__ == "__main__":
    main()
