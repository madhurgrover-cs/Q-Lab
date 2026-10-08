"""QAOA (Quantum Approximate Optimization Algorithm) for Max-Cut.

All Qiskit code in the project lives in this module.

The quantum part is simulated on a normal computer with Qiskit Aer. Runtimes
reported here are classical *simulator* wall-clock times, not quantum
hardware times, and say nothing about quantum speed.

Bit order: Qiskit prints measured bitstrings with qubit 0 on the RIGHT. Our
Phase 1 convention has node 0 on the LEFT. ``qiskit_to_node_bitstring`` is
the only place that converts between them.
"""

import time
from dataclasses import dataclass, field

import networkx as nx
import numpy as np
from qiskit.circuit import ParameterVector, QuantumCircuit
from qiskit_aer.primitives import SamplerV2
from scipy.optimize import minimize

from qopt.graphs import validate_graph
from qopt.maxcut import SampleStats, summarize_samples

# A 20-qubit statevector is 2**20 complex numbers, about 16 MB. Fine on 4 GB RAM.
MAX_QAOA_QUBITS = 20


@dataclass(frozen=True)
class QAOAResult:
    """Outcome of one QAOA run.

    ``samples`` holds the final measurement at the optimized angles: counts,
    cut value of each bitstring, best measured cut, expected cut, and both
    approximation ratios.
    """

    p: int
    gammas: tuple[float, ...]  # optimized cost-layer angles, one per layer
    betas: tuple[float, ...]  # optimized mixer-layer angles, one per layer
    samples: SampleStats
    optimizer: str
    # Iterations as reported by SciPy; None if the method doesn't report it
    # (COBYLA doesn't). num_evaluations is always known: we count circuit runs.
    optimizer_iterations: int | None
    num_evaluations: int
    # Classical simulator wall-clock time, NOT quantum hardware runtime.
    # Excluded from == so identical seeded runs compare equal.
    simulator_runtime_s: float = field(compare=False)


def qiskit_to_node_bitstring(qiskit_bitstring: str) -> str:
    """Convert a Qiskit measurement string to our convention (node 0 first).

    Qiskit writes qubit 0 as the rightmost character, so we reverse it.
    Example: Qiskit "001" means qubit 0 measured 1, which is our "100".
    """
    return qiskit_bitstring[::-1]


def build_qaoa_circuit(graph: nx.Graph, p: int) -> QuantumCircuit:
    """Build the parameterized depth-p QAOA circuit for Max-Cut on ``graph``.

    One qubit per node; measuring qubit i gives node i's side. The circuit
    has 2p parameters: gamma[0..p-1] (cost layers) and beta[0..p-1]
    (mixer layers).
    """
    validate_graph(graph)
    if not isinstance(p, int) or isinstance(p, bool) or p < 1:
        raise ValueError(f"p must be an int >= 1, got {p!r}")
    n = graph.number_of_nodes()
    if n > MAX_QAOA_QUBITS:
        raise ValueError(f"QAOA supports at most {MAX_QAOA_QUBITS} qubits, got {n}")

    gamma = ParameterVector("gamma", p)
    beta = ParameterVector("beta", p)
    qc = QuantumCircuit(n)

    # Start: a Hadamard on every qubit gives an equal superposition of all
    # 2**n bitstrings, i.e. every possible cut is equally likely.
    qc.h(range(n))

    for layer in range(p):
        # Cost layer, exp(-i * gamma * sum_edges Z_u Z_v):
        # for each edge, CX-RZ-CX applies a phase that depends on whether
        # u and v are on the same side (uncut) or different sides (cut).
        # This "marks" good cuts with a different phase than bad ones.
        # (CX-RZ(2*gamma)-CX is the same as an RZZ(2*gamma) gate.)
        for u, v in graph.edges:
            qc.cx(u, v)
            qc.rz(2 * gamma[layer], v)
            qc.cx(u, v)

        # Mixer layer, exp(-i * beta * sum_nodes X_i):
        # rotating each qubit around X lets amplitude flow between bitstrings
        # that differ by one flipped node. Combined with the phases above,
        # this interference pushes probability toward larger cuts.
        qc.rx(2 * beta[layer], range(n))

    # Read out every qubit; results land in a classical register named "meas".
    qc.measure_all()
    return qc


def sample_counts(circuit: QuantumCircuit, shots: int, simulator_seed: int) -> dict[str, int]:
    """Run a fully bound circuit on the Aer simulator and return counts in
    our bitstring convention."""
    sampler = SamplerV2(seed=simulator_seed)
    result = sampler.run([circuit], shots=shots).result()
    raw = result[0].data.meas.get_counts()
    return {qiskit_to_node_bitstring(b): c for b, c in raw.items()}


def run_qaoa(
    graph: nx.Graph,
    p: int,
    optimal_cut: int,
    *,
    shots: int = 1024,
    seed: int = 0,
    simulator_seed: int = 0,
    optimizer: str = "COBYLA",
    maxiter: int = 100,
) -> QAOAResult:
    """Optimize the QAOA angles for ``graph`` and measure the final circuit.

    Loop: the classical optimizer (SciPy ``optimizer``) proposes angles ->
    we simulate the circuit with ``shots`` shots -> score = expected cut over
    the shots -> optimizer proposes better angles, up to ``maxiter`` times.

    - ``seed`` picks the random starting angles.
    - ``simulator_seed`` seeds the simulator during optimization. The final
      measurement uses ``simulator_seed + 1``: fresh shots the optimizer never
      saw, so the reported numbers aren't flattered by lucky shot noise.
    - ``optimal_cut`` (e.g. from brute force) is used for approximation ratios.
    """
    if shots < 1:
        raise ValueError(f"shots must be >= 1, got {shots}")
    if maxiter < 1:
        raise ValueError(f"maxiter must be >= 1, got {maxiter}")

    start = time.perf_counter()
    circuit = build_qaoa_circuit(graph, p)
    gamma_params = [prm for prm in circuit.parameters if prm.name.startswith("gamma")]
    beta_params = [prm for prm in circuit.parameters if prm.name.startswith("beta")]

    def bind(angles: np.ndarray) -> QuantumCircuit:
        # angles = [gamma_0..gamma_{p-1}, beta_0..beta_{p-1}]
        values = dict(zip(gamma_params + beta_params, angles.tolist()))
        return circuit.assign_parameters(values)

    num_evaluations = 0

    def objective(angles: np.ndarray) -> float:
        nonlocal num_evaluations
        num_evaluations += 1
        counts = sample_counts(bind(angles), shots, simulator_seed)
        # SciPy minimizes, so return minus the expected cut.
        return -summarize_samples(graph, counts, optimal_cut).expected_cut

    # Random starting angles. For unweighted Max-Cut the useful ranges are
    # gamma in [0, pi) and beta in [0, pi/2); outside them the circuit repeats.
    rng = np.random.default_rng(seed)
    x0 = np.concatenate([rng.uniform(0, np.pi, p), rng.uniform(0, np.pi / 2, p)])

    opt = minimize(objective, x0, method=optimizer, options={"maxiter": maxiter})

    final_counts = sample_counts(bind(opt.x), shots, simulator_seed + 1)
    samples = summarize_samples(graph, final_counts, optimal_cut)
    runtime = time.perf_counter() - start

    return QAOAResult(
        p=p,
        gammas=tuple(float(g) for g in opt.x[:p]),
        betas=tuple(float(b) for b in opt.x[p:]),
        samples=samples,
        optimizer=optimizer,
        optimizer_iterations=opt.get("nit"),
        num_evaluations=num_evaluations,
        simulator_runtime_s=runtime,
    )
