"""Worker contracts reject malformed data before any host launch."""

from dataclasses import FrozenInstanceError, replace
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from autoengineering.agents.hosts.base import HostResult
from autoengineering.agents.hosts.fake import FakeHost
from autoengineering.agents.records import (
    AgentRunSpec,
    ArtifactGrant,
    CandidateBrief,
    HostSelection,
    ResourceLimits,
    RoleHandoff,
    TaskAssignment,
    WorkerInvocation,
)
from autoengineering.campaign.records import ArtifactRef

H = "a" * 64


def run_spec():
    return AgentRunSpec(
        "1.0",
        "worker-run",
        "campaign",
        H,
        HostSelection("fake", "none", "scripted", "1.0"),
        {role: H for role in ("orchestrator", "investigator", "implementer", "reviewer")},
        ("linear",),
        H,
        ResourceLimits(12, 6, 4, 2, 120, 20, 65536, 1048576),
        H,
        H,
        "supplied",
    )


def task_assignment(grants=()):
    return TaskAssignment(
        "1.0",
        "investigate",
        "worker-run",
        "investigator",
        None,
        3,
        "Propose an allowed intervention",
        grants,
        "role-handoff-1.0",
        ("propose", "stop"),
        100,
        2,
    )


def handoff(evidence=H):
    return RoleHandoff(
        "1.0",
        "brief-1",
        "investigate",
        "invocation-1",
        "investigator",
        3,
        "complete",
        CandidateBrief(
            "candidate-1", "routing", "linear", "Test gain", "Cost may rise", (evidence,), ()
        ),
        (evidence,),
        (),
        "propose",
    )


def test_strict_roundtrip_and_nested_immutability(tmp_path):
    spec = run_spec()
    data = spec.to_dict()
    restored = AgentRunSpec.from_dict(data)
    data["role_templates"]["reviewer"] = "b" * 64
    assert restored.role_templates["reviewer"] == H
    with pytest.raises(TypeError):
        restored.role_templates["reviewer"] = H
    with pytest.raises(FrozenInstanceError):
        restored.id = "changed"
    path = tmp_path / "run.json"
    path.write_text(spec.to_json())
    assert AgentRunSpec.from_file(path) == spec
    assert restored.digest == spec.digest
    assert RoleHandoff.from_json(handoff().to_json()) == handoff()
    assert replace(spec, host=replace(spec.host, requested_model="other")).digest != spec.digest
    assert replace(spec, role_templates={**spec.role_templates, "reviewer": "b" * 64}).digest != (
        spec.digest
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("schema_version", "2.0"),
        ("id", "../escape"),
        ("unknown", 1),
        ("campaign_identity", "unknown"),
        ("permitted_interventions", ["linear", "linear"]),
        ("execution_mode", "shell"),
        ("role_templates", {"reviewer": H}),
    ],
)
def test_invalid_runs(field, value):
    data = run_spec().to_dict()
    data[field] = value
    with pytest.raises(ValueError):
        AgentRunSpec.from_dict(data)


@pytest.mark.parametrize(
    "field,value",
    [
        ("max_invocations", True),
        ("max_tasks", 0),
        ("max_repairs", -1),
        ("repairs_per_task", 3),
        ("worker_seconds", float("inf")),
        ("elapsed_seconds", float("nan")),
        ("transcript_bytes", False),
        ("observed_tokens", True),
        ("observed_tokens", 0),
    ],
)
def test_invalid_limits(field, value):
    data = run_spec().limits.to_dict()
    data[field] = value
    with pytest.raises(ValueError):
        ResourceLimits.from_dict(data)


def test_bounded_json_and_duplicate_fields(tmp_path):
    text = run_spec().to_json()
    with pytest.raises(ValueError, match="duplicate"):
        AgentRunSpec.from_json(text[:-1] + ',"id":"duplicate"}')
    with pytest.raises(ValueError, match="nonfinite"):
        AgentRunSpec.from_json(text.replace('"max_tasks":6', '"max_tasks":NaN'))
    with pytest.raises(ValueError, match="64 KiB"):
        AgentRunSpec.from_json(" " * 65537)
    with pytest.raises(ValueError, match="64 KiB"):
        replace(task_assignment(), question="x" * 65536)
    path = tmp_path / "huge.json"
    path.write_bytes(b" " * 65537)
    with pytest.raises(ValueError, match="64 KiB"):
        AgentRunSpec.from_file(path)


def test_role_output_is_typed_and_versioned():
    data = handoff().to_dict()
    data["role"] = "reviewer"
    with pytest.raises(ValueError, match="role schema"):
        RoleHandoff.from_dict(data)
    data = handoff().to_dict()
    data["output"]["import_path"] = "malicious:run"
    with pytest.raises(ValueError):
        RoleHandoff.from_dict(data)
    with pytest.raises(ValueError):
        replace(handoff(), unresolved_issues=("missing source",))
    with pytest.raises(ValueError):
        HostSelection("codex", "none", "model", "1.0")


def test_unknown_usage_and_invocation_receipts():
    ref = ArtifactRef("prompt.json", H, 3, "application/json", "broker", {})
    host = FakeHost(())
    invocation = WorkerInvocation(
        "1.0",
        "invocation-1",
        "worker-run",
        "investigate",
        0,
        "reserved",
        ref,
        host.capabilities(),
        "scripted",
        None,
        H,
        "nonce-1",
        None,
        None,
        None,
        None,
        0,
        None,
        {"input_tokens": None},
    )
    assert WorkerInvocation.from_json(invocation.to_json()) == invocation
    assert invocation.usage["input_tokens"] is None
    for state in ("running", "completed"):
        with pytest.raises(ValueError, match="receipt"):
            replace(invocation, state=state)
    with pytest.raises(ValueError):
        replace(invocation, usage={"tokens": True})


def test_fake_host_failures_and_no_duplicate_dispatch():
    result = HostResult("completed", handoff().to_json(), None, {"tokens": None}, 2)
    host = FakeHost([result, result, RuntimeError("unavailable"), result])
    task = task_assignment()
    assert (
        host.invoke(task, "brief", invocation_id="one", timeout_seconds=3, max_output_bytes=65536)
        == result
    )
    with pytest.raises(ValueError, match="already dispatched"):
        host.invoke(task, "brief", invocation_id="one", timeout_seconds=3, max_output_bytes=10)
    assert (
        host.invoke(
            task, "brief", invocation_id="two", timeout_seconds=1, max_output_bytes=65536
        ).status
        == "timeout"
    )
    with pytest.raises(RuntimeError, match="unavailable"):
        host.invoke(task, "brief", invocation_id="three", timeout_seconds=3, max_output_bytes=65536)
    assert (
        host.invoke(
            task, "brief", invocation_id="four", timeout_seconds=3, max_output_bytes=10
        ).status
        == "host_failure"
    )
    assert host.cancel("one") and not host.cancel("absent")
    assert len(host.calls) == 4


def test_base_import_has_no_host_or_scientific_execution_imports():
    source = """
import sys
import autoengineering.agents
import autoengineering.agents.records
import autoengineering.agents.hosts.fake
assert not any(name in sys.modules for name in (
    'torch', 'botorch', 'openai', 'autoengineering.campaign.controller',
    'autoengineering.agents.hosts.codex',
))
"""
    result = subprocess.run(
        [sys.executable, "-c", source],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(Path(__file__).parents[1] / "src")},
    )
    assert result.returncode == 0, result.stderr


def test_grant_scope_and_size():
    ref = ArtifactRef("summary.json", H, 10, "application/json", "broker", {})
    grant = ArtifactGrant(
        "1.0", "worker-run", "investigate", "investigator", ref, "read", 10, "worker_summary"
    )
    assert ArtifactGrant.from_json(grant.to_json()) == grant
    with pytest.raises(ValueError):
        replace(grant, max_bytes=9)
    with pytest.raises(ValueError):
        task_assignment((replace(grant, task_id="other"),))
    data = grant.to_dict()
    data["visibility"] = "private_labels"
    with pytest.raises(ValueError):
        ArtifactGrant.from_dict(data)
    assert json.loads(grant.to_json())["operation"] == "read"


@pytest.mark.parametrize("child", [None, "legacy-action", "study-fit:eval-000000"])
def test_scientific_child_identity_preserves_legacy_and_composite_values(child):
    from autoengineering.agents.records import ScientificAttempt

    value = ScientificAttempt("attempt", "reservation", "finished", child, 1, 1, False)
    assert ScientificAttempt.from_json(value.to_json()) == value


@pytest.mark.parametrize("child", ["study:", ":eval", "study:eval:extra", "study:../private"])
def test_scientific_child_identity_rejects_malformed_references(child):
    from autoengineering.agents.records import ScientificAttempt

    with pytest.raises(ValueError):
        ScientificAttempt("attempt", "reservation", "finished", child, 1, 1, False)
