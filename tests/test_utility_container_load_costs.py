"""Container output reconstruction and versioned registration are metadata only."""

from dataclasses import replace
from pathlib import Path
import json

import pytest

from autoengineering.utility.load_costs import (
    LoadCostRegistration,
    LoadScorePolicy,
)
from autoengineering.utility.load_container_costs import (
    CoupledRuntimeRegistration,
    ContainerLoadCostRegistration,
    decode_worker_output,
)

H = "1" * 64
ROOT = Path(__file__).resolve().parents[1]
ACTUAL = ROOT / "examples/utility/verification-engineering-linux-worker-v1/output.log"


def runtime():
    return CoupledRuntimeRegistration(
        "utility-coupled-runtime-registration-v1",
        "sha256:" + H,
        H,
        H,
        H,
        H,
        H,
        H,
    )


def test_actual_linux_worker_metadata_needs_no_example_or_framework_imports():
    work = decode_worker_output(ACTUAL.read_bytes())
    assert work.completed_model_starts == 24 and work.score.value == 0.27174569156641054
    assert work.total_inner_work.solver_iterations == 360
    assert work.total_inner_work.component_calls == 5880
    assert work.total_inner_work.derivative_calls == 1800


@pytest.mark.parametrize(
    "change",
    [
        lambda v: v.update(private_boundary_qualified=True),
        lambda v: v.update(owner_loss_qualified=True),
        lambda v: v["observed"]["effective_limits"].update(**{"pids.max": "max"}),
        lambda v: v["worker"].update(child_exit_code=False),
        lambda v: v["worker"].update(child_signal=9),
        lambda v: v["worker"].update(output_limited=True),
        lambda v: v["worker"].update(captured_bytes=16384),
        lambda v: v["worker"]["result"].update(automatic_retries=False),
        lambda v: v["worker"]["result"].update(PRIVATE_CANARY=123),
        lambda v: v["worker"]["result"].update(completed_model_starts=23),
        lambda v: v["worker"]["result"]["known_completed_inner_work"].update(
            solver_iterations=2401
        ),
        lambda v: v["worker"]["result"]["score"].update(value=-1),
        lambda v: v["worker"]["result"]["score"].update(status="scientific_infeasible", value=999),
    ],
)
def test_foreign_status_resource_policy_and_partial_output_are_rejected(change):
    value = json.loads(ACTUAL.read_bytes())
    change(value)
    with pytest.raises(ValueError):
        decode_worker_output(json.dumps(value).encode())


def test_unknown_failed_inner_work_and_scientific_veto_remain_distinct():
    value = json.loads(ACTUAL.read_bytes())
    work = value["worker"]["result"]
    work["score"].update(status="model_failure", value=None, feasible=None)
    work.update(
        attempted_model_starts=3,
        completed_model_starts=2,
        last_attempt_inner_work_unknown=True,
        known_completed_inner_work={
            "solver_iterations": 30,
            "component_calls": 50,
            "derivative_calls": 0,
        },
    )
    from autoengineering.campaign.serialization import canonical_json

    value["worker"]["captured_bytes"] = len(canonical_json(work).encode()) + 1
    read = decode_worker_output(json.dumps(value).encode())
    assert read.total_inner_work is None
    assert read.known_completed_inner_work.solver_iterations == 30
    veto = json.loads(ACTUAL.read_bytes())
    veto["worker"]["result"]["score"].update(
        status="scientific_infeasible", value=None, feasible=False
    )
    veto["worker"]["captured_bytes"] = len(canonical_json(veto["worker"]["result"]).encode()) + 1
    read = decode_worker_output(json.dumps(veto).encode())
    assert read.score.value is None and read.total_inner_work.solver_iterations == 360


@pytest.mark.parametrize("raw", [b'{"x":1,"x":2}', b'{"x":NaN}', b"x" * 16385])
def test_json_envelope_is_strict(raw):
    with pytest.raises(ValueError):
        decode_worker_output(raw)


def test_v1_registration_stays_unchanged_and_v2_roundtrips():
    from autoengineering.campaign.records import ArtifactRef

    artifact = ArtifactRef("source.json", H, 1, "application/json", "fixture", {})
    policy = LoadScorePolicy("utility-coupled-load-score-v1", H, H, 0.62)
    old = LoadCostRegistration("utility-load-cost-registration-v1", artifact, H, policy)
    assert type(LoadCostRegistration.from_json(old.to_json())) is LoadCostRegistration
    assert LoadCostRegistration.from_json(old.to_json()).to_json() == old.to_json()
    new = ContainerLoadCostRegistration(
        binding_artifact=artifact,
        callback_source_digest=H,
        policy=policy,
        schema="utility-load-cost-registration-v2",
        runtime=runtime(),
    )
    assert new.code_digest != old.code_digest
    assert LoadCostRegistration.from_json(new.to_json()) == new
    with pytest.raises(ValueError):
        replace(new, runtime=replace(runtime(), kernel_source_digest="2" * 64))
