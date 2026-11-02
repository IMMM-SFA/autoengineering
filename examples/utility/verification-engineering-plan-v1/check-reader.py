"""Read archived engineering selections without a model runtime or source access."""

import importlib
import json
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner
from autoengineering.cli import cli
from autoengineering.campaign.artifacts import read_bytes
from autoengineering.utility.confirmation import read_manifest, validate_manifest, SelectedState
from autoengineering.utility.controller import UtilityController
from autoengineering.utility.engineering_campaign import EngineeringCampaign
from autoengineering.utility.store import SuiteStore

root = Path("examples/utility/development/engineering-plan-v1").absolute()
original = importlib.import_module


def denied(*args, **kwargs):
    raise AssertionError("Offline read attempted scientific or network dispatch")


def guarded(name, *args, **kwargs):
    if name.startswith(
        ("openmdao", "examples.utility.engineering", "examples.interoperability.circuit")
    ):
        raise AssertionError("Offline read imported a scientific implementation")
    return original(name, *args, **kwargs)


def archived_only(source, ref, *args, **kwargs):
    if Path(source).absolute() == root / "captured":
        raise AssertionError("Offline read accessed original source root")
    return read_bytes(source, ref, *args, **kwargs)


with (
    patch("subprocess.Popen", denied),
    patch("socket.socket", denied),
    patch("importlib.import_module", guarded),
    patch("autoengineering.utility.engineering_process.supervise_process", denied),
    patch("autoengineering.utility.engineering_process.recover_completed_process", denied),
    patch("autoengineering.utility.engineering_native.supervise_process", denied),
    patch("autoengineering.utility.engineering_native.recover_completed_process", denied),
    patch("autoengineering.utility.confirmation.read_bytes", archived_only),
    patch("autoengineering.utility.engineering_campaign.read_bytes", archived_only),
    patch("autoengineering.utility.engineering_native.read_bytes", archived_only),
):
    store = SuiteStore(root / "suite")
    state = store.replay()
    manifest = read_manifest(store.root, state["frozen"])
    validate_manifest(store, manifest, state["attempts"], state["events"])
    controller = UtilityController(store)
    cells = []
    for selected in manifest.cells:
        assert selected.status == "selected"
        bound = SelectedState.from_json(read_bytes(store.root, selected.selected_state).decode())
        allocation, status = state["attempts"][selected.attempt_id]
        controller.verify_result(selected.attempt_id)
        child, bindings = controller._child(allocation.child_digest)
        case = next(b.case_id for b in bindings if b.cell_digest == selected.cell_digest)
        science = EngineeringCampaign(child.root / "cases" / case / "engineering", child).state()
        assert science["selected"] == bound
        for ref in bound.model.source_bundle:
            archived_only(store.root, ref)
        cells.append(
            {
                "cell": selected.cell_digest,
                "configuration": dict(bound.configuration),
                "state_sha256": selected.selected_state.sha256,
            }
        )
    runner = CliRunner()
    operations = {}
    for command in ("verify", "status"):
        result = runner.invoke(cli, ["utility", command, str(store.root)])
        assert result.exit_code == 0, result.output
        operations[command] = json.loads(result.output)
    assert not state["confirmation_accesses"] and not state["confirmation_scores"]
    report = {
        "selected_cells": len(cells),
        "suite_selection": state["frozen"],
        "cells": cells,
        "operations": operations,
        "scientific_registration_imports": "denied",
        "physical_network_dispatch": "denied",
        "original_source_root_access": "denied",
        "runtime": "base environment without OpenMDAO",
        "utility_verdict": "not_attempted",
        "scope_limit": "Original archive location; relocation remains unqualified",
    }
Path("examples/utility/verification-engineering-plan-v1/offline-reader.json").write_text(
    json.dumps(report, indent=2) + "\n"
)
print(json.dumps({k: v for k, v in report.items() if k not in ("cells", "operations")}))
