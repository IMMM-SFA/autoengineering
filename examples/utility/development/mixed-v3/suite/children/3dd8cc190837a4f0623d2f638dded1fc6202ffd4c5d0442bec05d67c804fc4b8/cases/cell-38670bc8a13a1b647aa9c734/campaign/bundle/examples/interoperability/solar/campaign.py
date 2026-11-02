"""Prepare a development solar campaign with fitting-only Optuna calibration."""
from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

import numpy as np

from autoengineering.campaign.artifacts import confined_file, reference
from autoengineering.campaign.records import DataContract
from autoengineering.campaign.identity import scientific_source_paths
from autoengineering.campaign.spec import (
    AcceptanceSpec, BaselineSpec, CalibrationSpec, CampaignSpec, CheckSpec,
    ConfirmationSpec, ExecutionSpec, InterventionSpec, ProvenanceSpec, WorkflowSpec,
)
from autoengineering.optimization import (
    BudgetSpec, ContinuousParameter, NoiseSpec, ObjectiveSpec, OptimizationRunSpec,
    SearchSpace, StudySpec,
)
from examples.open_chains.solar.run_workflow import POWER
from .data import load
from .fixture import BASELINE, ROOT, context, forcing


def prepare(cache, output):
    import autoengineering
    import pvlib

    output = Path(output).absolute()
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    bundle = output / "source"
    (bundle / "inputs").mkdir(mode=0o700, parents=True)
    data, inventory = load(cache)
    ctx = context(data, BASELINE, output)
    paths = set(scientific_source_paths(version="3"))
    paths |= {r.path for r in ctx.model.source_bundle}
    paths.update(("examples/open_chains/solar/sources.json",
                  "examples/open_chains/solar/run_workflow.py", "examples/open_chains/common.py",
                  "examples/interoperability/solar/campaign.py",
                  "examples/interoperability/solar/data.py"))
    lock_path = "examples/interoperability/optimizer_comparison/pixi.lock"
    package = Path(autoengineering.__file__).resolve().parent
    # A wheel stores package sources directly under autoengineering/, whereas
    # logical scientific paths retain their stable src/autoengineering prefix.
    # Capture those bytes in a fresh writable bundle, never beside installed code.
    for name in sorted(paths | {lock_path}):
        if name.startswith("src/autoengineering/"):
            original = confined_file(package, name.removeprefix("src/autoengineering/"))
        else:
            original = confined_file(ROOT, name)
        target = bundle / name
        target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        target.write_bytes(original.read_bytes())

    def ref(path, media="application/octet-stream"):
        return reference(bundle, path, media_type=media, producer="solar-campaign-author")

    np.savez(bundle / "inputs/forcing.npz", **forcing(data))
    time = ctx.model.outputs[0].time
    eligible = np.asarray(time.scoring_mask)
    early = data.index < "2018-06-05"
    observations = []
    for role, mask in (("fitting", early), ("comparison", ~early)):
        selected = np.flatnonzero(eligible & mask)
        if len(selected) < 24:
            raise ValueError("insufficient solar observation support")
        np.savez(bundle / f"inputs/{role}.npz", prediction=data[POWER].to_numpy()[selected])
        axis = replace(time, dates=tuple(time.dates[i] for i in selected),
                       warmup_mask=(False,) * len(selected), scoring_mask=(True,) * len(selected))
        port = replace(ctx.model.outputs[0], time=axis)
        observations.append(DataContract(role, ref(f"inputs/{role}.npz", "application/x-npz"),
                                         (port,), role, "exposed"))
    (bundle / "inputs/system.yaml").write_text("name: measured-poa-solar-development\ncomponents: []\n")
    sources = tuple(ref(path) for path in sorted(paths))
    lock = ref(lock_path, "text/plain")
    model = replace(ctx.model, implementations={"solar": "faiman-prilliman-v1"},
                    source_bundle=sources, dependency_bundle=lock.sha256)
    bounds = {"u0": (20., 35.), "u1": (4., 10.), "dc_loss_scale": (.9, 1.)}
    run = OptimizationRunSpec(
        StudySpec("solar-development-fitting", ObjectiveSpec("rmse", "minimize"), (),
                  BudgetSpec(12., "physical_executions", 12), NoiseSpec(), "system", 17),
        SearchSpace(tuple(ContinuousParameter(name, *limits) for name, limits in bounds.items())),
        "optuna", {}, "autoengineering.campaign.studies:campaign_evaluator",
    )
    equipment = pvlib.pvsystem.retrieve_sam("cecinverter")["TMEIC__PVL_L1833GRM"]
    spec = CampaignSpec(
        "1.0", "solar-development", "Previously exposed OEDI power reconstruction", 17,
        "solar-interoperability-core-v3",
        BaselineSpec(ref("inputs/system.yaml", "application/yaml"), model, "solar-pvlib", BASELINE),
        (DataContract("forcing", ref("inputs/forcing.npz", "application/x-npz"),
                      model.inputs, "forcing", "exposed"), *observations),
        (InterventionSpec("solar", ("faiman-v1", "sapm-v1"), bounds),),
        AcceptanceSpec("rmse", "minimize", 0., {}, (
            CheckSpec("finite", "1", True, "outputs", {}),
            CheckSpec("solar_physical", "1", True, "outputs", {
                "capacity_kw": float(equipment.Paco) / 1000,
                "standby_floor_kw": -float(equipment.Pnt) / 1000,
            }),
        )), CalibrationSpec(run, "fitting"), WorkflowSpec(max_candidates=1),
        ExecutionSpec(("solar-pvlib",), max_executions=18, timeout_seconds=5,
                      termination_grace_seconds=1, kill_wait_seconds=1, active_deadline_seconds=120),
        ConfirmationSpec("disabled"), ProvenanceSpec(sources, lock, model.outputs),
    )
    spec.to_yaml(output / "campaign.yaml")
    (output / "data-inventory.json").write_text(json.dumps(inventory, indent=2))
    return spec


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    prepared = prepare(args.cache, args.output)
    print(f"Prepared {prepared.name}: {args.output / 'campaign.yaml'}")
    print(f"Source root: {args.output / 'source'}")
