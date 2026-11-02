"""Nested source/review evidence stays immutable and schema checked."""

from dataclasses import FrozenInstanceError

import pytest

from autoengineering.agents.records import ImplementationBundle, ReviewFindings
from autoengineering.campaign.serialization import canonical_json

H = "a" * 64


def artifact(path):
    return {
        "path": path,
        "sha256": H,
        "size_bytes": 12,
        "media_type": "application/json",
        "producer": "trusted-controller",
        "metadata": {"check": "passed"},
    }


def bundle():
    return {
        "base_snapshot": H,
        "patch": artifact("patch.json"),
        "sources": [artifact("adapter.py")],
        "allowed_files": ["adapter.py"],
        "dependencies": ["python-stdlib", "math"],
        "interface_results": [artifact("interface.json")],
        "execution_boundary_receipt": artifact("boundary.json"),
        "admitted_identity": H,
    }


def review():
    return {
        "candidate_id": "candidate-1",
        "evaluation_id": "evaluation-1",
        "evidence_ids": [H],
        "findings": [
            {
                "id": "finding-1",
                "severity": "advisory",
                "description": "Check the stated domain limit",
                "supporting_checks": ["interface-check"],
                "evidence_ids": [H],
            }
        ],
        "missing_evidence": ["independent measured confirmation"],
        "recommendation": "repair",
    }


def test_bundle_copies_every_nested_artifact_and_collection():
    data = bundle()
    value = ImplementationBundle.from_dict(data)
    original = value.to_json()
    for ref in (
        data["patch"],
        *data["sources"],
        *data["interface_results"],
        data["execution_boundary_receipt"],
    ):
        ref["metadata"]["check"] = "changed"
        ref["path"] = "changed.json"
    data["sources"].clear()
    data["allowed_files"].append("unapproved.py")
    data["dependencies"].clear()
    data["interface_results"].clear()
    assert value.to_json() == original
    assert ImplementationBundle.from_json(original) == value
    for ref in (
        value.patch,
        *value.sources,
        *value.interface_results,
        value.execution_boundary_receipt,
    ):
        with pytest.raises(TypeError):
            ref.metadata["check"] = "changed"
        with pytest.raises(FrozenInstanceError):
            ref.path = "changed.json"
    exported = value.to_dict()
    exported["sources"][0]["metadata"].clear()
    exported["interface_results"][0]["path"] = "changed.json"
    assert value.to_json() == original


def test_review_copies_findings_checks_evidence_and_missing_evidence():
    data = review()
    value = ReviewFindings.from_dict(data)
    original = value.to_json()
    data["findings"][0]["supporting_checks"].clear()
    data["findings"][0]["evidence_ids"].clear()
    data["findings"][0]["description"] = "changed"
    data["findings"].clear()
    data["evidence_ids"].clear()
    data["missing_evidence"].clear()
    assert value.to_json() == original
    assert ReviewFindings.from_json(original) == value
    with pytest.raises(FrozenInstanceError):
        value.findings[0].description = "changed"
    exported = value.to_dict()
    exported["findings"][0]["supporting_checks"].append("invented")
    exported["missing_evidence"].clear()
    assert value.to_json() == original


@pytest.mark.parametrize(
    "field", ["patch", "sources", "interface_results", "execution_boundary_receipt"]
)
def test_unknown_nested_bundle_fields_do_not_confer_authority(field):
    data = bundle()
    ref = data[field][0] if isinstance(data[field], list) else data[field]
    ref["approved"] = True
    with pytest.raises(ValueError, match="unknown or missing fields|invalid type or value"):
        ImplementationBundle.from_dict(data)


@pytest.mark.parametrize(
    "problem",
    ["unknown", "outside-evidence", "blocking-proceed", "missing-proceed", "duplicate-id"],
)
def test_review_rejects_nested_authority_and_unresolved_findings(problem):
    data = review()
    if problem == "unknown":
        data["findings"][0]["scientifically_eligible"] = True
    elif problem == "outside-evidence":
        data["findings"][0]["evidence_ids"] = ["b" * 64]
    elif problem == "blocking-proceed":
        data["findings"][0]["severity"] = "blocking"
        data["missing_evidence"] = []
        data["recommendation"] = "proceed"
    elif problem == "missing-proceed":
        data["recommendation"] = "proceed"
    else:
        data["findings"].append(dict(data["findings"][0]))
    with pytest.raises(ValueError):
        ReviewFindings.from_dict(data)


@pytest.mark.parametrize("kind", ["bundle", "review"])
def test_nested_fields_cannot_bypass_envelope_size_limit(kind):
    if kind == "bundle":
        data, cls = bundle(), ImplementationBundle
        data["sources"][0]["metadata"]["check"] = "x" * 65536
    else:
        data, cls = review(), ReviewFindings
        data["findings"][0]["supporting_checks"] = ["x" * 65536]
    with pytest.raises(ValueError, match="64 KiB"):
        cls.from_dict(data)
    with pytest.raises(ValueError, match="64 KiB"):
        cls.from_json(canonical_json(data))
