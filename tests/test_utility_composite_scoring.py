"""Actual authored inference and fixed score worker; no runtime/data qualification."""

from dataclasses import replace
import json
import shutil
import subprocess
import sys

import pytest

from autoengineering.campaign.artifacts import read_bytes, reference
from autoengineering.campaign.serialization import digest
from autoengineering.campaign.store import StoreError
from autoengineering.utility.composite_scoring import (
    CompositeRMSEScorer,
    CompositeConfirmationService,
    validate_composite_receipt,
)
from autoengineering.utility.confirmation import read_selected_state
from autoengineering.utility.costs import join_confirmation_costs
from autoengineering.utility.inference_evidence import FrozenInferenceArchive
from autoengineering.utility.outcomes import OutcomeSpec
from autoengineering.utility.scoring import ConfirmationGrant, ConfirmationReceipt
from autoengineering.utility.store import SuiteStore
from test_utility_container_scoring import AuthoredRuntime
from test_utility_frozen_inference import setup as inference_setup


class RecordedAuthoredRuntime(AuthoredRuntime):
    """Authored metadata exercises bindings; these are not daemon attestations."""

    def execution_evidence(self, root, *, job_sha256, labels_sha256):
        score = self.recover(root, job_sha256=job_sha256, labels_sha256=labels_sha256)
        return dict(
            score=score,
            runtime_digest=self.identity,
            container_id=digest({"authored": str(root)}),
            nonce="a" * 32,
            image_id="sha256:" + "b" * 64,
            runtime_source_digest="c" * 64,
            wrapper_source_digest="d" * 64,
            worker_source_digest="e" * 64,
            start_receipt_digest="f" * 64,
            stop_receipt_digest="1" * 64,
            cleanup_receipt_digest="2" * 64,
            container_starts=1,
            scoring_process_starts=1,
            lifecycle_seconds=0.1,
        )


def setup(tmp_path, monkeypatch, *, change=None):
    store, grant, executor, _ = inference_setup(
        tmp_path, monkeypatch, authorize=False, change=change
    )
    model = read_selected_state(store.root, grant.inference.selected_state)
    task = store.spec.tasks[0]
    outcome = OutcomeSpec("engineering-outcome-v1", "rmse", "mm/day", "minimize", "mean", "1" * 64)
    assert outcome.digest == task.scoring_outcome_identity
    private = tmp_path / "private-scoring"
    private.mkdir(mode=0o700)
    # Label values stay in this authored private fixture; only their hash is public.
    clock = grant.inference.forcing.ports[0].time
    (private / "labels.json").write_text(
        json.dumps(
            {
                "labels": [0.0] * len(clock.dates),
                "mask": list(clock.scoring_mask),
            }
        )
    )
    labels = reference(private, "labels.json", media_type="application/json", producer="author")
    runtime = RecordedAuthoredRuntime()
    scorer = CompositeRMSEScorer(
        executor,
        private,
        labels=labels,
        runtime=runtime,
        inference=grant.inference,
        partition_digest=grant.partition_digest,
        outcome_contract=outcome,
    )
    grant = replace(grant, scorer_digest=scorer.identity)
    service = CompositeConfirmationService(
        store,
        scorer,
        scorer_digest=scorer.identity,
        outcome_contract=outcome,
    )
    return store, grant, executor, scorer, service, model, runtime


def test_actual_chain_preserves_parent_identity_counts_and_cold_replay(tmp_path, monkeypatch):
    store, grant, executor, scorer, service, _, runtime = setup(tmp_path, monkeypatch)
    receipt = service.confirm(grant)
    assert receipt.score.status == "success" and runtime.starts == 1
    assert receipt.measurement.scorer_digest == grant.scorer_digest == scorer.registration.digest
    assert (
        receipt.execution is None
        and receipt.composite.registration.boundary == "unqualified-candidate"
    )
    evidence = receipt.composite
    child = ConfirmationGrant.from_json(read_bytes(store.root, evidence.inner_grant).decode())
    assert child.scorer_digest != grant.scorer_digest and child.scientific_starts == 1
    assert evidence.inner_execution.grant_digest == child.digest
    archive = FrozenInferenceArchive.from_json(
        read_bytes(store.root, evidence.inference_archive).decode()
    )
    prediction = json.loads(read_bytes(store.root, archive.predictions))["prediction"]
    mask = grant.inference.forcing.ports[0].time.scoring_mask
    expected = (sum(v * v for v, keep in zip(prediction, mask) if keep) / sum(mask)) ** 0.5
    assert receipt.score.value == pytest.approx(expected)
    state = store.replay()
    assert state["phase_used"][("fixed_evaluations", "confirmation", "scientific_starts")] == 2
    assert len(state["confirmation_scores"]) == len(state["confirmation_accesses"]) == 1
    costs = {r.resource: r.quantity for r in join_confirmation_costs(store)}
    assert costs["confirmation_inference_starts"] == costs["confirmation_scoring_starts"] == 1
    assert costs["confirmation_container_starts"] == 1
    assert costs["confirmation_inference_lifecycle_duration"] >= 0
    assert "private-scoring" not in receipt.to_json()
    assert "labels.json" not in receipt.to_json()
    assert service.confirm(grant) == receipt and runtime.starts == 1

    # A copied public suite alone reconstructs the complete chain. No original
    # source, driver, private labels, work tree, model import or execution is needed.
    relocated = tmp_path / "relocated-suite"
    shutil.copytree(store.root, relocated)
    for root in (
        executor.driver_root,
        executor.work_root,
        scorer.private_root,
        executor.source_root,
    ):
        shutil.rmtree(root)
    monkeypatch.setattr(
        "autoengineering.utility.inference_execution.supervise",
        lambda *_a, **_k: pytest.fail("rerun"),
    )
    monkeypatch.setattr(
        "autoengineering.utility.inference_execution.live_members",
        lambda *_a: pytest.fail("process inspection"),
    )
    monkeypatch.setattr(runtime, "run", lambda *_a, **_k: pytest.fail("score rerun"))
    assert SuiteStore(relocated).replay() == state
    assert {r.resource: r.quantity for r in join_confirmation_costs(SuiteStore(relocated))} == costs
    script = """
import importlib.abc,sys
class NoModels(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,*args):
  if fullname.split('.')[0] in {'examples','torch','openmdao','pvlib','py_wake'}:raise AssertionError('model import')
sys.meta_path.insert(0,NoModels())
from pathlib import Path
from autoengineering.utility.store import SuiteStore
from autoengineering.utility.costs import join_confirmation_costs
from autoengineering.utility import composite_scoring,inference_execution
import numpy,scipy.optimize,subprocess,socket,os
def forbidden(*args,**kwargs):raise AssertionError('execution or array load')
numpy.load=scipy.optimize.least_squares=scipy.optimize.minimize=subprocess.Popen=socket.socket=forbidden
inference_execution.supervise=inference_execution.live_members=forbidden
root=Path(sys.argv[1]);allowed={p for p in root.rglob('*') if p.is_file()}
old=Path.open;old_os=os.open
def guarded(path,*args,**kwargs):
 if path not in allowed:raise AssertionError('ungranted read')
 return old(path,*args,**kwargs)
def guarded_os(path,flags,*args,**kwargs):
 if Path(path) not in allowed or flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT):raise AssertionError('ungranted read/write')
 return old_os(path,flags,*args,**kwargs)
Path.open=guarded;os.open=guarded_os
store=SuiteStore(root)
assert len(store.replay()['confirmation_scores'])==1
assert next(r.quantity for r in join_confirmation_costs(store) if r.resource=='confirmation_inference_starts')==1
print('cold composite replay verified')
"""
    cold = subprocess.run(
        [sys.executable, "-c", script, str(relocated)],
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    assert cold.stdout.strip() == "cold composite replay verified"


@pytest.mark.parametrize("point", ["composite_inference_committed", "confirmation_score_created"])
def test_interruption_preserves_two_charges_and_never_repeats_science(tmp_path, monkeypatch, point):
    store, grant, executor, scorer, service, _, runtime = setup(tmp_path, monkeypatch)

    def fault(where):
        if where == point:
            raise KeyboardInterrupt("authored stage loss")

    store.fault = fault
    with pytest.raises(KeyboardInterrupt):
        service.confirm(grant)
    assert len(store.replay()["confirmation_accesses"]) == 1
    assert not store.replay()["confirmation_scores"]
    costs = {r.resource: r.quantity for r in join_confirmation_costs(store)}
    assert costs["confirmation_inference_starts"] == 1
    assert costs["confirmation_scoring_starts"] is None
    before = runtime.starts
    with pytest.raises(StoreError, match="uncertain"):
        service.confirm(grant)
    monkeypatch.setattr(executor, "execute", lambda *_a: pytest.fail("inference repeated"))
    monkeypatch.setattr(runtime, "run", lambda *_a, **_k: pytest.fail("score repeated"))
    (scorer.private_root / "labels.json").unlink()
    shutil.rmtree(executor.driver_root)
    shutil.rmtree(executor.work_root)
    store.fault = lambda _p: None
    if point == "composite_inference_committed":
        with pytest.raises(StoreError, match="unverified"):
            service.recover(grant)
        assert runtime.starts == 0 and not store.replay()["confirmation_scores"]
    else:
        receipt = service.recover(grant)
        assert receipt.score.status == "success" and receipt.recovery is not None
        assert receipt.measurement is None
        assert service.recover(grant) == receipt
    assert runtime.starts == before
    assert (
        store.replay()["phase_used"][("fixed_evaluations", "confirmation", "scientific_starts")]
        == 2
    )


def test_cancellation_between_stages_blocks_label_access(tmp_path, monkeypatch):
    store, grant, _, scorer, service, _, runtime = setup(tmp_path, monkeypatch)
    (scorer.private_root / "labels.json").unlink()

    def fault(point):
        if point == "composite_inference_committed":
            store.append(
                request_id="authored-stage-cancel",
                operation="cancel",
                cell_digest=grant.cell_digest,
                attempt_id="cancel-composite",
                child_digest=grant.digest,
                phase="confirmation",
            )

    store.fault = fault
    with pytest.raises(StoreError, match="charges retained"):
        service.confirm(grant)
    assert store.replay()["cancelled"] and runtime.starts == 0
    assert not store.replay()["confirmation_scores"]
    assert len(store.replay()["confirmation_accesses"]) == 1
    assert not (scorer.private_root / "labels.json").exists()
    assert {r.resource: r.quantity for r in join_confirmation_costs(store)}[
        "confirmation_inference_starts"
    ] == 1


@pytest.mark.parametrize(
    "change,status",
    [("prefix", "model_failure"), ("output", "infrastructure_failure"), ("timeout", "timeout")],
)
def test_inference_failure_never_opens_labels_or_starts_scoring(
    tmp_path, monkeypatch, change, status
):
    store, grant, _, scorer, service, _, runtime = setup(tmp_path, monkeypatch, change=change)
    (scorer.private_root / "labels.json").unlink()
    monkeypatch.setattr(
        runtime, "preflight", lambda: pytest.fail("scorer entered after inference failure")
    )
    receipt = service.confirm(grant)
    assert receipt.score.status == status and receipt.score.value is None
    assert receipt.composite.inner_execution is receipt.composite.inner_grant is None
    assert runtime.starts == 0
    costs = {r.resource: r.quantity for r in join_confirmation_costs(store)}
    assert costs["confirmation_scoring_starts"] == 0
    assert costs["confirmation_inference_starts"] == 1


def test_foreign_inner_identity_and_corrupt_inference_cannot_complete_parent(tmp_path, monkeypatch):
    store, grant, _, _, service, _, _ = setup(tmp_path, monkeypatch)
    receipt = service.confirm(grant)
    nested = receipt.composite
    variants = [
        replace(nested, registration=replace(nested.registration, labels_digest="3" * 64)),
        replace(nested, inner_execution=replace(nested.inner_execution, scorer_digest="4" * 64)),
        replace(nested, inner_execution=replace(nested.inner_execution, runtime_digest="5" * 64)),
        replace(nested, inner_execution=replace(nested.inner_execution, grant_digest="6" * 64)),
    ]
    for evidence in variants:
        with pytest.raises(StoreError):
            validate_composite_receipt(store, grant, replace(receipt, composite=evidence))
    assert ConfirmationReceipt.from_json(receipt.to_json()) == receipt
    archive = FrozenInferenceArchive.from_json(
        read_bytes(store.root, nested.inference_archive).decode()
    )
    for ref in (
        archive.job,
        archive.supervisor,
        archive.result,
        archive.outputs,
        archive.predictions,
    ):
        path = store.root / ref.path
        original = path.read_bytes()
        path.write_bytes(original + b" ")
        with pytest.raises((StoreError, ValueError)):
            SuiteStore(store.root).replay()
        path.write_bytes(original)
    assert service.confirm(grant) == receipt
