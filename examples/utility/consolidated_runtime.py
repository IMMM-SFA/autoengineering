"""Trusted scientific selection entry points for the consolidated study.

Inputs are supplied by the trusted broker, never arbitrary worker paths. These
kernels do not select data, open confirmation files or invoke agents. The process
supervisor below enforces a permanently charged, shared selection-time allowance.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
from pathlib import Path
import time

import numpy as np

from autoengineering.adapters.python import run_lifecycle
from autoengineering.agents.process import supervise_process
from autoengineering.campaign.serialization import digest
from autoengineering.campaign.store import checked_directory
from examples.utility.consolidated_sources import save


def hydrology(plan, forcing, labels, configuration, scratch):
    from examples.utility.hydrology import physical_checks
    from examples.utility.hydrology_site import SiteHydrologyAdapter, prepared_development

    if (
        set(configuration) != {"capacity", "recession", "pet"}
        or not 20 <= configuration["capacity"] <= 200
        or not 0.05 <= configuration["recession"] <= 0.95
        or configuration["pet"] not in ("hamon", "hargreaves")
    ):
        raise ValueError("Hydrology configuration exceeds the shared domain")
    site, ctx, arrays = prepared_development(
        plan, forcing, configuration, scratch, role="selection"
    )
    mask = np.asarray(labels["mask"], dtype=bool)
    expected = np.asarray(ctx.model.outputs[0].time.scoring_mask)
    if mask.shape != expected.shape or np.any(mask & ~expected) or not mask.any():
        raise ValueError("Hydrology labels differ from the selection partition")
    result = run_lifecycle(
        SiteHydrologyAdapter(site), ctx, arrays, ctx.model.inputs, ctx.model.outputs
    )
    checks = physical_checks(result.outputs, arrays, configuration)
    if any(c.status != "pass" for c in checks):
        raise ValueError("Hydrology physical checks failed")
    p, y = result.outputs["prediction"][mask], np.asarray(labels["labels"])[mask]
    if not np.isfinite(y).all() or y.sum() <= 0:
        raise ValueError("Hydrology reference values are invalid")
    return {
        "discharge_rmse": float(np.sqrt(np.mean((p - y) ** 2))),
        "volume_bias": float(p.sum() / y.sum() - 1),
        "model_starts": 1,
    }


def solar(data, configuration):
    from examples.utility.solar_1278_inputs import evaluate

    if set(configuration) != {"scale"}:
        raise ValueError("Solar selection admits only the common effective derating")
    return evaluate(data, configuration["scale"]) | {"model_starts": 1}


def engineering(rows, configuration, scratch):
    from examples.utility import engineering_load as load
    from examples.utility.engineering_load_scoring import _cases

    if set(configuration) != {"source_current"}:
        raise ValueError("Engineering selection admits only source current")
    current = configuration["source_current"]
    if not math.isfinite(current) or not 0.01 <= current <= 0.1:
        raise ValueError("Engineering current exceeds the shared domain")
    powers, voltages, residuals = [], [], []
    for i, row in enumerate(_cases(rows)):
        case = Path(scratch) / f"case-{i:02d}"
        case.mkdir(mode=0o700, exist_ok=False)
        ctx = load.context(current, case)
        forcing = {k: np.asarray(v, dtype=float) for k, v in row["forcing"].items()}
        result = run_lifecycle(load.adapter(), ctx, forcing, ctx.model.inputs, ctx.model.outputs)
        powers.append(
            current * (float(result.outputs["node1_voltage"]) - row["forcing"]["ground_voltage"])
        )
        voltages.append(float(result.outputs["node2_voltage"]))
        residuals.append(float(result.diagnostics["residual_norm"]))
    if not np.isfinite(powers + voltages + residuals).all():
        raise ValueError("Engineering selection has nonfinite output")
    return {
        "mean_source_power": float(np.mean(powers)),
        "worst_case_power": max(powers),
        "minimum_node2_voltage": min(voltages),
        "maximum_residual": max(residuals),
        "feasible": min(voltages) >= 0.62 and max(residuals) <= 1e-10 and min(powers) >= 0,
        "model_starts": 24,
    }


def wind(profiles, configuration):
    if tuple(p.year for p in profiles) != (2010, 2011):
        raise ValueError("Wind selection requires both declared development years")
    energies = [float(profile.physical({}, configuration)["annual_energy"]) for profile in profiles]
    return {
        "mean_annual_energy": float(np.mean(energies)),
        "annual_energy": energies,
        "model_starts": 2,
    }


@dataclass(frozen=True)
class SelectionBudget:
    seconds: float = 600.0
    evaluations: int = 8
    host_invocations: int = 12

    def __post_init__(self):
        if (
            not 0 < self.seconds <= 600
            or not 1 <= self.evaluations <= 32
            or not 0 <= self.host_invocations <= 12
        ):
            raise ValueError("Selection budget exceeds the consolidated cap")


class SelectionSupervisor:
    """One parent-owned budget per cell; uncertain child attempts are never retried.

    Reserve full timeouts, not observed elapsed time, so owner loss cannot erase
    charges. The parent watchdog terminates owned children on parent loss. This
    process boundary is not a filesystem sandbox or a live-agent permission grant.
    """

    def __init__(self, root, cell_digest, budget):
        self.root = checked_directory(root)
        if len(cell_digest) != 64 or any(c not in "0123456789abcdef" for c in cell_digest):
            raise ValueError("Selection cell needs its immutable digest")
        self.budget = budget
        self.binding = {
            "cell_digest": cell_digest,
            "seconds": budget.seconds,
            "evaluations": budget.evaluations,
            "host_invocations": budget.host_invocations,
        }
        path = self.root / "binding.json"
        if path.exists():
            if json.loads(path.read_text()) != self.binding:
                raise ValueError("Selection budget or cell cannot change on resume")
        else:
            if any(self.root.iterdir()):
                raise ValueError("Selection supervisor requires an empty scope")
            from autoengineering.campaign.store import EventStore

            EventStore.create(self.root / "lock-store")
            save(path, self.binding)

    def run(
        self, request_id, command, *, cwd, environment, stdin=b"", seconds=60, kind="scientific"
    ):
        from autoengineering.utility.contracts import identifier
        from autoengineering.campaign.store import EventStore

        identifier(request_id)
        if kind not in ("scientific", "host"):
            raise ValueError("Unknown selection operation kind")
        # EventStore's writer uses the project's advisory single-writer lock.
        store = EventStore(self.root / "lock-store")
        with store.writer():
            intents = [json.loads(p.read_text()) for p in self.root.glob("*-intent.json")]
            if any(x["request_id"] == request_id for x in intents):
                raise ValueError("Consumed selection attempt cannot be redispatched")
            if (
                sum(x["kind"] == kind for x in intents)
                >= (
                    self.budget.evaluations
                    if kind == "scientific"
                    else self.budget.host_invocations
                )
                or not 0 < seconds <= 600
                or sum(x["seconds_reserved"] for x in intents) + seconds > self.budget.seconds
            ):
                raise ValueError("Selection allowance exhausted")
            intent = {
                "request_id": request_id,
                "kind": kind,
                "seconds_reserved": seconds,
                "command_digest": digest(list(command)),
                "stdin_digest": digest(stdin.hex()),
            }
            save(self.root / f"{request_id}-intent.json", intent)
            start = time.monotonic()
            result = supervise_process(
                tuple(command),
                directory=self.root / request_id,
                cwd=Path(cwd),
                environment=environment,
                nonce=request_id,
                stdin=stdin,
                timeout_seconds=seconds,
                max_output_bytes=65536,
                on_launch=lambda event: save(self.root / f"{request_id}-launch.json", event),
                parent_watchdog=True,
            )
            save(
                self.root / f"{request_id}-result.json",
                {
                    "status": result.status,
                    "returncode": result.returncode,
                    "elapsed_seconds": time.monotonic() - start,
                    "stopped": result.stopped,
                    "output_truncated": result.truncated,
                },
            )
            return result
