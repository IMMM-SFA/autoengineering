"""Failed native calls cannot hide corrupt evidence from later invocations."""

from types import SimpleNamespace

import pytest

from autoengineering.campaign.artifacts import put_bytes
from autoengineering.campaign.serialization import canonical_json
from examples.agent_campaign import native_status as reporting

H = "a" * 64


def test_failed_provider_does_not_skip_later_missing_proof(tmp_path, monkeypatch):
    (tmp_path / "artifacts").mkdir(mode=0o700)
    worker_root = tmp_path / "cases/single_agent/worker"
    for parent in reversed((worker_root / "processes").parents):
        if parent.is_relative_to(tmp_path):
            parent.mkdir(mode=0o700, exist_ok=True)
    (worker_root / "processes").mkdir(mode=0o700)
    control = SimpleNamespace(
        id="control",
        digest=H,
        state="host_failure",
        usage={},
        resolved_model=None,
        elapsed_seconds=None,
    )
    failed = SimpleNamespace(id="failed", digest=H, resolved_model=None, usage={})
    later = SimpleNamespace(id="later", digest=H, resolved_model="model", usage={})
    worker = SimpleNamespace(
        root=worker_root,
        replay=lambda: SimpleNamespace(invocations={c.id: c for c in (control, failed, later)}),
    )
    batch = SimpleNamespace(root=tmp_path, spec=SimpleNamespace(host_configuration_digest=H))
    proof = put_bytes(
        tmp_path,
        canonical_json({"call_digest": H, "bindings": {}}).encode(),
        name="control.json",
        media_type="application/json",
        producer="unit-fixture",
    )
    missing = put_bytes(
        tmp_path,
        b"{}",
        name="provider.json",
        media_type="application/json",
        producer="unit-fixture",
    )
    (tmp_path / missing.path).unlink()
    interruption = {"call_id": "control", "evidence": proof.to_dict(), "passed": True}
    (worker_root / "processes/interruption.json").write_text(canonical_json(interruption))
    receipt = {
        "kind": "native_matched_leaf_river_development",
        "passed": False,
        "interruption": interruption,
        "provider_proofs": {
            "failed": {"verified": False, "reason": "fixed_worker_response_proof_unavailable"},
            "later": {"verified": True, "evidence": missing.to_dict()},
        },
    }
    monkeypatch.setattr(reporting, "WorkerStore", lambda *a: worker)
    monkeypatch.setattr(
        reporting,
        "common_report",
        lambda *a: {
            "status": "failed",
            "active_case": None,
            "route_verdicts": {"single_agent": receipt},
        },
    )
    with pytest.raises(ValueError, match="regular file"):
        reporting.reconstruct_report(batch, H)
