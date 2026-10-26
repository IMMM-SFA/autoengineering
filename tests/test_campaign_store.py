"""Commit-boundary recovery, corruption refusal, concurrency and projection replay."""

from dataclasses import replace
import json

import pytest

from autoengineering.campaign.artifacts import reference
from autoengineering.campaign.records import CampaignEvent, Response
from autoengineering.campaign.serialization import digest
from autoengineering.campaign.store import EventStore, StoreError, WriterBusy


def event(revision=1, previous=None, from_state="created", to_state="baseline_ready", artifacts=()):
    return CampaignEvent(
        revision,
        digest({"command": revision}),
        previous,
        "controller",
        "evaluate",
        from_state,
        to_state,
        Response(
            f"request-{revision}",
            "ok",
            revision,
            {"state": to_state},
            None,
            tuple(ref.sha256 for ref in artifacts),
        ),
        artifacts,
    )


def test_replay_ignores_projection_and_rebuilds_without_models(tmp_path):
    store = EventStore.create(tmp_path / "campaign")
    first = event()
    with store.writer():
        store.commit(first)
        second = event(2, first.digest, "baseline_ready", "proposal_open")
        store.commit(second)
    expected = store.replay().to_dict()
    (store.root / "state.json").write_text('{"state":"wrong"}')
    assert store.replay().to_dict() == expected
    (store.root / "state.json").unlink()
    with store.writer():
        assert store.refresh_projection().to_dict() == expected
    assert json.loads((store.root / "state.json").read_text()) == expected


@pytest.mark.parametrize(
    "boundary,committed",
    [
        ("before_staging", False),
        ("after_artifact_durability", False),
        ("after_event_commit", True),
        ("after_projection", True),
        ("before_acknowledgment", True),
    ],
)
def test_commit_crashes_have_one_authoritative_result(tmp_path, boundary, committed):
    def fail(stage):
        if stage == boundary:
            raise RuntimeError("injected crash")

    store = EventStore.create(tmp_path / "campaign", fault=fail)
    with store.writer(), pytest.raises(RuntimeError):
        store.commit(event())
    recovered = EventStore(store.root)
    assert recovered.replay().revision == int(committed)
    with recovered.writer():
        if not committed:
            recovered.commit(event())
        recovered.refresh_projection()
    assert recovered.replay().revision == 1
    assert recovered.replay().responses["request-1"][1] == event().response


@pytest.mark.parametrize(
    "corruption", ["gap", "modified", "noncanonical", "symlink", "missing_result"]
)
def test_corruption_refuses_without_rewriting_bytes(tmp_path, corruption):
    store = EventStore.create(tmp_path / "campaign")
    result_path = store.root / "artifacts/result.json"
    result_path.write_text('{"value":1}')
    artifact = reference(
        store.root, "artifacts/result.json", media_type="application/json", producer="test"
    )
    first = event(artifacts=(artifact,))
    with store.writer():
        store.commit(first)
        store.commit(event(2, first.digest, "baseline_ready", "proposal_open"))
    path = store.events_path / "000000000001.json"
    if corruption == "gap":
        path.unlink()
    elif corruption == "modified":
        raw = path.read_text().replace('"baseline_ready"', '"candidate_ready"')
        path.write_text(raw)
    elif corruption == "noncanonical":
        path.write_text(path.read_text() + "\n")
    elif corruption == "symlink":
        saved = path.read_bytes()
        path.unlink()
        (tmp_path / "event.json").write_bytes(saved)
        path.symlink_to(tmp_path / "event.json")
    else:
        result_path.unlink()
    before = {str(p): p.read_bytes() for p in store.root.rglob("*") if p.is_file()}
    with pytest.raises(StoreError):
        store.replay()
    after = {str(p): p.read_bytes() for p in store.root.rglob("*") if p.is_file()}
    assert before == after


def test_single_writer_and_no_overwrite(tmp_path):
    store = EventStore.create(tmp_path / "campaign")
    another = EventStore(store.root)
    with store.writer():
        with pytest.raises(WriterBusy), another.writer():
            pass
        store.commit(event())
        with pytest.raises(StoreError):
            store.commit(event())
    assert store.replay().revision == 1
    with pytest.raises(StoreError, match="lock"):
        store.commit(event())
    with pytest.raises(StoreError, match="nonempty|absent or empty"):
        EventStore.create(store.root)


def test_torn_temporary_evidence_is_preserved_and_not_replayed(tmp_path):
    store = EventStore.create(tmp_path / "campaign")
    torn = store.events_path / ".event.partial.tmp"
    torn.write_bytes(b'{"revision":')
    assert store.replay().revision == 0
    with store.writer():
        preserved = store.quarantine_temporaries()
    assert len(preserved) == 1
    assert (store.root / preserved[0]).read_bytes() == b'{"revision":'
    assert not torn.exists()


def test_committed_result_hash_modification_and_invalid_chain(tmp_path):
    store = EventStore.create(tmp_path / "campaign")
    with store.writer():
        store.commit(event())
        with pytest.raises(StoreError):
            store.commit(event(2, "0" * 64, "baseline_ready", "proposal_open"))
        response = replace(event(2).response, artifact_ids=("0" * 64,))
        invalid = replace(
            event(2, event().digest, "baseline_ready", "proposal_open"), response=response
        )
        with pytest.raises(StoreError):
            store.commit(invalid)
    assert store.replay().revision == 1


def test_tail_event_has_its_own_checksum(tmp_path):
    store = EventStore.create(tmp_path / "campaign")
    with store.writer():
        store.commit(event())
    path = store.events_path / "000000000001.json"
    raw = json.loads(path.read_text())
    raw["event"]["response"]["result"]["state"] = "fabricated"
    from autoengineering.campaign.serialization import canonical_json

    path.write_text(canonical_json(raw) + "\n")
    with pytest.raises(StoreError, match="malformed"):
        store.replay()
