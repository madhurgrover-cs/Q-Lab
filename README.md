# Q-Opt Lab

**Research question:** How does QAOA compare with classical optimization for
the Max-Cut problem as problem size and simulated quantum noise increase?

This project measures and reports what happens. It makes no claim of quantum
advantage.

## Status

| Phase | Contents | Status |
|---|---|---|
| 1 | Max-Cut + classical baselines (greedy, simulated annealing, exact brute force) | done |
| 2 | QAOA (simulated with Qiskit Aer) + random-sampling baseline, multi-start optimizer | done |
| 3 | Noise simulation (illustrative noise levels, not a real-device model) | built, awaiting review |
| 4 | Experiment runner | — |
| 5 | Analysis plots | — |
| 6 | FastAPI + React web app | — |
| 7 | Docker deployment | — |

Phase notes: [Phase 1](docs/phase-1-notes.md) · [Phase 2](docs/phase-2-notes.md) · [Phase 3](docs/phase-3-notes.md)

## Setup (Windows, PowerShell)

Requires Python 3.14.

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --only-binary=:all: -r requirements.txt
python -m pip install -e .
```

## Run

```powershell
python -m pytest -q             # tests
python scripts\demo_phase1.py   # Phase 1 demo
python scripts\demo_phase2.py   # Phase 2 demo: QAOA vs baselines, restarts (~30 s)
python scripts\demo_phase3.py   # Phase 3 demo: QAOA under noise (~85 s)
```
