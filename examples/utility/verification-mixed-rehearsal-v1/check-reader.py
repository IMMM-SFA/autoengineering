"""Reconstruct the sealed three-family rehearsal without original sources or models."""

import builtins
from collections import Counter
import importlib
import io
import json
import os
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner
from autoengineering.cli import cli
from autoengineering.campaign.artifacts import read_bytes
from autoengineering.campaign.controller import CampaignController
from autoengineering.utility.confirmation import read_manifest, validate_manifest, SelectedState
from autoengineering.utility.controller import UtilityController
from autoengineering.utility.costs import join_batch_costs, reconcile
from autoengineering.utility.engineering_native import native_cost_records
from autoengineering.utility.engineering_campaign import EngineeringCampaign
from autoengineering.utility.store import SuiteStore

root = Path("examples/utility/development/mixed-v5").absolute()
forbidden = (root / "engineering-preparation/captured", root / "solar-preparation/source")
original_import = importlib.import_module


def denied(*args, **kwargs):
    raise AssertionError("Offline reconstruction attempted physical/network dispatch")


def guarded_import(name, *args, **kwargs):
    if name.startswith(("examples.", "pvlib", "openmdao")):
        raise AssertionError("Offline reconstruction imported a scientific implementation")
    return original_import(name, *args, **kwargs)


def guarded_open(original):
    def opened(path, *args, **kwargs):
        if not isinstance(path, int):
            candidate = Path(os.fsdecode(path)).absolute()
            if any(candidate.is_relative_to(p) for p in forbidden):
                raise AssertionError("Offline reconstruction accessed original captured inputs")
        return original(path, *args, **kwargs)

    return opened


with (
    patch("subprocess.Popen", denied),
    patch("socket.socket", denied),
    patch("importlib.import_module", guarded_import),
    patch("os.open", guarded_open(os.open)),
    patch("builtins.open", guarded_open(builtins.open)),
    patch("io.open", guarded_open(io.open)),
):
    store = SuiteStore(root / "suite")
    state = store.replay()
    assert state["frozen"] is not None
    manifest = read_manifest(store.root, state["frozen"])
    validate_manifest(store, manifest, state["attempts"], state["events"])
    controller = UtilityController(store)
    task_for_cell = {c.digest: c.task_id for c in store.spec.cells}
    tasks, statuses, cells, reservations, stops = Counter(), Counter(), [], {}, {}
    large = 0
    cost_records, cost_children = [], set()
    for selected in manifest.cells:
        allocation, status = state["attempts"][selected.attempt_id]
        assert status == "finished"
        controller.verify_result(selected.attempt_id)
        child, bindings = controller._child(allocation.child_digest)
        case = next(b.case_id for b in bindings if b.cell_digest == selected.cell_digest)
        if child.digest not in cost_children:
            cost_records.extend(
                join_batch_costs(child, {b.case_id: b.cell_digest for b in bindings})
            )
            cost_children.add(child.digest)
        projection = child.replay()
        assert not projection.pending
        reservations.update(projection.reservations)
        stops.update(projection.observations)
        task = task_for_cell[selected.cell_digest]
        tasks[task] += 1
        if task == "circuit":
            science = EngineeringCampaign(
                child.root / "cases" / case / "engineering", child
            ).state()
            for report in science["native_reports"]:
                cost_records.extend(native_cost_records(report, selected.cell_digest))
        else:
            science = CampaignController.open(
                child.root / "cases" / case / "campaign", inspect_only=True
            ).state()
        if selected.status != "selected":
            cells.append(
                {
                    "cell": selected.cell_digest,
                    "task": task,
                    "status": selected.status,
                    "reason": selected.reason,
                }
            )
            continue
        bound = SelectedState.from_json(read_bytes(store.root, selected.selected_state).decode())
        if task == "circuit":
            assert science["selected"] == bound
        else:
            assert any(e == bound.evaluation for e in science.evaluations)
            if bound.candidate is not None:
                assert bound.candidate in science.snapshots
        for ref in bound.model.source_bundle:
            read_bytes(store.root, ref)
        large += sum(ref.size_bytes > 65536 for ref in (selected.model, selected.selected_state))
        statuses[bound.evaluation.status] += 1
        cells.append(
            {
                "cell": selected.cell_digest,
                "task": task,
                "status": selected.status,
                "state": selected.selected_state.to_dict(),
                "configuration": dict(bound.configuration),
            }
        )
    assert len(cells) == 21 and all(count == 7 for count in tasks.values())
    assert set(reservations) == set(stops)
    assert all(o.stop_verified for o in stops.values())
    assert not state["confirmation_accesses"] and not state["confirmation_scores"]
    operations = {}
    for command in ("verify", "status"):
        result = CliRunner().invoke(cli, ["utility", command, str(store.root)])
        assert result.exit_code == 0, result.output
        operations[command] = json.loads(result.output)
    cost_summary = reconcile(tuple(cost_records), tuple(r.receipt_id for r in cost_records))
    cost_document = {
        "records": [r.to_dict() for r in cost_records],
        "reconciliation": cost_summary,
        "scope": "Batch reservations/receipt durations and native driver/inner counters; not total cost",
        "human_effort": "not_recorded",
        "inclusive_wall_time": "not_joined",
        "CPU_GPU_time_energy": "not_joined",
        "complete_cost_evidence": False,
    }
    summary = {
        "assigned_cells": len(cells),
        "selected_cells": sum(c.status == "selected" for c in manifest.cells),
        "selection_outcomes": dict(Counter(c.status for c in manifest.cells)),
        "tasks": dict(tasks),
        "evaluations": dict(statuses),
        "physical_reservations": dict(Counter(r.resource for r in reservations.values())),
        "physical_statuses": dict(Counter(o.status for o in stops.values())),
        "all_stops_verified": True,
        "large_selected_artifacts": large,
        "cells": cells,
        "suite_selection": state["frozen"],
        "public_commands": operations,
        "model_imports": "denied",
        "physical_network_dispatch": "denied",
        "original_captured_input_access": "denied",
        "confirmation": "not_attempted",
        "utility_verdict": "not_attempted",
        "relocation": "not_qualified",
        "complete_cost_evidence": False,
        "partial_cost_reconciliation": cost_summary,
    }
Path("examples/utility/verification-mixed-rehearsal-v1/partial-costs.json").write_text(
    json.dumps(cost_document, indent=2) + "\n"
)
Path("examples/utility/verification-mixed-rehearsal-v1/offline-reader.json").write_text(
    json.dumps(summary, indent=2) + "\n"
)
print(
    json.dumps(
        {
            k: v
            for k, v in summary.items()
            if k not in ("cells", "public_commands", "partial_cost_reconciliation")
        }
    )
)
