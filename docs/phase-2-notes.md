# Phase 2 — QAOA for Max-Cut

## What was built

| File | Purpose |
|---|---|
| `src/qopt/qaoa.py` | **All quantum code.** `build_qaoa_circuit(graph, p)`, `sample_counts(...)` (runs on the Aer simulator), `run_qaoa(...)` (optimizer loop), `qiskit_to_node_bitstring(...)` (the single bit-order conversion), `QAOAResult`. |
| `src/qopt/maxcut.py` | Added `SampleStats` and `summarize_samples(graph, counts, optimal_cut)`: best cut, expected cut and both ratios, from any batch of sampled bitstrings. |
| `src/qopt/classical/random_sampling.py` | `random_sampling(graph, shots, seed, optimal_cut)`: the "no intelligence" baseline QAOA must beat. |
| `tests/test_qaoa.py`, `tests/test_maxcut.py` | 20 new tests (113 total). |
| `scripts/demo_phase2.py` | Side-by-side comparison on a 6-node and an 8-node graph. |

### APIs chosen (Qiskit 2.5.2, Qiskit Aer 0.17.2, SciPy 1.18.1)

I checked these against the installed versions before writing code.
`qiskit.algorithms`, `qiskit.opflow` and `qiskit.execute` no longer exist in
this Qiskit at all.

| API | Why |
|---|---|
| `qiskit.circuit.QuantumCircuit` with `h`, `cx`, `rz`, `rx`, `measure_all` | The circuit is built gate by gate so you can read it. There's no prebuilt `QAOAAnsatz` hiding the structure. |
| `qiskit.circuit.ParameterVector` + `assign_parameters` | The circuit is built once with named placeholders (`gamma[k]`, `beta[k]`); the optimizer's numbers are filled in each round. |
| `qiskit_aer.primitives.SamplerV2(seed=...)` | The current "primitives" interface (V2) for getting measurement counts, the same style IBM's real-hardware service uses. It's seedable, and in Phase 3 the same class can take a noise model. |
| `scipy.optimize.minimize(method="COBYLA")` | A standard derivative-free optimizer, a good fit because our score is estimated from noisy shots. The method is configurable. |

## Key concepts

### Qubits and superposition
A classical bit is 0 or 1. A **qubit** can be in a **superposition**: a
weighted blend of 0 and 1 that only becomes a definite 0 or 1 when measured,
randomly, with probabilities set by those weights. With n qubits the blend
covers all 2ⁿ bitstrings at once. Here, one qubit = one node, so one
measurement gives one candidate cut.

### The QAOA circuit, layer by layer
1. **Start**: a Hadamard gate (`h`) on every qubit gives an equal superposition.
   Every cut is equally likely, which is the same as random guessing.
2. **Cost layer** (angle **γ**, gamma): for each edge, `cx – rz(2γ) – cx`
   gives the bitstring a phase (a rotation of its hidden "arrow") depending
   on whether that edge is cut. Probabilities don't change yet; it *tags*
   bitstrings according to how good they are.
3. **Mixer layer** (angle **β**, beta): `rx(2β)` on every qubit mixes amplitude
   between bitstrings that differ by one node. Because of the tags, the
   contributions *interfere*: some add up and some cancel. With good angles,
   probability flows toward bigger cuts.
4. Repeat cost + mixer **p** times (the *depth*). More layers allow better
   results in principle, at the cost of more gates and more angles to tune.
5. **Measure** every qubit to get one bitstring.

For an 8-node, 16-edge graph at p=1 that's 8 `h` + 32 `cx` + 16 `rz` +
8 `rx` gates.

### The angles
γ₁…γₚ and β₁…βₚ (2p numbers) are the circuit's only knobs. QAOA's job is to
find the angles that give the highest average cut.

### Why a classical optimizer is involved
There's no formula for the best angles. So QAOA is a **loop**:
SciPy's COBYLA proposes angles → we simulate the circuit and measure → we
score the average cut → COBYLA proposes better angles. The quantum part only
*evaluates*; a normal classical algorithm does the *searching*. That's why
QAOA is called a **hybrid** algorithm. Each loop round is one "circuit
evaluation". COBYLA doesn't report an "iteration" count, so
`optimizer_iterations` is `None` for it, and we report `num_evaluations`,
which we count ourselves.

### Shots
Measuring destroys the superposition and gives one bitstring, so we
re-prepare and measure the circuit many times. Each run is a **shot**. 1024
shots give a histogram (`counts`), and from it:
- **expected cut**: the average over all shots. This is what QAOA actually
  optimizes and the fair measure of quality.
- **best cut**: the best single shot. On small graphs it's misleading: in
  the demo, *random guessing* also found the optimum on both graphs, just
  by trying 1024 times.

### Bit order (one place only)
Qiskit writes qubit 0 as the **rightmost** character (`'001'` = qubit 0 is 1).
Our Phase 1 convention puts node 0 **first**. `qiskit_to_node_bitstring`
reverses the string. It's the only place this happens, and a test checks it
on a real measurement and an asymmetric graph where getting it wrong changes
the cut value.

### Honest measurement choices
- **Fresh final shots:** during optimization the simulator uses
  `simulator_seed`. The reported result is measured with
  `simulator_seed + 1`, on shots the optimizer never saw, so lucky shot noise
  that the optimizer may have exploited doesn't inflate the numbers.
- **Runtime label:** `simulator_runtime_s` is how long the *classical
  simulator on this laptop* took (whole optimization plus final
  measurement). It is not, and says nothing about, quantum hardware speed.

## Demo output (real run, this machine; ~14 s total)

```
shots=1024, optimizer=COBYLA (maxiter=100), seeds=0
best = best single bitstring; expected = average cut over all shots
ratio = cut / optimal cut. Single-answer solvers have best = expected.

Graph: 6 nodes, 9 edges (density=0.5, seed=42), optimal cut = 7
  method           best  ratio   expected  ratio   notes
  exact               7  1.000      7.00  1.000
  greedy              7  1.000      7.00  1.000
  annealing           7  1.000      7.00  1.000
  random sampling     7  1.000      4.55  0.650
  QAOA p=1            7  1.000      5.70  0.814   28 circuit evals, 0.75s simulator, P(optimal)=0.264
                   angles: g0=2.892 b0=0.301
  QAOA p=2            7  1.000      5.77  0.824   64 circuit evals, 1.74s simulator, P(optimal)=0.287
                   angles: g0=2.753 b0=0.047, g1=0.666 b1=1.305
  (random sampling P(optimal)=0.062)

Graph: 8 nodes, 16 edges (density=0.5, seed=42), optimal cut = 13
  method           best  ratio   expected  ratio   notes
  exact              13  1.000     13.00  1.000
  greedy             13  1.000     13.00  1.000
  annealing          13  1.000     13.00  1.000
  random sampling    13  1.000      8.01  0.616
  QAOA p=1           13  1.000      9.87  0.759   29 circuit evals, 1.24s simulator, P(optimal)=0.076
                   angles: g0=2.932 b0=0.343
  QAOA p=2           13  1.000      9.92  0.763   47 circuit evals, 1.60s simulator, P(optimal)=0.081
                   angles: g0=2.882 b0=0.353, g1=0.872 b1=-0.026
  (random sampling P(optimal)=0.010)
```

How to read it:
- **Every** method's best cut is optimal, random guessing included, so the
  best-cut column tells us nothing on graphs this small.
- On **expected cut**, QAOA clearly beats random sampling (0.814 vs 0.650,
  0.759 vs 0.616) and samples the optimal cut much more often (26% vs 6%,
  8% vs 1%). So the circuit really does shift probability toward good cuts.
- QAOA's expected cut is **well below** greedy and annealing, which return
  the optimum directly, in milliseconds. On these graphs the classical
  methods are better. No quantum advantage is shown or claimed.
- **p=2 barely improved on p=1.** In theory p=2 at its best angles is at least
  as good as p=1, so the optimizer (COBYLA from one random start, with
  shot noise) likely stopped at a weaker setting. On the 8-node graph
  `b1 ≈ 0`, meaning the second mixer layer is almost switched off. This is a
  known practical difficulty of QAOA, not a bug. Phase 4 experiments should
  use several seeds and may test smarter starting angles.
  *(Addressed by the follow-up below.)*
- Times are single runs of a classical simulator. Don't compare them to
  classical solver times as if they were quantum times.

## Follow-up: multiple restarts (`num_restarts`)

Added after Phase 2 was approved, to address the "p=2 barely beat p=1" issue.

**What it does.** `run_qaoa(..., num_restarts=k)` runs COBYLA from *k*
different random starting angles (all drawn from `seed`) and keeps the
angles with the best optimizer score. The final, reported measurement still
uses fresh shots (`simulator_seed + 1`), exactly as before.

**Why it's legitimate, not result tuning.** Optimizers like COBYLA only walk
"downhill" from where they start, so a single start can get stuck at a poor
setting (a *local optimum*). Multi-start is the standard fix. The choice of
winner uses only the optimizer's own score on the optimization shots,
never the reported fresh shots or the known optimum. All restarts share the
same `simulator_seed`, so their scores are directly comparable.

Details:
- Restart 0 uses the same start as `num_restarts=1`, so the default (1)
  reproduces Phase 2 exactly, and more restarts can only match or beat its
  optimizer score (tested).
- The result records `num_restarts`, `num_evaluations` (summed over all
  restarts) and `training_expected_cut` (the optimizer's score at the chosen
  angles).
- Cost: roughly *k* times more simulator time.
- COBYLA is unbounded, so angles can come out beyond the [0, π) range
  (e.g. g1=4.364). That's fine: the circuit repeats with period π, so it's
  the same circuit as 4.364 − π = 1.223.

**Demo re-run (real output, r = num_restarts):**
```
Graph: 6 nodes, 9 edges (density=0.5, seed=42), optimal cut = 7
  method           best  ratio   expected  ratio   notes
  random sampling     7  1.000      4.55  0.650
  QAOA p=1 r=1        7  1.000      5.70  0.814   28 circuit evals, 0.52s simulator, P(optimal)=0.264
  QAOA p=2 r=1        7  1.000      5.77  0.824   64 circuit evals, 1.19s simulator, P(optimal)=0.287
  QAOA p=1 r=5        7  1.000      5.70  0.814   158 circuit evals, 2.50s simulator, P(optimal)=0.264
  QAOA p=2 r=5        7  1.000      5.81  0.830   249 circuit evals, 4.98s simulator, P(optimal)=0.304

Graph: 8 nodes, 16 edges (density=0.5, seed=42), optimal cut = 13
  method           best  ratio   expected  ratio   notes
  random sampling    13  1.000      8.01  0.616
  QAOA p=1 r=1       13  1.000      9.87  0.759   29 circuit evals, 0.78s simulator, P(optimal)=0.076
  QAOA p=2 r=1       13  1.000      9.92  0.763   47 circuit evals, 1.44s simulator, P(optimal)=0.081
  QAOA p=1 r=5       13  1.000      9.90  0.761   156 circuit evals, 4.06s simulator, P(optimal)=0.077
  QAOA p=2 r=5       13  1.000     10.56  0.812   228 circuit evals, 7.15s simulator, P(optimal)=0.149
(exact, greedy and annealing all optimal; full output from scripts\demo_phase2.py)
```

What happened:
- **8 nodes:** with 5 restarts, p=2 clearly beats p=1 (expected ratio 0.812
  vs 0.761), and P(optimal) roughly doubles (0.077 → 0.149). So the earlier
  result was an optimizer problem, not a limit of p=2.
- **6 nodes:** only a small gain (0.830 vs 0.814). p=1 didn't change at all
  with restarts: its first start was already the best found.
- The r=1 rows are identical to the original Phase 2 output.
- QAOA remains below greedy and annealing, which find the optimum.

## How to run it

From the project root, in PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1      # activate the venv (Python 3.14)
python -m pip install -e .        # once; makes `import qopt` work
python -m pytest -q               # all tests (~30 s as of Phase 3)
python -m pytest tests\test_qaoa.py -q   # just the QAOA tests
python scripts\demo_phase2.py     # Phase 2 demo, incl. restarts (~30 s)
```
