"""Public seven-route wind development rehearsal with bounded native callbacks."""

from __future__ import annotations

import argparse
from dataclasses import replace
from pathlib import Path

from autoengineering.campaign.artifacts import reference
from autoengineering.utility.callback_native import CallbackDriverSpec
from autoengineering.utility.engineering_campaign import EngineeringCallbackCampaignSpec
from autoengineering.utility.engineering_process import execution_identity
from examples.utility.rehearse_engineering_plan import build_plan, run_prepared
from examples.utility.rehearse_wind_native import prepare as prepare_native
from examples.utility.wind import ROOT


def prepare_plan(output):
    output, source, wind = prepare_native(output)
    execution = wind.execution
    extra = (
        "examples/utility/wind_callback.py",
        "examples/utility/rehearse_wind_plan.py",
        "examples/utility/rehearse_engineering_plan.py",
    )
    for name in extra:
        target = source / name
        target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        target.write_bytes((ROOT / name).read_bytes())
    names = [r.path for r in execution.sources] + list(extra)
    refs = tuple(
        reference(source, n, media_type="text/plain", producer="wind-route-development")
        for n in names
    )
    identity = execution_identity(
        execution.entrypoint,
        refs,
        execution.lock,
        execution.scenarios,
        execution.timeout_seconds,
        execution.output_bytes,
        profile="supervised-engineering-v2",
    )
    execution = replace(
        execution, sources=refs, study=replace(execution.study, source_identity=identity)
    )
    native = CallbackDriverSpec(
        "utility-callback-driver-v1",
        execution,
        "examples.utility.wind_callback:execute",
        wind.native.to_json(),
        {"wake": wind.native.maximum_wake_calls, "gradient": wind.native.maximum_gradient_calls},
        wind.timeout_seconds,
        wind.output_bytes,
    )
    geometry = wind.native.geometry
    ctx = geometry.context(geometry.baseline, output / "model-identity", source_root=source)
    declared = {r.path: r for r in (*execution.sources, execution.lock)}
    model = replace(
        ctx.model, source_bundle=tuple(declared[r.path] for r in ctx.model.source_bundle)
    )
    campaign = EngineeringCallbackCampaignSpec(
        "utility-engineering-campaign-v3",
        "wind-route-development",
        execution,
        model,
        geometry.baseline,
        (),
        16,
        native=native,
    )
    return build_plan(output, source, campaign, task_id="wind", family="wind")


def run(output):
    return run_prepared(*prepare_plan(output))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    run(parser.parse_args().output)
