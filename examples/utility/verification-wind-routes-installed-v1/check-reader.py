"""Read the sealed wind route suite with science, dispatch and original sources denied."""

import argparse
import builtins
from collections import Counter
import importlib
import io
import json
import os
from pathlib import Path
import sys

import autoengineering
from unittest.mock import patch

from click.testing import CliRunner
from autoengineering.cli import cli
from autoengineering.campaign.artifacts import read_bytes
from autoengineering.utility.confirmation import SelectedState, read_manifest
from autoengineering.utility.controller import UtilityController
from autoengineering.utility.costs import join_batch_costs, reconcile
from autoengineering.utility.engineering_campaign import EngineeringCampaign
from autoengineering.utility.engineering_execution import ScriptedEngineeringPlan
from autoengineering.utility.engineering_native import native_cost_records
from autoengineering.utility.store import SuiteStore

parser = argparse.ArgumentParser()
parser.add_argument("archive", type=Path)
parser.add_argument("--forbidden", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
root = args.archive.absolute()
forbidden = args.forbidden.resolve()
assert Path(autoengineering.__file__).resolve().is_relative_to(Path(sys.prefix))
assert not Path(autoengineering.__file__).resolve().is_relative_to(forbidden)
plan = ScriptedEngineeringPlan.from_json((root / "execution-plan.json").read_text())
archive = root / "archived-sources"
original_import = importlib.import_module
original_builtin = builtins.__import__
for prefix in ("py_wake", "topfarm", "openmdao"):
    assert not any(n == prefix or n.startswith(prefix + ".") for n in sys.modules)


def denied(*args, **kwargs):
    raise AssertionError("Wind suite reader attempted scientific/network/process dispatch")


def guarded_import(name, *args, **kwargs):
    if name.startswith(("examples.", "py_wake", "topfarm", "openmdao")):
        raise AssertionError("Wind suite reader imported a scientific implementation")
    return original_import(name, *args, **kwargs)


def guarded_builtin(name, globals=None, locals=None, fromlist=(), level=0):
    if name.startswith(("examples.", "py_wake", "topfarm", "openmdao")):
        raise AssertionError("Wind suite reader imported a scientific implementation")
    return original_builtin(name, globals, locals, fromlist, level)


def guarded_open(original):
    def opened(path, *args, **kwargs):
        if not isinstance(path, int) and Path(os.fsdecode(path)).absolute().is_relative_to(
            forbidden
        ):
            raise AssertionError("Wind suite reader read original captured source")
        return original(path, *args, **kwargs)

    return opened


with (
    patch("subprocess.Popen", denied),
    patch("socket.socket", denied),
    patch("importlib.import_module", guarded_import),
    patch("builtins.__import__", guarded_builtin),
    patch("os.open", guarded_open(os.open)),
    patch("builtins.open", guarded_open(builtins.open)),
    patch("io.open", guarded_open(io.open)),
):
    store = SuiteStore(root / "suite")
    state = store.replay()
    assert state["frozen"] is not None
    manifest = read_manifest(store.root, state["frozen"])
    controller = UtilityController(store)
    assert len(manifest.cells) == 7
    reservations, observations, cells, records, children = {}, {}, [], [], set()
    scientific, callback_statuses, work = Counter(), Counter(), Counter()
    for selected in manifest.cells:
        allocation, status = state["attempts"][selected.attempt_id]
        assert status == "finished"
        controller.verify_result(selected.attempt_id)
        child, bindings = controller._child(allocation.child_digest)
        case = next(b.case_id for b in bindings if b.cell_digest == selected.cell_digest)
        if child.digest not in children:
            records.extend(join_batch_costs(child, {b.case_id: b.cell_digest for b in bindings}))
            children.add(child.digest)
        projection = child.replay()
        assert not projection.pending
        reservations.update(projection.reservations)
        observations.update(projection.observations)
        campaign = EngineeringCampaign(
            child.root / "cases" / case / "engineering", child, inspect_only=True
        )
        assert campaign.spec.schema == "utility-engineering-campaign-v3"
        saved = campaign.state()
        scientific.update(v.evaluation.status for v in saved["evaluations"])
        for report in saved["native_reports"]:
            assert report.schema == "utility-callback-report-v1"
            callback_statuses[report.status] += 1
            records.extend(native_cost_records(report, selected.cell_digest))
            if report.result:
                work.update(c.kind for c in report.result.calls)
        assert selected.status == "selected"
        bound = SelectedState.from_json(read_bytes(store.root, selected.selected_state).decode())
        assert saved["selected"] == bound
        assert bound.evaluation.eligible and bound.evaluation.status == "success"
        for ref in bound.model.source_bundle:
            read_bytes(store.root, ref)
        cells.append(
            {
                "cell": selected.cell_digest,
                "status": selected.status,
                "configuration": dict(bound.configuration),
                "metrics": dict(bound.evaluation.metrics),
                "decision": saved["decision"].outcome,
            }
        )
    assert set(reservations) == set(observations) and all(
        o.stop_verified for o in observations.values()
    )
    assert not state["confirmation_accesses"] and not state["confirmation_scores"]
    commands = {}
    for command in ("verify", "status"):
        result = CliRunner().invoke(cli, ["utility", command, str(store.root)])
        assert result.exit_code == 0, result.output
        commands[command] = json.loads(result.output)
    for ref in (*plan.source_inventory, plan.lock):
        read_bytes(archive, ref)
    cost_summary = reconcile(tuple(records), tuple(r.receipt_id for r in records))
summary = {
    "installed_package": autoengineering.__file__,
    "archive_relocation": "passed",
    "assigned_cells": 7,
    "selected_cells": 7,
    "cells": cells,
    "scientific_evaluation_statuses": dict(scientific),
    "native_report_statuses": dict(callback_statuses),
    "native_callback_entries": dict(work),
    "physical_reservations": dict(Counter(r.resource for r in reservations.values())),
    "observed_statuses": dict(Counter(o.status for o in observations.values())),
    "all_stops_verified": True,
    "source_files_verified": len(plan.source_inventory) + 1,
    "selection": state["frozen"],
    "public_commands": commands,
    "model_imports_network_dispatch": "denied",
    "original_captured_source_access": "denied_for_original_checkout",
    "complete_cost_evidence": False,
    "confirmation": "not_attempted",
    "utility_verdict": "not_attempted",
}
v = args.output
(v / "partial-costs.json").write_text(
    json.dumps(
        {
            "records": [r.to_dict() for r in records],
            "reconciliation": cost_summary,
            "human_effort": "not_recorded",
            "total_compute_time": "not_joined",
            "complete_cost_evidence": False,
        },
        indent=2,
    )
    + "\n"
)
(v / "offline-reader.json").write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps({k: v for k, v in summary.items() if k not in ("cells", "public_commands")}))
