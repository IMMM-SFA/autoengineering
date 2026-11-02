"""Reconstruct the final retained native result with scientific dispatch denied."""

import importlib
import json
from pathlib import Path
from unittest.mock import patch

from autoengineering.agents.batch import BatchStore
from autoengineering.utility.engineering_campaign import EngineeringCampaign
from autoengineering.utility.engineering_native import native_cost_records

root = Path("examples/utility/development/engineering-native-v2").absolute()
original = importlib.import_module


def denied(*args, **kwargs):
    raise AssertionError("Offline read attempted physical or network dispatch")


def guarded(name, *args, **kwargs):
    if name.startswith(
        ("openmdao", "examples.utility.engineering", "examples.interoperability.circuit")
    ):
        raise AssertionError("Offline read imported scientific implementation")
    return original(name, *args, **kwargs)


with (
    patch("subprocess.Popen", denied),
    patch("socket.socket", denied),
    patch("importlib.import_module", guarded),
    patch("autoengineering.utility.engineering_native.supervise_process", denied),
    patch("autoengineering.utility.engineering_native.recover_completed_process", denied),
    patch("autoengineering.utility.engineering_process.supervise_process", denied),
    patch("autoengineering.utility.engineering_process.recover_completed_process", denied),
):
    batch = BatchStore(root / "batch")
    state = EngineeringCampaign(root / "campaign", batch).state()
    summary = json.loads((root / "summary.json").read_text())
    assert state["selected"].to_dict() == summary["selected_state"]
    assert state["decision"].to_dict() == summary["decision"]
    report = state["native_reports"][0]
    assert report.result.schema == "utility-native-result-v2"
    native = next(v for v in state["evaluations"] if v.evaluation.id.startswith("native-choice-"))
    assert native.evaluation.id not in state["decision"].eligible_alternatives
    result = {
        "state": state["projection"].state,
        "native_driver_status": report.status,
        "outer_reservations": len(batch.replay().reservations),
        "native_inner_model_calls": len(report.result.solves),
        "native_scenario_checks": [c.to_dict() for s in native.scenarios for c in s.checks],
        "selected_configuration": dict(state["selected"].configuration),
        "native_cost_quantities": {
            r.resource: r.quantity for r in native_cost_records(report, "0" * 64)
        },
        "scientific_process_network_dispatch": "denied",
        "scientific_registration_imports": "denied",
        "utility_verdict": "not_attempted",
    }
Path("examples/utility/verification-engineering-native-v1/offline-reader.json").write_text(
    json.dumps(result, indent=2) + "\n"
)
print(json.dumps({k: v for k, v in result.items() if k != "native_scenario_checks"}))
