# Phase 3 — Noise simulation

## What was built

| File | Purpose |
|---|---|
| `src/qopt/noise.py` | **New.** `NoiseLevel` (name + 3 error rates), the `NOISE_LEVELS` table (`none`, `low`, `medium`, `high`), `get_noise_level(name)`, `build_noise_model(level)` and `check_noise_covers_circuit(circuit, model)`. |
| `src/qopt/qaoa.py` | `run_qaoa(..., noise="none", optimization_mode="noisy")`. `sample_counts(..., noise_model=None)`. `QAOAResult` now records `noise` (name and exact rates) and `optimization_mode`. |
| `tests/test_noise.py` | **New.** 26 tests. |
| `scripts/demo_phase3.py` | **New.** QAOA p=1 and p=2 under all four levels, on a 6-node and an 8-node graph. |

(The Phase 2 restarts follow-up is documented in `docs/phase-2-notes.md`.)

### APIs chosen (checked on Qiskit Aer 0.17.2 before coding)

| API | Why |
|---|---|
| `qiskit_aer.noise.NoiseModel` | Aer's container for "which error happens after which instruction". |
| `depolarizing_error(param, num_qubits)` | The simplest standard gate error: one number per gate type, easy to read and explain. |
| `ReadoutError([[1-p, p], [p, 1-p]])` | Measurement bit flips: row = true value, column = value read. |
| `add_all_qubit_quantum_error(error, ["h","rz","rx"])` / `(error, ["cx"])`, `add_all_qubit_readout_error(...)` | Attach errors **by gate name** to every qubit, so the names must match our circuit's gates exactly. |
| `SamplerV2(seed=..., options={"backend_options": {"noise_model": model}})` | The same sampler as Phase 2, now with a noise model. For `"none"` we pass **no** model at all, so it's literally the Phase 2 code path. |

## The noise levels

| level | one-qubit error (h, rz, rx) | two-qubit error (cx) | readout error |
|---|---|---|---|
| none | 0 | 0 | 0 |
| low | 0.001 | 0.01 | 0.01 |
| medium | 0.005 | 0.03 | 0.03 |
| high | 0.01 | 0.08 | 0.05 |

**These are illustrative levels, not a calibrated model of any real
device.** How they were chosen:
- **Relative sizes follow a well-known pattern:** two-qubit gates are about
  10× worse than one-qubit gates, and readout errors are around 1%. That's
  the rough order of magnitude commonly reported for today's
  superconducting quantum computers.
- **low** is roughly "a decent current device". **medium** is about 3× worse.
  **high** is about 8× worse on two-qubit gates, closer to older or very
  noisy hardware.
- The range is chosen so the demo graphs show a clear trend from "barely
  affected" to "almost random", without being trivially destroyed.

Every number is in `NOISE_LEVELS` in `src/qopt/noise.py`, printed by the
demo, and stored in each `QAOAResult.noise`. Nothing is hidden.

## Key concepts

### What noise is, physically
A qubit is a tiny physical system: a superconducting circuit, a trapped
ion, and so on. It is constantly disturbed by its surroundings: heat,
stray electromagnetic fields, imperfect control pulses. Each gate is a
real pulse that's never exactly right, and the qubit slowly "forgets" its
state over time (*decoherence*). Reading a qubit out is also an imperfect
physical measurement. Result: every operation has a small chance of going
wrong, and errors pile up across the circuit.

### What each of our parameters means
- **One-qubit error** (after every `h`, `rz`, `rx`): a *depolarizing* error.
  With this probability the qubit's state is thrown away and replaced by a
  completely random one, so its information is lost. (Because "random"
  sometimes lands on the original state by chance, the probability of an
  actual change is a bit lower, ¾ of the number for one qubit.)
- **Two-qubit error** (after every `cx`): the same, but both qubits
  involved are randomized together (an actual change in 15 of 16 cases).
- **Readout error**: when measuring, each bit is reported wrong with this
  probability, so a 0 is read as 1 or a 1 as 0. The quantum state was fine;
  the reading wasn't.

### Why deeper circuits suffer more
Every gate is another chance for an error. Our QAOA circuit has
2 × (edges) × p `cx` gates. For the 8-node, 16-edge demo graph, counting
only `cx` errors, the chance that a whole run has no `cx` error at all is:

| level (cx error) | p=1 (32 cx) | p=2 (64 cx) |
|---|---|---|
| low (0.01) | 0.99³² ≈ 72% | 0.99⁶⁴ ≈ 53% |
| high (0.08) | 0.92³² ≈ 7% | 0.92⁶⁴ ≈ 0.5% |

Errors scramble the delicate interference QAOA relies on and push the
output toward random bitstrings. So without noise, more layers (p=2) help,
because there are more knobs to tune. With noise, extra layers also add
extra errors, and the demo shows that trade-off going against p=2.

### Two optimization modes
- `"noisy"` (default): the optimizer sees noisy results while tuning the
  angles, like running QAOA on real hardware.
- `"ideal"`: the angles are tuned on the noiseless simulator, then only the
  final measurement is noisy. This asks "how much do good angles suffer
  from noise?" and gives identical angles at every noise level, so
  differences come from noise alone (the tests use this).

The mode is stored in `QAOAResult.optimization_mode`. With `noise="none"`
both modes give the same result.

### A silent-failure trap we hit (and now guard against)
Aer attaches errors **by gate name**. If the names don't match the circuit's
gates, the "noisy" simulation is secretly ideal and nothing warns you. We
found a second version of this trap while testing: **Aer quietly leaves out
an error whose probability is exactly 0**, so that gate type then has no
noise entry at all. Protections:
- `check_noise_covers_circuit` runs before every noisy simulation and
  raises if any instruction in the circuit (other than `barrier`) has no
  error attached.
- `build_noise_model` rejects a noisy level with any rate of 0.
- Tests take circuits whose ideal result is certain (always `00`), put a
  large error on **one** gate type (h, rz, rx, cx or measure) and check the
  result is no longer certain. So each error is shown to have a real effect.

### Limits of our noise model
It's deliberately simple. Real devices differ in many ways:
- **Only depolarizing and readout errors.** No energy decay or dephasing
  over time (T1/T2), no slightly-wrong rotation angles (coherent errors), no
  crosstalk between neighbouring qubits, no leakage.
- **Every qubit is identical.** Real qubits each have their own error rates,
  which drift over time.
- **Any qubit can talk to any other.** Real chips connect only neighbouring
  qubits, so extra SWAP gates (3 `cx` each) would be needed: real circuits
  are deeper than ours, so we are *optimistic* here.
- **`rz` is noisy here.** On IBM-style hardware `rz` is done in software
  ("virtual") and is essentially error-free, so we're slightly *pessimistic*
  here.
- **No timing.** Idle qubits don't decay while they wait for other gates.
- **No error mitigation**, which real experiments often use.

So the results show **trends** (how quality falls as noise and depth grow),
not predictions for any specific machine.

## Demo output (real run, this machine; 84.3 s total)

```
shots=1024, COBYLA maxiter=100, restarts=3, seeds=0, angles optimized under noise
Noise levels (illustrative, NOT a model of any real device):
  none    1q=0.0    2q=0.0   readout=0.0
  low     1q=0.001  2q=0.01  readout=0.01
  medium  1q=0.005  2q=0.03  readout=0.03
  high    1q=0.01   2q=0.08  readout=0.05

Graph: 6 nodes, 9 edges (density=0.5, seed=42), optimal cut = 7
  method                 expected   ratio P(optimal)   notes
  exact                      7.00   1.000      1.000
  random sampling            4.55   0.650      0.062
  QAOA p=1 noise=none        5.70   0.814      0.264   91 evals, 1.5s simulator
  QAOA p=1 noise=low         5.55   0.793      0.233   79 evals, 2.5s simulator
  QAOA p=1 noise=medium      5.29   0.755      0.188   80 evals, 2.5s simulator
  QAOA p=1 noise=high        4.96   0.708      0.118   88 evals, 2.8s simulator
  QAOA p=2 noise=none        5.81   0.830      0.304   157 evals, 3.3s simulator
  QAOA p=2 noise=low         5.56   0.794      0.242   165 evals, 7.1s simulator
  QAOA p=2 noise=medium      5.27   0.753      0.197   150 evals, 6.7s simulator
  QAOA p=2 noise=high        4.77   0.681      0.089   113 evals, 4.9s simulator

Graph: 8 nodes, 16 edges (density=0.5, seed=42), optimal cut = 13
  method                 expected   ratio P(optimal)   notes
  exact                     13.00   1.000      1.000
  random sampling            8.01   0.616      0.010
  QAOA p=1 noise=none        9.90   0.761      0.077   100 evals, 2.6s simulator
  QAOA p=1 noise=low         9.64   0.742      0.062   106 evals, 5.6s simulator
  QAOA p=1 noise=medium      9.24   0.711      0.040   112 evals, 6.1s simulator
  QAOA p=1 noise=high        8.63   0.664      0.024   99 evals, 5.4s simulator
  QAOA p=2 noise=none       10.49   0.807      0.168   131 evals, 4.0s simulator
  QAOA p=2 noise=low         9.39   0.723      0.054   138 evals, 9.5s simulator
  QAOA p=2 noise=medium      8.89   0.684      0.027   145 evals, 10.2s simulator
  QAOA p=2 noise=high        8.16   0.628      0.009   132 evals, 9.5s simulator

Total demo runtime: 84.3s (classical simulator)
```

How to read it:
- **More noise is always worse here.** Expected cut and P(optimal) fall at
  every step from none to high, for both graphs and both depths.
- **Depth vs noise:** with no noise, p=2 beats p=1 (8 nodes: 0.807 vs 0.761).
  With any noise on the 8-node graph, p=2 is *worse* than p=1 (low: 0.723 vs
  0.742; high: 0.628 vs 0.664). The extra layer's errors cost more than its
  extra tuning gains. On 6 nodes the two depths are about equal at low and
  medium noise, and p=2 is worse at high.
- **Approaching random:** 8 nodes, p=2, high noise gives an expected ratio of
  0.628, barely above random sampling's 0.616, and P(optimal) 0.009 vs
  random's 0.010, i.e. no better than guessing at finding the optimum.
- Classical greedy and annealing found the optimum on both graphs (Phases 1
  and 2). No quantum advantage is shown or claimed.
- This is one graph per size and one seed. Phase 4 will repeat runs across
  seeds and graphs before drawing conclusions.
- Noisy simulation is roughly 2–3× slower than ideal on this laptop.

## How to run it

From the project root, in PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1               # activate the venv (Python 3.14)
python -m pip install -e .                 # once; makes `import qopt` work
python -m pytest -q                        # all 142 tests (~30 s)
python -m pytest tests\test_noise.py -q    # just the noise tests (~20 s)
python scripts\demo_phase3.py              # Phase 3 demo (~85 s)
```

Using it from Python:

```python
from qopt.qaoa import run_qaoa
r = run_qaoa(graph, p=1, optimal_cut=opt, noise="medium", num_restarts=3)
r.noise               # NoiseLevel(name='medium', one_qubit_error=0.005, ...)
r.optimization_mode   # 'noisy'
```
