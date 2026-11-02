"""Account for circuit work in native driver passes without scoring a design.

OpenMDAO pre/post optimization passes can retain circuit diagnostics without
executing that subsystem. Cumulative counters describe the problem lifetime;
their deltas distinguish work observed in this pass. No model is imported here.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from autoengineering.campaign.serialization import Record

COUNTERS = ("component_calls", "component_linearize_calls")


@dataclass(frozen=True)
class CircuitPassWork(Record):
    schema: Literal["utility-circuit-native-pass-work-v1"]
    circuit_work_observed: bool
    component_calls: int
    component_linearize_calls: int
    nonlinear_iterations_this_pass: int
    design_eligibility: Literal["not_assessed"] = "not_assessed"

    def _validate(self):
        if (
            min(
                self.component_calls,
                self.component_linearize_calls,
                self.nonlinear_iterations_this_pass,
            )
            < 0
        ):
            raise ValueError("native circuit work cannot be negative")
        touched = self.component_calls > 0 or self.component_linearize_calls > 0
        if self.circuit_work_observed != touched or (
            not touched and self.nonlinear_iterations_this_pass != 0
        ):
            raise ValueError("retained circuit diagnostics cannot become fresh work")


def account_circuit_pass(
    before: Mapping[str, int], after: Mapping[str, int], *, diagnostic_solver_iterations: int
) -> CircuitPassWork:
    """Preserve observed deltas; never infer scientific eligibility from return.

    Reset/decreasing counters refuse because their actual work cannot be recovered
    by subtraction. The raw diagnostic snapshot belongs in the caller's receipt.
    Final candidate checks remain separate, including when all deltas are zero.
    """
    if (
        not isinstance(before, Mapping)
        or not isinstance(after, Mapping)
        or set(before) != set(COUNTERS)
        or set(after) != set(COUNTERS)
        or type(diagnostic_solver_iterations) is not int
        or diagnostic_solver_iterations < 0
        or any(type(value) is not int or value < 0 for value in (*before.values(), *after.values()))
    ):
        raise ValueError("native circuit counters must be exact nonnegative integers")
    deltas = {name: after[name] - before[name] for name in COUNTERS}
    if any(value < 0 for value in deltas.values()):
        raise ValueError("native circuit counter reset requires separate accounting")
    touched = any(deltas.values())
    return CircuitPassWork(
        "utility-circuit-native-pass-work-v1",
        touched,
        deltas["component_calls"],
        deltas["component_linearize_calls"],
        diagnostic_solver_iterations if touched else 0,
    )
