"""Exercise the native case handler with a declared synthetic, fake-host baseline.

This isolates orchestration from provider access and measured Leaf River data.
The native report reader must reject this synthetic batch as live evidence.
"""

from pathlib import Path
import shutil

import pytest

from autoengineering.agents.batch import BatchStore
from autoengineering.campaign.serialization import unique_json
from examples.agent_campaign.native_runtime import NativeRuntime
from examples.agent_campaign.native_status import read_report
from test_agent_comparison import prepared as prepared, fork


def test_native_case_handler_reuses_synthetic_science_and_never_becomes_live_evidence(
    prepared, tmp_path
):
    source, plan = fork(prepared, tmp_path)
    view = tmp_path / "native-view"
    view.mkdir(mode=0o700)
    (view / "leaf").mkdir(mode=0o700)
    shutil.copytree(source / "captured_source", view / "leaf/captured_source")
    shutil.copytree(source / "scientific", view / "scientific")
    batch = BatchStore.create(plan.runtime_root, plan.batch)
    case = plan.cases[0]
    batch.start_case(case.id, case.configuration_digest)
    # This private handler fixture deliberately bypasses NativeRuntime.create.
    # The real entry point requires verified real-provider conformance first.
    runtime = object.__new__(NativeRuntime)
    runtime.preparation, runtime.batch = view, batch
    assert runtime._case(case, max_new_evaluations=1) is None
    receipt = runtime._case(case)
    assert receipt["passed"] and receipt["scientific_starts"] == 38
    assert receipt["logical_host_calls"] == 13
    assert receipt["physical_host_calls"] == receipt["physical_provider_calls"] == 0
    assert receipt["verified_provider_responses"] == 0
    assert receipt["candidate_order"] == ["pet-hamon-v1", "pet-hargreaves-v1"]
    assert receipt["invalid_candidate_control"]["reason"] == "candidate topology/interface differs"
    assert receipt["confirmation"] == "confirmation_not_attempted"
    from autoengineering.agents.store import WorkerStore

    worker = WorkerStore(batch.root / "cases/scripted/worker")
    first_prompt = next(iter(worker.replay().invocations.values())).prompt
    from autoengineering.campaign.artifacts import read_bytes

    raw = read_bytes(worker.root, first_prompt).decode()
    value = unique_json(raw[raw.index('{"approved_evidence"') :])
    summary = unique_json(value["approved_evidence"][0]["content"])
    assert summary["comparison_policy"]["version"].startswith("native-matched-preparation-")
    before = batch.replay().events, worker.replay().events
    again = runtime._case(case)
    assert again["worker_head"] == receipt["worker_head"]
    assert again["scientific_head"] == receipt["scientific_head"]
    assert (batch.replay().events, worker.replay().events) == before
    assert not (Path(plan.runtime_root) / "origin.json").exists()
    with pytest.raises(ValueError):
        read_report(batch.root, expected_digest=batch.digest)
