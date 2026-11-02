"""Campaign costs follow committed state and never rerun scientific code."""

import shutil
from dataclasses import replace

import pytest

from autoengineering.agents.batch import BatchStore
from autoengineering.campaign.artifacts import read_bytes
from autoengineering.campaign.serialization import unique_json
from autoengineering.utility.campaign_costs import join_campaign_costs
from test_agent_batch_science import fixture

MAPPING = {"model": "1" * 64}


def completed(tmp_path):
    batch, controller = fixture(tmp_path)
    assert controller.advance().state == "completed"
    return batch, controller


def interrupted_completed_worker(tmp_path, monkeypatch):
    batch, controller = fixture(tmp_path)
    checkpoint = controller._checkpoint

    class AuthoredLoss(BaseException):
        pass

    def lose_before_commit(target, state, reason, artifacts=()):
        if reason == "action_finished":
            raise AuthoredLoss("authored loss after worker output before campaign commit")
        return checkpoint(target, state, reason, artifacts)

    monkeypatch.setattr(controller, "_checkpoint", lose_before_commit)
    with pytest.raises(AuthoredLoss):
        controller.advance()
    monkeypatch.setattr(controller, "_checkpoint", checkpoint)
    assert len(batch.replay().pending) == 1
    assert len(controller.state().budget.attempts) == 1
    return batch, controller


def test_recovery_refuses_malformed_process_group_identity(tmp_path, monkeypatch):
    from autoengineering.campaign.serialization import canonical_json
    from autoengineering.campaign.store import StoreError

    batch, controller = interrupted_completed_worker(tmp_path, monkeypatch)
    path = controller.store.root / "attempts/attempt-000001/process.json"
    value = unique_json(path.read_text())
    value.update(pid=-1, pgid=-1)
    path.write_text(canonical_json(value))
    with pytest.raises(StoreError):
        controller.reconcile_batch()
    assert len(batch.replay().pending) == len(batch.replay().reservations) == 1
    assert controller.state().budget.unresolved_attempts == 1


def test_recovered_worker_settles_original_batch_charge_and_retains_lifecycle(
    tmp_path, monkeypatch
):
    batch, controller = interrupted_completed_worker(tmp_path, monkeypatch)
    files = sorted((controller.store.root / "attempts").glob("*/action-start.json"))
    assert len(files) == 1
    original = [p.read_bytes() for p in files]
    controller.reconcile_batch()
    assert not batch.replay().pending and len(batch.replay().reservations) == 1
    assert [p.read_bytes() for p in files] == original
    assert len(list((controller.store.root / "attempts").glob("*/action-start.json"))) == 1
    attempt = controller.state().budget.attempts[0]
    receipt = unique_json(read_bytes(controller.store.root, attempt.receipt).decode())
    assert receipt["schema"] == "campaign-recovery-receipt-v2"
    assert receipt["identity"]["nonce"] == attempt.launch_nonce and receipt["stopped"]
    assert controller.state().evaluations[0].provenance["execution_seed"] == str(
        controller.spec.seed
    )
    records = join_campaign_costs(batch, MAPPING)
    assert len(records) == 2 and all(r.quantity is not None for r in records)
    before = batch.replay()
    controller.reconcile_batch()
    assert batch.replay() == before


def test_legacy_recovery_without_process_identity_keeps_unknown_work(tmp_path, monkeypatch):
    from autoengineering.campaign.artifacts import put_bytes
    from autoengineering.campaign.serialization import canonical_json

    batch, controller = interrupted_completed_worker(tmp_path, monkeypatch)
    recover = controller._recover_finished

    def legacy_serialization(attempt):
        resolved, evaluation, refs = recover(attempt)
        value = unique_json(read_bytes(controller.store.root, resolved.receipt).decode())
        legacy = {k: value[k] for k in ("attempt_id", "nonce", "output_sha256", "recovered")}
        ref = put_bytes(
            controller.store.root,
            canonical_json(legacy).encode(),
            name="recovery-receipt.json",
            media_type="application/json",
            producer="authored-legacy-serialization",
        )
        provenance = {k: v for k, v in evaluation.provenance.items() if k != "lifecycle_record"}
        return (
            replace(resolved, receipt=ref),
            replace(evaluation, provenance=provenance),
            (
                *evaluation.outputs,
                ref,
            ),
        )

    monkeypatch.setattr(controller, "_recover_finished", legacy_serialization)
    controller.reconcile_batch()
    assert len(batch.replay().pending) == 1
    records = join_campaign_costs(batch, MAPPING)
    assert len(records) == 2 and all(r.quantity is None for r in records)
    assert len(batch.replay().reservations) == 1


def test_campaign_costs_use_committed_lifecycle_and_ignore_scratch_cache(tmp_path, monkeypatch):
    batch, controller = completed(tmp_path)
    state = controller.state()
    expected = {}
    for evaluation in state.evaluations:
        ref = next(
            ref
            for event in controller.store.replay().events
            for ref in event.artifacts
            if ref.sha256 == evaluation.provenance["lifecycle_record"]
        )
        expected[ref.producer] = unique_json(read_bytes(controller.store.root, ref).decode())[
            "elapsed_seconds"
        ]
    # The projection cache and mutable scratch metadata are not authoritative.
    (controller.store.root / "state.json").write_text("not a controller state")
    for path in (controller.store.root / "jobs").glob("*.metadata.json"):
        path.write_text('{"elapsed_seconds": 999999999}')
    before = batch.replay()
    monkeypatch.setattr("subprocess.Popen", lambda *_a, **_k: pytest.fail("reader launched"))
    records = join_campaign_costs(batch, MAPPING)
    starts = [r for r in records if r.resource == "campaign_process_starts"]
    durations = [r for r in records if r.resource == "campaign_model_lifecycle_duration"]
    assert len(starts) == len(expected) == 2 and all(r.quantity == 1 for r in starts)
    assert sorted(r.quantity for r in durations) == sorted(expected.values())
    assert all(r.cell_digests == (MAPPING["model"],) for r in records)
    assert not any("training" in r.resource for r in records)
    assert join_campaign_costs(batch, MAPPING) == records
    assert batch.replay() == before


def test_relocated_campaign_reader_needs_no_original_roots(tmp_path, monkeypatch):
    batch, _ = completed(tmp_path)
    expected = join_campaign_costs(batch, MAPPING)
    copy = tmp_path / "relocated"
    shutil.copytree(batch.root, copy)
    shutil.rmtree(batch.root)
    monkeypatch.setattr("subprocess.Popen", lambda *_a, **_k: pytest.fail("reader launched"))
    assert join_campaign_costs(BatchStore(copy), MAPPING) == expected


@pytest.mark.parametrize("target", ["lifecycle", "output", "receipt", "state", "specification"])
def test_modified_committed_campaign_evidence_cannot_supply_costs(tmp_path, target):
    batch, controller = completed(tmp_path)
    state = controller.state()
    events = controller.store.replay().events
    if target == "lifecycle":
        ref = next(
            r for event in events for r in event.artifacts if r.path.endswith("/lifecycle.json")
        )
    elif target == "output":
        ref = state.evaluations[0].outputs[0]
    elif target == "receipt":
        ref = state.budget.attempts[0].receipt
    elif target == "state":
        ref = next(r for r in events[-1].artifacts if r.path.endswith("/state.json"))
    else:
        (controller.store.root / "campaign.yaml").write_text("{}")
        ref = None
    if ref:
        (controller.store.root / ref.path).write_bytes(b"corrupt committed bytes")
    with pytest.raises(ValueError):
        join_campaign_costs(batch, MAPPING)
    assert len(batch.replay().reservations) == 2


def test_failed_worker_keeps_known_outer_start_and_unknown_lifecycle(tmp_path, monkeypatch):
    import test_agent_batch_science as fixtures

    spec = fixtures.agent_fixture()
    spec = replace(spec, execution=replace(spec.execution, timeout_seconds=0.01))
    monkeypatch.setattr(fixtures, "agent_fixture", lambda: spec)
    batch, controller = fixture(tmp_path)
    controller.advance()
    records = join_campaign_costs(batch, MAPPING)
    assert records
    assert all(r.quantity == 1 for r in records if r.resource == "campaign_process_starts")
    assert all(
        r.quantity is None for r in records if r.resource == "campaign_model_lifecycle_duration"
    )


def test_pending_campaign_permission_does_not_invent_processes(tmp_path):
    from test_agent_batch import reservation

    batch, _ = fixture(tmp_path)
    batch.reserve(reservation(case="model", resource="science", at=batch.clock()))
    assert join_campaign_costs(batch, MAPPING) == ()
    assert len(batch.replay().pending) == 1


@pytest.mark.parametrize("mapping", [{}, {"foreign": "1" * 64}])
def test_campaign_cost_mapping_cannot_drop_reserved_case(tmp_path, mapping):
    batch, _ = fixture(tmp_path)
    with pytest.raises(ValueError, match="mapping"):
        join_campaign_costs(batch, mapping)


def test_suite_reports_campaign_costs_without_dispatch_and_blocks_corruption(tmp_path, monkeypatch):
    from autoengineering.utility.execution import ScriptedCoordinator
    from autoengineering.utility.report import accounting_report
    from test_utility_execution import setup

    store, plan, source = setup(tmp_path)
    assert ScriptedCoordinator(store, plan, source).run()["finished_cells"] == 2
    head = store.replay()["head"]
    monkeypatch.setattr("subprocess.Popen", lambda *_a, **_k: pytest.fail("reader launched"))
    report = accounting_report(store)
    rows = [r for r in report["receipts"] if r["resource"].startswith("campaign_")]
    assert rows and not report["evidence_blockers"]
    assert all(r["quantity"] is not None for r in rows)
    assert not report["complete_cost_evidence"]
    assert accounting_report(store) == report and store.replay()["head"] == head
    path = next(store.root.glob("children/*/cases/*/campaign/artifacts/*/lifecycle.json"))
    path.write_bytes(b"corrupt")
    assert accounting_report(store)["evidence_blockers"]
