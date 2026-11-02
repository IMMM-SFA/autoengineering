"""Actual source-closed envelope receipts replay without their scientific source."""

import json
from pathlib import Path
import shutil
import socket
import subprocess

import pytest

from autoengineering.agents.batch import BatchStore
from autoengineering.campaign.serialization import digest
from autoengineering.utility.engineering_campaign import EngineeringCampaign
from autoengineering.utility.native_costs import join_native_costs

ARCHIVE = (Path(__file__).resolve().parents[1]
           / "examples/utility/verification-engineering-envelope-supervised-v1/public")


def forbid(*args, **kwargs):
    pytest.fail("archive replay attempted live execution")


def test_actual_envelope_selection_and_support_costs_replay(tmp_path, monkeypatch):
    root = tmp_path / "public"
    shutil.copytree(ARCHIVE, root)
    monkeypatch.setattr(socket, "socket", forbid)
    monkeypatch.setattr(subprocess, "Popen", forbid)
    batch = BatchStore(root / "batch")
    campaign = EngineeringCampaign(root / "campaign", batch, inspect_only=True)
    state = campaign.state()
    request = json.loads((root / "request.json").read_text())
    costs = {r.resource: r.quantity for r in join_native_costs(
        batch, {"conventional": digest(request)},
    )}
    assert state["decision"].outcome == "accepted_candidate"
    assert state["selected"].evaluation == state["evaluations"][1].evaluation
    assert len(batch.replay().reservations) == 49 and not batch.replay().pending
    assert costs["native_inner_model_calls"] == 35
    assert costs["native_support_model_calls"] == 1
    assert not state["native_reports"][0].result.optimizer_target_met
    assert not (root / "source").exists()


def test_changed_original_support_evidence_refuses_without_process(tmp_path, monkeypatch):
    root = tmp_path / "public"
    shutil.copytree(ARCHIVE, root)
    batch = BatchStore(root / "batch")
    projection = batch.replay()
    native = next(key for key in projection.reservations if key.startswith("native-"))
    ref = projection.observations[native].evidence[0]
    path = root / "batch" / ref.path
    record = json.loads(path.read_text())
    record["result"]["support_solves"] = []
    path.write_text(json.dumps(record))
    monkeypatch.setattr(socket, "socket", forbid)
    monkeypatch.setattr(subprocess, "Popen", forbid)
    with pytest.raises(ValueError):
        EngineeringCampaign(root / "campaign", batch, inspect_only=True)
