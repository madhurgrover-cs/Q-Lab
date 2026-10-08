"""Phase 2 demo: QAOA (p=1, p=2) next to the classical baselines.

Run from the project root with the venv active:
    python scripts/demo_phase2.py

All quantum results come from a classical simulator (Qiskit Aer). Times are
simulator wall-clock on this laptop, not quantum hardware times.
"""

from qopt.classical import (
    brute_force_max_cut,
    greedy_max_cut,
    random_sampling,
    simulated_annealing,
)
from qopt.graphs import generate_random_graph
from qopt.qaoa import run_qaoa

GRAPHS = [(6, 0.5, 42), (8, 0.5, 42)]  # (nodes, density, seed)
SHOTS = 1024
MAXITER = 100
SEED = 0


def row(name: str, best: int, expected: float, best_ratio: float, exp_ratio: float, extra: str = "") -> str:
    return f"  {name:<16} {best:>4} {best_ratio:>6.3f}   {expected:>7.2f} {exp_ratio:>6.3f}   {extra}"


def main() -> None:
    print(f"shots={SHOTS}, optimizer=COBYLA (maxiter={MAXITER}), seeds={SEED}")
    print("best = best single bitstring; expected = average cut over all shots")
    print("ratio = cut / optimal cut. Single-answer solvers have best = expected.\n")

    for n, density, gseed in GRAPHS:
        g = generate_random_graph(n, density, gseed)
        exact = brute_force_max_cut(g)
        opt = exact.cut_value
        print(f"Graph: {n} nodes, {g.number_of_edges()} edges (density={density}, seed={gseed}), optimal cut = {opt}")
        print(f"  {'method':<16} {'best':>4} {'ratio':>6}   {'expected':>7} {'ratio':>6}   notes")

        for name, res in [
            ("exact", exact),
            ("greedy", greedy_max_cut(g)),
            ("annealing", simulated_annealing(g, seed=SEED)),
        ]:
            r = res.cut_value / opt
            print(row(name, res.cut_value, res.cut_value, r, r))

        rand = random_sampling(g, shots=SHOTS, seed=SEED, optimal_cut=opt)
        print(row("random sampling", rand.best_cut, rand.expected_cut, rand.best_ratio, rand.expected_ratio))

        for p in (1, 2):
            q = run_qaoa(g, p, opt, shots=SHOTS, seed=SEED, simulator_seed=SEED, maxiter=MAXITER)
            s = q.samples
            p_opt = sum(c for b, c in s.counts.items() if s.cut_values[b] == opt) / s.shots
            extra = (
                f"{q.num_evaluations} circuit evals, {q.simulator_runtime_s:.2f}s simulator, "
                f"P(optimal)={p_opt:.3f}"
            )
            print(row(f"QAOA p={p}", s.best_cut, s.expected_cut, s.best_ratio, s.expected_ratio, extra))
            angles = ", ".join(f"g{i}={gm:.3f} b{i}={bt:.3f}" for i, (gm, bt) in enumerate(zip(q.gammas, q.betas)))
            print(f"  {'':<16} angles: {angles}")

        rand_p_opt = sum(c for b, c in rand.counts.items() if rand.cut_values[b] == opt) / rand.shots
        print(f"  (random sampling P(optimal)={rand_p_opt:.3f})\n")


if __name__ == "__main__":
    main()
