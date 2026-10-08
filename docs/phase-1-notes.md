# Phase 1 — Max-Cut and classical baselines

## What was built

| File | Purpose |
|---|---|
| `src/qopt/graphs.py` | `generate_random_graph(num_nodes, density, seed)`: reproducible random graphs, with input validation. `validate_graph(graph)`: checks a graph is usable by the solvers. |
| `src/qopt/maxcut.py` | `cut_value(graph, bitstring)`: scores a partition. `MaxCutResult`: what every solver returns (`bitstring`, `cut_value`). |
| `src/qopt/classical/greedy.py` | `greedy_max_cut(graph)`: fast, deterministic heuristic. |
| `src/qopt/classical/annealing.py` | `simulated_annealing(graph, seed, ...)`: randomized local search. |
| `src/qopt/classical/brute_force.py` | `brute_force_max_cut(graph)`: exact answer for graphs of ≤ 20 nodes (the reference). |
| `tests/` | 93 pytest tests. |
| `scripts/demo_phase1.py` | Runs all three solvers on random graphs of 6–18 nodes. |
| `pyproject.toml` | Makes `qopt` installable (`pip install -e .`) and configures pytest. |

## Key concepts

### The Max-Cut problem
You have a graph: dots (nodes) joined by lines (edges). Split the nodes into
two groups. An edge is **cut** when its two ends land in different groups.
**Max-Cut** asks for the split that cuts as many edges as possible.

It's simple to state but **NP-hard**: no known algorithm solves every case
quickly. That's why it's a popular test problem for QAOA.

### Bitstrings
A split is written as a string of `0`s and `1`s: `bitstring[i]` is node
*i*'s group. For a triangle (edges 0-1, 1-2, 2-0), `"100"` puts node 0 alone,
which cuts edges 0-1 and 2-0, so the cut value is 2. Flipping every bit
(`"011"`) describes the same split, so it has the same cut value.

This matters for Phase 2: a quantum computer measures qubits as bitstrings,
so QAOA's output plugs straight into `cut_value`. (One catch for later:
Qiskit prints bitstrings with qubit 0 on the **right**. Phase 2 will convert
explicitly.)

### Random graphs: G(n, p)
`generate_random_graph(n, density, seed)` makes an *Erdős–Rényi* graph: each
of the n(n−1)/2 possible edges is included with probability `density`.
The **seed** fixes the random number generator, so the same inputs always
give the same graph. That makes experiments reproducible. Invalid input
(0 nodes, density 1.5, a float seed, …) raises an error immediately instead
of silently producing a weird graph.

### Solver 1: brute force (exact)
Try every possible split and keep the best. With n nodes there are 2ⁿ splits,
or 2ⁿ⁻¹ if we use the "flip everything" symmetry and fix node 0 in group 0.
The answer is guaranteed optimal, but the work **doubles with every extra
node**: 18 nodes is ~131k splits, 30 nodes would be ~537 million. We cap it
at 20 nodes. Scoring uses NumPy over all splits at once, which keeps it fast
in Python. It is the **reference answer** every other solver, and later
QAOA, is measured against.

### Solver 2: greedy
Go through nodes 0, 1, 2, … and put each one in whichever group cuts more
edges to the nodes already placed. It is very fast (one pass) and always cuts
**at least half** of all edges, but it never revisits a decision, so it can
miss the optimum (see 18 nodes in the demo below).

### Solver 3: simulated annealing (SA)
Inspired by slowly cooling metal. Start with a random split and repeatedly
pick a random node and consider moving it to the other group:
- if the cut doesn't get worse, accept the move;
- if it gets worse by `|delta|`, still accept it with probability
  `exp(delta / T)`.

The "temperature" **T** starts high (lots of bad moves accepted, which helps
escape dead ends) and drops steadily toward 0, when only improvements are
accepted. We return the best split ever seen. SA has no optimality guarantee,
but it's a strong, widely used baseline. Same seed means same result.

### Approximation ratio
`ratio = solver's cut / optimal cut`. 1.000 means the optimum was found.
This is the main metric we will use to compare QAOA with these baselines.

## Demo output (real run, this machine)

```
Random graphs: density=0.5, seed=42
ratio = solver cut / optimal cut (1.000 = found the optimum)

nodes edges | solver      cut  ratio  time ms  bitstring
--------------------------------------------------------
    6     9 | exact         7  1.000     0.36  011100
            | greedy        7  1.000     0.03  001011
            | annealing     7  1.000   148.48  001011

   10    21 | exact        15  1.000     0.33  0111100010
            | greedy       15  1.000     0.05  0011100011
            | annealing    15  1.000    12.56  0111100010

   14    47 | exact        33  1.000     2.90  00110110110100
            | greedy       33  1.000     0.09  00100110110101
            | annealing    33  1.000    16.92  11011001001010

   18    75 | exact        51  1.000   246.17  011100001110001110
            | greedy       49  0.961     0.06  001110001110001100
            | annealing    51  1.000    19.02  100010111000100110
```

What it shows:
- Brute-force time grows exponentially (≈0.3 ms → 246 ms from 10 to 18
  nodes), while greedy and SA stay roughly flat.
- Greedy is near-instant but fell short at 18 nodes (49 vs 51).
- SA found the optimum every time here. That's on small graphs; it isn't
  guaranteed in general.
- Different optimal solvers can return different bitstrings with the same
  cut value. Max-Cut often has several optimal splits.
- SA's 148 ms on the 6-node graph is a one-off first-call warm-up, not the
  algorithm. Timings are single runs, so they're noisy; Phase 4 will repeat
  runs properly.

## How to run it

From the project root, in PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1                                   # activate the venv (Python 3.14)
python -m pip install --only-binary=:all: -r requirements.txt  # only needed once
python -m pip install -e .                                     # makes `import qopt` work; once
python -m pytest -q                                            # run the tests
python scripts\demo_phase1.py                                  # run the demo
```

`pip install -e .` ("editable install") registers the `src/qopt` folder with
the venv, so `import qopt` works from tests, scripts and (later) the web app,
and edits to the code take effect without reinstalling.
