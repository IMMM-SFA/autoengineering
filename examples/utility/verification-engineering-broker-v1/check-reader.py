"""Reconstruct the final engineering routes without models, processes or network."""

import importlib
import json
from pathlib import Path
from unittest.mock import patch

from autoengineering.agents.store import WorkerStore
from autoengineering.campaign.artifacts import read_bytes
from autoengineering.utility.controller import UtilityController
from autoengineering.utility.engineering_broker import engineering_recipe_identity
from autoengineering.utility.engineering_campaign import EngineeringCampaign
from autoengineering.utility.routes import RoutePlan
from autoengineering.utility.store import SuiteStore

root = Path("examples/utility/development/engineering-routes-v3").absolute()
original_import = importlib.import_module


def denied(*args, **kwargs):
    raise AssertionError("Offline reconstruction attempted dispatch")


def guarded(name, *args, **kwargs):
    if name.startswith(
        ("openmdao", "examples.utility.engineering", "examples.interoperability.circuit")
    ):
        raise AssertionError("Offline reconstruction imported a scientific implementation")
    return original_import(name, *args, **kwargs)


with (
    patch("subprocess.Popen", denied),
    patch("socket.socket", denied),
    patch("importlib.import_module", guarded),
    patch("autoengineering.utility.engineering_process.supervise_process", denied),
    patch("autoengineering.utility.engineering_process.recover_completed_process", denied),
    patch("autoengineering.utility.engineering_native.supervise_process", denied),
    patch("autoengineering.utility.engineering_native.recover_completed_process", denied),
):
    store = SuiteStore(root / "suite")
    controller = UtilityController(store)
    plan = RoutePlan.from_json((root / "route-plan.json").read_text())
    projected = store.replay()
    rows = []
    for cell in store.spec.cells:
        allocation, status = projected["attempts"]["child-" + cell.digest[:48]]
        assert status == "finished"
        controller.verify_result(allocation.attempt_id)
        batch, bindings = controller._child(allocation.child_digest)
        binding = next(b for b in bindings if b.cell_digest == cell.digest)
        case_root = batch.root / "cases" / binding.case_id
        campaign = EngineeringCampaign(case_root / "engineering", batch)
        state = campaign.state()
        assert state["projection"].state == "selection_frozen"
        assert campaign.spec.execution.study.run.study.seed == cell.seed
        recipe = next(r.recipe for r in plan.task_routes if r.route_id == cell.route_id)
        assert recipe.numerical_recipe_digest == engineering_recipe_identity(campaign.spec)
        physical = batch.replay()
        science = [r for r in physical.reservations.values() if r.resource == "science"]
        assert all(physical.observations[r.id].stop_verified for r in science)
        workers = WorkerStore(case_root / "worker") if (case_root / "worker").exists() else None
        if workers:
            worker = workers.replay()
            roles = {t.role for t in worker.tasks.values()}
            if cell.route_id.startswith("no_"):
                assert cell.route_id.removeprefix("no_") not in roles
            if cell.route_id == "single_agent":
                assert roles == {"single_agent"}
            for task in worker.tasks.values():
                summary = json.loads(read_bytes(workers.root, task.grants[0].artifact).decode())
                assert (
                    summary["parameter_domain"]
                    == campaign.spec.execution.study.run.search_space.to_dict()
                )
                assert summary["scenarios"] == [
                    s.to_dict() for s in campaign.spec.execution.scenarios
                ]
                assert summary["numerical_recipe"]["paired_seed"] == cell.seed
        rows.append(
            {
                "route": cell.route_id,
                "seed": cell.seed,
                "scientific_processes": len(science),
                "host_calls": len(workers.replay().invocations) if workers else 0,
                "native_jobs": len(state["native_reports"]),
                "native_inner_model_calls": sum(
                    len(r.result.solves) for r in state["native_reports"] if r.result
                ),
                "selected_configuration": dict(state["selected"].configuration)
                if state["selected"]
                else None,
            }
        )
    assert sum(r["scientific_processes"] for r in rows) == 99
    assert sum(r["host_calls"] for r in rows) == 85
    assert len({r["seed"] for r in rows}) == 1
    assert len(projected["mechanical_steps"]) == 10
    assert projected["used"][("fixed_evaluations", "host_invocations")] == 150
    assert not projected["confirmation_accesses"] and not projected["confirmation_scores"] and projected["frozen"] is None
    result = {
        "cells": rows,
        "source": "original parent/child/worker/campaign journals",
        "scientific_process_network_dispatch": "denied",
        "scientific_registration_imports": "denied",
        "finished_cells": len(rows),
        "scientific_processes": 99,
        "host_calls": 85,
        "mechanical_steps": 10,
        "reserved_host_allowance": 150,
        "native_inner_model_calls": sum(r["native_inner_model_calls"] for r in rows),
        "utility_verdict": "not_attempted",
        "suite_selection_barrier": "not_frozen",
    }
Path("examples/utility/verification-engineering-broker-v1/offline-reader.json").write_text(
    json.dumps(result, indent=2) + "\n"
)
print(json.dumps({k: v for k, v in result.items() if k != "cells"}))
