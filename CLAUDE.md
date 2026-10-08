# Q-Opt Lab

Portfolio project. Research question:
"How does QAOA compare with classical optimization for the Max-Cut problem
as problem size and simulated quantum noise increase?"

Roadmap (build one phase at a time, never ahead):
1. Max-Cut + classical baselines  2. QAOA  3. Noise simulation
4. Experiment runner  5. Analysis plots  6. FastAPI + React web app  7. Docker deployment

## About the user
- CS student, no quantum background: explain concepts at beginner level.
- Windows laptop, 4 GB RAM: keep everything lightweight (small graphs, few qubits).

## Environment
- Python **3.14** in `.venv` (created with `py -3.14 -m venv .venv`).
  The system default `python` is 3.10, so always use the venv's interpreter.
- Activate (PowerShell): `.\.venv\Scripts\Activate.ps1`
- Install: `python -m pip install --only-binary=:all: -r requirements.txt`
  (wheels only: never build packages from source on this machine).

## Rules for every phase
- Build only the phase the user asks for, then STOP and wait for approval.
- Run tests and a small demo, and show the real output.
- Write `docs/phase-N-notes.md`: what was built, key concepts, how to run it.
- Give the exact commands to run the tests and the demo.
- Never fake or hardcode results. Never claim quantum advantage.
- Type hints, modular code, tests, no unnecessary dependencies or abstractions.

## Git
- NEVER run `git commit`, `git push`, or any command that changes git history
  (amend, rebase, reset, merge, tag, etc.). The user makes all commits.
- At the end of each phase, suggest a commit message and list the changed files.
