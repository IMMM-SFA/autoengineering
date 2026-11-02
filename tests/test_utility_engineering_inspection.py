"""Relocated campaign inspection keeps original identities and disables mutation."""

import hashlib
import json
import shutil

import pytest

from autoengineering.agents.batch import BatchStore
from autoengineering.campaign.store import StoreError
from autoengineering.utility.engineering_campaign import EngineeringCampaign
from test_utility_callback_native import campaign_setup
from test_utility_engineering_campaign import request, setup as plain_campaign_setup
from test_utility_engineering_native import native_campaign


def inventory(root):
    return {
        str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in root.rglob("*")
        if p.is_file()
    }


@pytest.mark.parametrize("kind", ["plain", "native", "callback"])
def test_relocated_campaign_inspection_never_executes_or_writes(tmp_path, monkeypatch, kind):
    if kind == "plain":
        campaign, batch, source = plain_campaign_setup(tmp_path)
    elif kind == "native":
        campaign, batch = native_campaign(tmp_path)
        source = campaign.executor.source_root
    else:
        campaign, batch, source = campaign_setup(tmp_path)
    operations = (
        (("baseline", "fixed"),)
        if kind == "plain"
        else (("baseline", "fixed"), ("native", "native"))
    )
    for candidate, mode in operations:
        assert (
            campaign.handle(
                request(
                    campaign, "evaluate", {"candidate_id": candidate, "mode": mode}, id=candidate
                )
            ).status
            == "ok"
        )
    campaign.handle(request(campaign, "review"))
    campaign.handle(request(campaign, "freeze"))
    expected = campaign.state()
    archive = tmp_path / "archive"
    shutil.copytree(batch.root, archive / "batch")
    shutil.copytree(campaign.store.root, archive / "campaign")
    relocated = BatchStore(archive / "batch")
    before = inventory(archive)

    def denied(*args, **kwargs):
        raise AssertionError("archive reader dispatched work")

    monkeypatch.setattr("subprocess.Popen", denied)
    monkeypatch.setattr("socket.socket", denied)
    # Original scientific inputs can disappear. Original path strings remain
    # bound to their old jobs, not interpreted as new filesystem permissions.
    shutil.rmtree(source)
    with pytest.raises(StoreError, match="original case"):
        EngineeringCampaign(archive / "campaign", relocated)
    reader = EngineeringCampaign(archive / "campaign", relocated, inspect_only=True)
    assert reader.state()["selected"] == expected["selected"]
    assert reader.state()["native_reports"] == expected["native_reports"]
    assert reader.identity == campaign.identity
    with pytest.raises(StoreError, match="read only"):
        reader.cancel("forbidden-cancel")
    with pytest.raises(StoreError, match="read only"):
        reader.handle(request(reader, "review", id="forbidden-review"))
    assert inventory(archive) == before


def test_inspection_rejects_executor_or_non_boolean_mode(tmp_path):
    campaign, batch, _ = campaign_setup(tmp_path)
    for value in (1, "true", None):
        with pytest.raises(StoreError):
            EngineeringCampaign(campaign.store.root, batch, inspect_only=value)
    with pytest.raises(StoreError):
        EngineeringCampaign(
            campaign.store.root, batch, executor=campaign.executor, inspect_only=True
        )


@pytest.mark.parametrize("field", ["seed", "scratch_path"])
def test_relocated_inspection_rejects_altered_original_scenario_job(tmp_path, field):
    campaign, batch, _ = campaign_setup(tmp_path)
    assert (
        campaign.handle(
            request(campaign, "evaluate", {"candidate_id": "baseline", "mode": "fixed"})
        ).status
        == "ok"
    )
    archive = tmp_path / "archive"
    shutil.copytree(batch.root, archive / "batch")
    shutil.copytree(campaign.store.root, archive / "campaign")
    scenario = next((archive / "batch/cases/first/engineering-processes").glob("*/scenario.json"))
    data = json.loads(scenario.read_text())
    data[field] = data[field] + 1 if field == "seed" else "/tmp/unrelated-scenario"
    scenario.write_text(json.dumps(data))
    with pytest.raises(StoreError, match="original|archived"):
        EngineeringCampaign(archive / "campaign", BatchStore(archive / "batch"), inspect_only=True)
