"""Phase 3 demo: QAOA (p=1, p=2) under the four illustrative noise levels.

Run from the project root with the venv active:
    python scripts/demo_phase3.py

All quantum results come from a classical simulator (Qiskit Aer) with an
illustrative noise model, not from a real device. Times are simulator
wall-clock on this laptop.
"""

import time

from qopt.classical import brute_force_max_cut, random_sampling
from qopt.graphs import generate_random_graph
from qopt.maxcut import SampleStats
from qopt.noise import NOISE_LEVELS
from qopt.qaoa import run_qaoa

GRAPHS = [(6, 0.5, 42), (8, 0.5, 42)]  # (nodes, density, seed)
SHOTS = 1024
MAXITER = 100
RESTARTS = 3
SEED = 0


def p_optimal(s: SampleStats, opt: int) -> float:
    """Fraction of shots that measured an optimal cut."""
    return sum(c for b, c in s.counts.items() if s.cut_values[b] == opt) / s.shots


def row(name: str, s: SampleStats, opt: int, extra: str = "") -> str:
    return (
        f"  {name:<22} {s.expected_cut:>8.2f} {s.expected_ratio:>7.3f} "
        f"{p_optimal(s, opt):>10.3f}   {extra}"
    )


def main() -> None:
    start = time.perf_counter()
    print(f"shots={SHOTS}, COBYLA maxiter={MAXITER}, restarts={RESTARTS}, seeds={SEED}, "
          "angles optimized under noise")
    print("Noise levels (illustrative, NOT a model of any real device):")
    for lvl in NOISE_LEVELS.values():
        print(f"  {lvl.name:<7} 1q={lvl.one_qubit_error:<6} 2q={lvl.two_qubit_error:<5} "
              f"readout={lvl.readout_error}")
    print()

    for n, density, gseed in GRAPHS:
        g = generate_random_graph(n, density, gseed)
        opt = brute_force_max_cut(g).cut_value
        print(f"Graph: {n} nodes, {g.number_of_edges()} edges (density={density}, "
              f"seed={gseed}), optimal cut = {opt}")
        print(f"  {'method':<22} {'expected':>8} {'ratio':>7} {'P(optimal)':>10}   notes")
        print(f"  {'exact':<22} {opt:>8.2f} {1.0:>7.3f} {1.0:>10.3f}")
        rand = random_sampling(g, shots=SHOTS, seed=SEED, optimal_cut=opt)
        print(row("random sampling", rand, opt))

        for p in (1, 2):
            for level in NOISE_LEVELS:
                q = run_qaoa(
                    g, p, opt, shots=SHOTS, seed=SEED, simulator_seed=SEED,
                    maxiter=MAXITER, num_restarts=RESTARTS, noise=level,
                )
                extra = f"{q.num_evaluations} evals, {q.simulator_runtime_s:.1f}s simulator"
                print(row(f"QAOA p={p} noise={level}", q.samples, opt, extra))
        print()

    print(f"Total demo runtime: {time.perf_counter() - start:.1f}s (classical simulator)")


if __name__ == "__main__":
    main()
