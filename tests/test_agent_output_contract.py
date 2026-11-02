"""Model-visible fields checked against independent handoffs and strict records.

The small schema-subset interpreter is a test oracle only. It is never an
acceptance engine and adds no runtime dependency or provider conformance claim.
"""

from dataclasses import replace
from itertools import repeat
import json
import re

import pytest

from autoengineering.agents.output_contract import output_contract, MAX_BYTES
from autoengineering.agents.records import (
    ArtifactGrant,
    RoleHandoff,
    TaskAssignment,
)
from autoengineering.campaign.records import ArtifactRef
from autoengineering.campaign.serialization import canonical_json
from autoengineering.campaign.artifacts import read_bytes
from autoengineering.agents.hosts.base import HostResult
from autoengineering.agents.hosts.fake import FakeHost
from autoengineering.agents.scheduler import SerialScheduler
from test_agent_scheduler import setup

H = "a" * 64


def matches(s, value, root):
    if isinstance(s, bool):
        return s
    if "$ref" in s and not matches(root["$defs"][s["$ref"].split("/")[-1]], value, root):
        return False
    if "const" in s and value != s["const"]:
        return False
    if "enum" in s and value not in s["enum"]:
        return False
    if "not" in s and matches(s["not"], value, root):
        return False
    for name in ("allOf", "anyOf", "oneOf"):
        if name in s:
            count = sum(matches(part, value, root) for part in s[name])
            if (
                (name == "allOf" and count != len(s[name]))
                or (name == "anyOf" and not count)
                or (name == "oneOf" and count != 1)
            ):
                return False
    if "if" in s and matches(s["if"], value, root) and not matches(s.get("then", {}), value, root):
        return False
    types = {
        "string": (str,),
        "object": (dict,),
        "array": (list,),
        "integer": (int,),
        "number": (int, float),
        "boolean": (bool,),
        "null": (type(None),),
    }
    if "type" in s and type(value) not in types[s["type"]]:
        return False
    if isinstance(value, str) and "pattern" in s and not re.search(s["pattern"], value):
        return False
    if type(value) in (int, float) and value < s.get("minimum", value):
        return False
    if isinstance(value, list):
        if len(value) < s.get("minItems", 0) or len(value) > s.get("maxItems", len(value)):
            return False
        if s.get("uniqueItems") and len({canonical_json(v) for v in value}) != len(value):
            return False
        if not all(matches(s.get("items", {}), v, root) for v in value):
            return False
    if isinstance(value, dict):
        if not set(s.get("required", ())) <= set(value):
            return False
        for key, v in value.items():
            if key in s.get("properties", {}):
                if not matches(s["properties"][key], v, root):
                    return False
            elif "additionalProperties" in s and not matches(s["additionalProperties"], v, root):
                return False
    return True


def task(role, *, version="1.0"):
    single = role == "single_agent"
    scope = "1.1" if single else "1.0"
    ref = ArtifactRef("context.json", H, 10, "application/json", "test", {})
    grant = ArtifactGrant(scope, "run", "task", role, ref, "read", 64, "worker_summary")
    operations = {
        "orchestrator": ("assign", "freeze", "stop"),
        "investigator": ("propose", "stop"),
        "implementer": ("configure", "stop"),
        "reviewer": ("review", "stop"),
        "single_agent": ("propose", "configure", "review", "freeze", "stop"),
    }[role]
    return TaskAssignment(
        scope,
        "task",
        "run",
        role,
        None,
        3,
        "Return the assigned result",
        (grant,),
        f"role-handoff-{version}",
        operations,
        1000,
        1,
    )


def handoff(role, output, action, version="1.0"):
    return {
        "schema_version": version,
        "id": "handoff-call",
        "task_id": "task",
        "invocation_id": "call",
        "role": role,
        "campaign_revision": 3,
        "status": "complete",
        "output": output,
        "supporting_artifact_ids": [H],
        "unresolved_issues": [],
        "proposed_next_action": action,
        "supersedes": None,
    }


BRIEF = {
    "candidate_id": "candidate",
    "target": "routing",
    "implementation_id": "linear",
    "hypothesis": "Measure gain",
    "expected_tradeoffs": "Measure cost",
    "evidence_ids": [H],
    "eligibility_gaps": [],
}
CONFIG = {
    "candidate_id": "candidate",
    "implementation_id": "linear",
    "parameters": {"multiplier": 1.5},
    "evidence_ids": [H],
}
REVIEW = {
    "candidate_id": "candidate",
    "evaluation_id": "evaluation",
    "evidence_ids": [H],
    "findings": [],
    "missing_evidence": [],
    "recommendation": "proceed",
}
CONTROL = {"action": "freeze", "role": None, "reason": "Supplied pool exhausted"}
DRAFT = {
    "candidate_id": "candidate",
    "base_snapshot": H,
    "files": {"adapter.py": "def run(x): return x"},
    "dependencies": ["python-stdlib", "math"],
    "evidence_ids": [H],
}


@pytest.mark.parametrize(
    "role,output,action,version,generated",
    [
        ("orchestrator", CONTROL, "freeze", "1.0", False),
        ("investigator", BRIEF, "propose", "1.0", False),
        ("implementer", CONFIG, "configure", "1.0", False),
        ("reviewer", REVIEW, "review", "1.0", False),
        ("implementer", DRAFT, "configure", "1.1", True),
        *[
            ("single_agent", v, a, "1.2", False)
            for v, a in (
                (BRIEF, "propose"),
                (CONFIG, "configure"),
                (REVIEW, "review"),
                (CONTROL, "freeze"),
            )
        ],
    ],
)
def test_complete_contract_accepts_authoritative_record_examples(
    role, output, action, version, generated
):
    t = task(role, version=version)
    contract = output_contract(
        t,
        "call",
        permitted_implementations=("linear",),
        generated=generated,
        candidate_id="candidate",
        evaluation_id="evaluation",
    )
    value = handoff(role, output, action, version)
    assert RoleHandoff.from_dict(value).to_dict() == value
    assert matches(contract["schema"], value, contract["schema"])
    assert len(canonical_json(contract).encode()) <= MAX_BYTES
    assert contract["schema"]["additionalProperties"] is False
    assert set(value) - {"supersedes"} == set(contract["schema"]["required"])
    assert set(contract["schema"]["$defs"]) <= {
        "NextStep",
        "CandidateBrief",
        "SuppliedConfiguration",
        "ReviewFindings",
        "Finding",
        "SourceDraft",
    }


@pytest.mark.parametrize(
    "change",
    [
        {"invocation_id": "old-call"},
        {"role": "reviewer"},
        {"campaign_revision": 4},
        {"campaign_revision": 3.0},
        {"extra": "not allowed"},
        {"supporting_artifact_ids": ["b" * 64]},
        {"unresolved_issues": ["incomplete"]},
        {"output": {**BRIEF, "implementation_id": "unlisted"}},
        {"output": {**BRIEF, "unknown": "field"}},
    ],
)
def test_contract_binds_context_grants_and_exact_fields(change):
    contract = output_contract(task("investigator"), "call", permitted_implementations=("linear",))
    assert not matches(
        contract["schema"],
        {**handoff("investigator", BRIEF, "propose"), **change},
        contract["schema"],
    )


def test_single_action_type_and_review_constraints_are_visible():
    c = output_contract(
        task("single_agent", version="1.2"), "call", permitted_implementations=("linear",)
    )
    assert not matches(c["schema"], handoff("single_agent", CONFIG, "propose", "1.2"), c["schema"])
    assert not matches(
        c["schema"],
        handoff(
            "single_agent", {**CONTROL, "action": "assign", "role": "investigator"}, "freeze", "1.2"
        ),
        c["schema"],
    )
    assert not matches(
        c["schema"],
        handoff("single_agent", {**REVIEW, "missing_evidence": ["Missing check"]}, "review", "1.2"),
        c["schema"],
    )


def test_source_contract_excludes_self_admission_and_extra_files():
    c = output_contract(
        task("implementer", version="1.1"),
        "call",
        permitted_implementations=("linear",),
        generated=True,
    )
    assert set(c["schema"]["$defs"]) == {"SourceDraft"}
    assert not matches(
        c["schema"],
        handoff(
            "implementer",
            {**DRAFT, "files": {**DRAFT["files"], "escape.py": "bad"}},
            "configure",
            "1.1",
        ),
        c["schema"],
    )
    with pytest.raises(ValueError, match="generated"):
        output_contract(
            task("implementer", version="1.1"), "call", permitted_implementations=("linear",)
        )


def test_scheduler_persists_current_contract_before_host_and_model_can_use_plain_json(tmp_path):
    store, _, t, _ = setup(tmp_path)

    def response(task, prompt, invocation):
        frame = json.loads(prompt[prompt.index('{"approved_evidence"') :])
        c = frame["output_contract"]
        saved = store.replay().invocations[invocation]
        assert saved.state == "reserved" and read_bytes(store.root, saved.prompt).decode() == prompt
        fields = c["schema"]["properties"]
        value = {k: s["const"] for k, s in fields.items() if "const" in s}
        evidence = frame["approved_evidence"][0]["id"]
        value.update(
            id="handoff-" + invocation,
            status="complete",
            output={**BRIEF, "evidence_ids": [evidence]},
            supporting_artifact_ids=[evidence],
            unresolved_issues=[],
            proposed_next_action="propose",
            supersedes=None,
        )
        assert matches(c["schema"], value, c["schema"])
        # Build JSON from the delivered contract and data, not a RoleHandoff constructor.
        return HostResult("completed", canonical_json(value), None, {}, 0)

    host = FakeHost(repeat(response))
    result = SerialScheduler(store, host, clock=lambda: 100).dispatch(t, campaign_revision=3)
    assert result.state == "completed" and result.normalized_output is not None
    assert result.prompt.size_bytes == len(host.calls[0][2].encode())


def test_empty_grants_allow_control_only_without_invented_citations():
    t = replace(task("orchestrator"), grants=())
    c = output_contract(t, "call", permitted_implementations=())
    value = {**handoff("orchestrator", CONTROL, "freeze"), "supporting_artifact_ids": []}
    assert matches(c["schema"], value, c["schema"])
    assert not matches(c["schema"], {**value, "supporting_artifact_ids": [H]}, c["schema"])


def test_large_contract_is_rejected_before_dispatch():
    with pytest.raises(ValueError, match="32 KiB"):
        output_contract(
            task("investigator"),
            "call",
            permitted_implementations=tuple(f"implementation-{i:06d}" for i in range(2000)),
        )


def test_legacy_generated_bundle_has_all_reference_fields_but_cannot_self_admit():
    c = output_contract(
        task("implementer"), "call", permitted_implementations=("linear",), generated=True
    )
    ref = {
        "path": "adapter.py",
        "sha256": H,
        "size_bytes": 10,
        "media_type": "text/plain",
        "producer": "source",
        "metadata": {},
    }
    output = {
        "base_snapshot": H,
        "patch": ref,
        "sources": [ref],
        "allowed_files": ["adapter.py"],
        "dependencies": [],
        "interface_results": [],
        "execution_boundary_receipt": None,
        "admitted_identity": None,
    }
    value = handoff("implementer", output, "configure")
    assert RoleHandoff.from_dict(value).to_dict() == value
    assert matches(c["schema"], value, c["schema"])
    assert not matches(
        c["schema"], {**value, "output": {**output, "admitted_identity": H}}, c["schema"]
    )
    assert set(c["schema"]["$defs"]) == {
        "SuppliedConfiguration",
        "ImplementationBundle",
        "ArtifactRef",
    }


@pytest.mark.parametrize("after,expected", [(199.5, "timeout"), (201, None)])
def test_prompt_preparation_cannot_extend_original_deadline(tmp_path, monkeypatch, after, expected):
    from autoengineering.agents import scheduler as module
    from autoengineering.campaign.store import StoreError

    store, host, t, _ = setup(tmp_path)
    clock = [100.0]
    original = module.output_contract

    def delayed(*args, **kwargs):
        value = original(*args, **kwargs)
        clock[0] = after
        return value

    monkeypatch.setattr(module, "output_contract", delayed)
    scheduler = SerialScheduler(store, host, clock=lambda: clock[0])
    if expected is None:
        with pytest.raises(StoreError, match="prompt preparation"):
            scheduler.dispatch(t, campaign_revision=3)
        assert not host.calls and not store.replay().invocations
    else:
        call = scheduler.dispatch(t, campaign_revision=3)
        assert call.state == expected and call.started_at == after
        assert call.elapsed_seconds == 0.5 and len(host.calls) == 1
