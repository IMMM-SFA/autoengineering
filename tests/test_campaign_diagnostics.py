"""The declared causality stage is budgeted and resumable on synthetic hydrology."""

from dataclasses import replace

import numpy as np

from autoengineering.campaign.artifacts import reference
from autoengineering.campaign.controller import CampaignController
from autoengineering.campaign.records import DataContract
from autoengineering.campaign.spec import (
    AcceptanceSpec,
    BaselineSpec,
    CalibrationSpec,
    CheckSpec,
    ExecutionSpec,
    InterventionSpec,
    ProvenanceSpec,
)
from autoengineering.optimization import (
    BudgetSpec,
    ContinuousParameter,
    NoiseSpec,
    ObjectiveSpec,
    OptimizationRunSpec,
    SearchSpace,
    StudySpec,
)
from examples.campaign_contracts.build_fixture import ROOT, fixture
from examples.campaign_contracts.hydrology import SOURCES
from test_adapter_contracts import forcing_data, hydro_context


def synthetic_profile(tmp_path):
    spec = fixture()
    context = hydro_context()
    sources = (
        *spec.provenance.sources,
        *(reference(ROOT, path, media_type="text/x-python", producer="author") for path in SOURCES),
    )
    model = replace(context.model, implementations={"response": "hamon-v1"}, source_bundle=sources)
    source_root = tmp_path / "source"
    source_root.mkdir()
    for ref in (*sources, spec.baseline.system, spec.provenance.environment_lock):
        target = source_root / ref.path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / ref.path).read_bytes())
    np.savez(source_root / "forcing.npz", **forcing_data())
    data = [
        DataContract(
            "forcing",
            reference(source_root, "forcing.npz", media_type="application/x-npz", producer="test"),
            model.inputs,
            "forcing",
            "exposed",
        )
    ]
    for role, indexes in (("fitting", slice(0, 8)), ("comparison", slice(8, 12))):
        port = model.outputs[0]
        time = port.time
        time = replace(
            time,
            dates=time.dates[indexes],
            warmup_mask=time.warmup_mask[indexes],
            scoring_mask=time.scoring_mask[indexes],
        )
        port = replace(port, time=time)
        np.savez(source_root / f"{role}.npz", prediction=np.linspace(0.2, 1.2, len(time.dates)))
        data.append(
            DataContract(
                role,
                reference(
                    source_root, f"{role}.npz", media_type="application/x-npz", producer="test"
                ),
                (port,),
                role,
                "exposed",
            )
        )
    run = OptimizationRunSpec(
        StudySpec(
            "synthetic-hydro",
            ObjectiveSpec("rmse", "minimize"),
            (),
            BudgetSpec(2, "calls", 2),
            NoiseSpec(),
            "system",
            17,
        ),
        SearchSpace(
            (ContinuousParameter("capacity", 20, 200), ContinuousParameter("recession", 0.05, 0.95))
        ),
        "sobol",
        {},
        "autoengineering.campaign.studies:campaign_evaluator",
    )
    checks = tuple(
        CheckSpec(name, "1", True, "outputs" if name == "finite" else "whole_model", {})
        for name in ("finite", "nonnegative", "soil_capacity", "daily_balance")
    )
    spec = replace(
        spec,
        baseline=BaselineSpec(spec.baseline.system, model, "hydrology", context.parameters),
        data=tuple(data),
        provenance=ProvenanceSpec(sources, spec.provenance.environment_lock, model.outputs),
        interventions=(
            InterventionSpec(
                "response",
                ("hamon-v1", "hargreaves-v1"),
                {"capacity": (20.0, 200.0), "recession": (0.05, 0.95)},
            ),
        ),
        execution=ExecutionSpec(("hydrology",), diagnostics="causal_future_forcing_v1"),
        calibration=CalibrationSpec(run, "fitting"),
        acceptance=AcceptanceSpec("rmse", "minimize", 0.01, {"kge": 0.02, "bias": 0.05}, checks),
    )
    path = tmp_path / "profile.yaml"
    spec.to_yaml(path)
    return path, source_root


def test_two_causality_calls_pause_before_the_stage_and_never_reselect_on_perturbed_labels(
    tmp_path,
):
    path, source_root = synthetic_profile(tmp_path)
    controller = CampaignController.create(
        path, source_root, tmp_path / "campaign", max_new_evaluations=9
    )
    assert controller.advance().state == "proposal_open"
    assert len(controller.state().budget.attempts) == 8
    controller = CampaignController.open(controller.store.root, max_new_evaluations=2)
    assert controller.advance().state == "completed"
    state = controller.state()
    assert len(state.budget.attempts) == 10
    diagnostics = [item for item in state.evaluations if item.split_id == "diagnostic"]
    assert len(diagnostics) == 2
    assert all(not item.metrics for item in diagnostics)
    assert all(check.status == "pass" for item in diagnostics for check in item.checks)
    assert all(item.checks[-1].name == "causal_prefix" for item in diagnostics)
    assert len([item for item in state.evaluations if item.split_id == "fitting"]) == 4
    assert len(state.decisions) == 4  # Three declared pair comparisons plus final selection.
    assert state.decisions[2].comparator_id == state.decisions[0].eligible_alternatives[-1]
