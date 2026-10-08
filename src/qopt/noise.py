"""Named, illustrative noise levels for the Qiskit Aer simulator.

These numbers are ILLUSTRATIVE, chosen to span "fairly clean" to "very
noisy". They are NOT a calibrated model of any real quantum device.

Noise model (deliberately simple, every number visible below):
- After every one-qubit gate (h, rz, rx): a depolarizing error. With
  probability ``one_qubit_error`` the qubit's state is replaced by a
  completely random one.
- After every two-qubit gate (cx): the same, on both qubits, with
  probability ``two_qubit_error``.
- At measurement: each measured bit is flipped with probability
  ``readout_error`` (0 read as 1, or 1 read as 0).
"""

from dataclasses import dataclass

from qiskit.circuit import QuantumCircuit
from qiskit_aer.noise import NoiseModel, ReadoutError, depolarizing_error

# The gates our QAOA circuit is built from (see qaoa.build_qaoa_circuit).
ONE_QUBIT_GATES = ("h", "rz", "rx")
TWO_QUBIT_GATES = ("cx",)
# Instructions that need no noise: barrier is only a drawing/ordering marker.
NOISELESS_INSTRUCTIONS = {"barrier"}


@dataclass(frozen=True)
class NoiseLevel:
    name: str
    one_qubit_error: float  # depolarizing probability after h, rz, rx
    two_qubit_error: float  # depolarizing probability after cx
    readout_error: float  # probability each measured bit is flipped


NOISE_LEVELS: dict[str, NoiseLevel] = {
    level.name: level
    for level in [
        NoiseLevel("none", one_qubit_error=0.0, two_qubit_error=0.0, readout_error=0.0),
        NoiseLevel("low", one_qubit_error=0.001, two_qubit_error=0.01, readout_error=0.01),
        NoiseLevel("medium", one_qubit_error=0.005, two_qubit_error=0.03, readout_error=0.03),
        NoiseLevel("high", one_qubit_error=0.01, two_qubit_error=0.08, readout_error=0.05),
    ]
}


def get_noise_level(name: str) -> NoiseLevel:
    """Look up a noise level by name; raise ValueError listing valid names."""
    if name not in NOISE_LEVELS:
        raise ValueError(
            f"unknown noise level {name!r}; choose one of {list(NOISE_LEVELS)}"
        )
    return NOISE_LEVELS[name]


def build_noise_model(level: NoiseLevel) -> NoiseModel | None:
    """Return the Aer noise model for ``level``, or None for "none".

    None means "run the plain ideal simulator", exactly as in Phase 2.
    Every other level needs all three rates in (0, 1): Aer silently drops an
    error whose probability is 0, which would leave those gates noiseless.
    """
    if level.name == "none":
        return None
    rates = (level.one_qubit_error, level.two_qubit_error, level.readout_error)
    if not all(0 < r < 1 for r in rates):
        raise ValueError(f"noisy level {level.name!r} needs all rates in (0, 1), got {rates}")
    model = NoiseModel()
    model.add_all_qubit_quantum_error(
        depolarizing_error(level.one_qubit_error, 1), list(ONE_QUBIT_GATES)
    )
    model.add_all_qubit_quantum_error(
        depolarizing_error(level.two_qubit_error, 2), list(TWO_QUBIT_GATES)
    )
    p = level.readout_error
    model.add_all_qubit_readout_error(ReadoutError([[1 - p, p], [p, 1 - p]]))
    return model


def check_noise_covers_circuit(circuit: QuantumCircuit, model: NoiseModel) -> None:
    """Raise if the circuit uses an instruction the noise model doesn't touch.

    Guards against a classic silent bug: a noise model attached to gate
    names the circuit never uses, so "noisy" runs are secretly ideal.
    """
    used = set(circuit.count_ops()) - NOISELESS_INSTRUCTIONS
    missing = used - set(model.noise_instructions)
    if missing:
        raise ValueError(f"noise model has no errors for instructions {sorted(missing)}")
