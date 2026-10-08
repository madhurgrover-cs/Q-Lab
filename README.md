# Q-Opt Lab

**Research question:** How does QAOA compare with classical optimization for
the Max-Cut problem as problem size and simulated quantum noise increase?

This project measures and reports what happens. It makes no claim of quantum
advantage.

## Status

| Phase | Contents | Status |
|---|---|---|
| 1 | Max-Cut + classical baselines (greedy, simulated annealing, exact brute force) | done |
| 2 | QAOA | — |
| 3 | Noise simulation | — |
| 4 | Experiment runner | — |
| 5 | Analysis plots | — |
| 6 | FastAPI + React web app | — |
| 7 | Docker deployment | — |

Phase notes: [docs/phase-1-notes.md](docs/phase-1-notes.md)

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
```
