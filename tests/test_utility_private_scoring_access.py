"""Private-access accounting with synthetic labels and an authored boundary.

The boundary stub runs the fixed worker without a sandbox. No test here qualifies
memory limits, OS privacy, real labels or independent confirmation.
"""

from dataclasses import replace
import json
from pathlib import Path
import sys

import pytest

from autoengineering.campaign.artifacts import put_bytes, reference
from autoengineering.campaign.serialization import digest
from autoengineering.campaign.store import StoreError
from autoengineering.utility import private_scoring as module
from autoengineering.utility.contracts import ResourceCap
from autoengineering.utility.outcomes import OutcomeSpec
from autoengineering.utility.scoring import ConfirmationGrant, ConfirmationService
from autoengineering.utility.store import SuiteStore
from test_utility_confirmation import selected_suite

H = "1" * 64


class AuthoredBoundary:
    def identity(self, root, limits):
        return digest({"scope": "authored boundary, not qualification", "root": str(root)})

    def command(self, root, entrypoint, limits):
        return (str(Path(sys.executable).resolve()), "-I", "-S", str(root / entrypoint))


def fixture(tmp_path, monkeypatch, *, suite=False, prediction=None):
    tmp_path.chmod(0o700)
    if suite:
        store, manifest, contract = selected_suite(
            tmp_path,
            outcome_name="rmse",
            confirmation_active_time=12,
        )
        public, model = store.root, manifest.cells[0].model
        selected = store.replay()["frozen"]
    else:
        store = None
        public = tmp_path / "public"
        public.mkdir(mode=0o700)
        (public / "artifacts").mkdir(mode=0o700)
        model = put_bytes(
            public,
            b'{"synthetic":true}',
            name="model.json",
            media_type="application/json",
            producer="fixture",
        )
        contract = OutcomeSpec("engineering-outcome-v1", "rmse", "W", "minimize", "mean", H)
        selected = H
    private = tmp_path / "private"
    private.mkdir(mode=0o700)
    (private / "labels.json").write_text('{"labels":[1,5],"mask":[true,true]}')
    labels = reference(
        private, "labels.json", media_type="application/json", producer="fixture-custodian"
    )
    document = {
        "model_sha256": model.sha256,
        "partition_digest": H,
        "selection_digest": selected,
        "prediction": [2, 4] if prediction is None else prediction,
    }
    predictions = put_bytes(
        public,
        json.dumps(document).encode(),
        name="predictions.json",
        media_type="application/json",
        producer="fixture",
    )
    monkeypatch.setattr(module, "MacOSBoundary", AuthoredBoundary)
    monkeypatch.setattr(module, "data_limit_available", lambda _: True)
    reads = []
    original = module.read_bytes

    def tracked(root, artifact, **kwargs):
        if Path(root) == private:
            attempts = list(private.glob("*/private-access.json"))
            assert len(attempts) == 1, "private read before durable access intent"
            intent = json.loads(attempts[0].read_text())
            assert intent["labels_sha256"] == labels.sha256
            if store is not None:
                assert len(store.replay()["confirmation_accesses"]) == 1
                assert (
                    store.replay()["phase_used"][
                        ("fixed_evaluations", "confirmation", "scientific_starts")
                    ]
                    == 1
                )
            reads.append(artifact.sha256)
        return original(root, artifact, **kwargs)

    monkeypatch.setattr(module, "read_bytes", tracked)

    def construct():
        return module.PrivateRMSEScorer(
            public,
            private,
            labels=labels,
            predictions=predictions,
            partition_digest=H,
            outcome_contract=contract,
        )

    scorer = construct()
    grant = ConfirmationGrant(
        store.spec.digest if store else H,
        store.spec.cells[0].digest if store else H,
        H,
        scorer.identity,
        contract.digest,
        model.sha256,
        selected,
        (
            ResourceCap("scientific_starts", "count", 1, "reservation"),
            ResourceCap("active_time", "s", 6, "reservation"),
        ),
    )
    return store, private, model, scorer, grant, contract, reads, construct


def test_registration_and_reconstruction_never_open_labels(tmp_path, monkeypatch):
    _, private, model, scorer, grant, _, reads, construct = fixture(tmp_path, monkeypatch)
    assert not reads
    score = scorer(grant, model)
    assert score.value == 1 and len(reads) == 1
    (private / "labels.json").unlink()
    (private / grant.digest / "workspace/labels.json").unlink()
    monkeypatch.setattr(
        module, "supervise_process", lambda *_a, **_k: pytest.fail("replacement worker")
    )
    reopened = construct()
    assert reopened.identity == scorer.identity and len(reads) == 1
    assert reopened.recover(grant, model) == score and len(reads) == 1
    with pytest.raises(StoreError, match="already exists"):
        reopened(grant, model)


@pytest.mark.parametrize(
    "prediction", [[True, 1], ["private-like-value", 1], [], {"array": [1, 2]}]
)
def test_invalid_public_predictions_fail_without_private_access(tmp_path, monkeypatch, prediction):
    _, private, model, scorer, grant, _, reads, _ = fixture(
        tmp_path, monkeypatch, prediction=prediction
    )
    with pytest.raises(StoreError, match="public predictions"):
        scorer(grant, model)
    assert not reads and not (private / grant.digest).exists()


def test_stale_grant_refuses_before_private_access(tmp_path, monkeypatch):
    _, private, model, scorer, grant, _, reads, _ = fixture(tmp_path, monkeypatch)
    with pytest.raises(StoreError, match="registration"):
        scorer(replace(grant, partition_digest="2" * 64), model)
    assert not reads and not (private / grant.digest).exists()


def test_confirmation_reservation_and_access_precede_the_only_label_read(tmp_path, monkeypatch):
    store, private, model, scorer, grant, contract, reads, construct = fixture(
        tmp_path, monkeypatch, suite=True
    )
    receipt = ConfirmationService(
        store, scorer, scorer_digest=scorer.identity, outcome_contract=contract
    ).confirm(grant)
    assert receipt.score.value == 1 and len(reads) == 1
    (private / "labels.json").unlink()
    reopened_scorer = construct()
    reopened = ConfirmationService(
        SuiteStore(store.root),
        reopened_scorer,
        scorer_digest=reopened_scorer.identity,
        outcome_contract=contract,
    )
    assert reopened.confirm(grant) == receipt and len(reads) == 1
    assert (
        store.replay()["phase_used"][("fixed_evaluations", "confirmation", "scientific_starts")]
        == 1
    )


@pytest.mark.parametrize(
    "target",
    ["private-access.json", "workspace/job.json", "workspace/score.py", "process/job.json"],
)
def test_recovery_rejects_changed_public_binding_without_label_read(tmp_path, monkeypatch, target):
    _, private, model, scorer, grant, _, reads, construct = fixture(tmp_path, monkeypatch)
    scorer(grant, model)
    (private / grant.digest / target).write_text("{}")
    with pytest.raises(ValueError):
        construct().recover(grant, model)
    assert len(reads) == 1


def test_uncertain_private_read_retains_intent_and_never_retries(tmp_path, monkeypatch):
    store, private, _, scorer, grant, contract, reads, _ = fixture(
        tmp_path, monkeypatch, suite=True
    )
    (private / "labels.json").unlink()
    service = ConfirmationService(
        store, scorer, scorer_digest=scorer.identity, outcome_contract=contract
    )
    with pytest.raises(StoreError, match="uncertain"):
        service.confirm(grant)
    assert len(reads) == 1 and (private / grant.digest / "private-access.json").is_file()
    with pytest.raises(StoreError, match="uncertain"):
        service.confirm(grant)
    assert len(reads) == 1 and len(store.replay()["confirmation_accesses"]) == 1


def test_pre_access_commit_failure_never_opens_labels_or_gets_free_retry(tmp_path, monkeypatch):
    store, private, _, scorer, grant, contract, reads, _ = fixture(
        tmp_path, monkeypatch, suite=True
    )
    original = module.durable_write

    def fail(path, raw):
        if path.name == "private-access.json":
            raise RuntimeError("authored intent commit failure")
        return original(path, raw)

    monkeypatch.setattr(module, "durable_write", fail)
    service = ConfirmationService(
        store, scorer, scorer_digest=scorer.identity, outcome_contract=contract
    )
    with pytest.raises(StoreError, match="uncertain"):
        service.confirm(grant)
    assert not reads and (private / grant.digest).is_dir()
    monkeypatch.setattr(module, "durable_write", original)
    with pytest.raises(StoreError, match="uncertain"):
        service.confirm(grant)
    assert not reads and len(store.replay()["confirmation_accesses"]) == 1


def test_lost_worker_start_preserves_private_access_without_rescoring(tmp_path, monkeypatch):
    store, private, model, scorer, grant, contract, reads, construct = fixture(
        tmp_path, monkeypatch, suite=True
    )

    def fail(*_args, **_kwargs):
        raise RuntimeError("authored worker start uncertainty")

    monkeypatch.setattr(module, "supervise_process", fail)
    service = ConfirmationService(
        store, scorer, scorer_digest=scorer.identity, outcome_contract=contract
    )
    with pytest.raises(StoreError, match="uncertain"):
        service.confirm(grant)
    assert len(reads) == 1 and (private / grant.digest / "private-access.json").is_file()
    reopened = construct()
    with pytest.raises(ValueError):
        reopened.recover(grant, model)
    with pytest.raises(StoreError, match="uncertain"):
        service.confirm(grant)
    assert len(reads) == 1


def test_legacy_scorer_identity_cannot_resume_as_deferred_access_profile(tmp_path, monkeypatch):
    import hashlib

    _, private, model, scorer, grant, _, reads, _ = fixture(tmp_path, monkeypatch)
    legacy = digest(
        {
            "profile": "private-json-rmse-macos-v1",
            "labels": scorer.labels.sha256,
            "predictions": scorer.predictions.sha256,
            "partition": scorer.partition_digest,
            "outcome": scorer.outcome_contract.digest,
            "worker": hashlib.sha256(scorer.worker_bytes).hexdigest(),
            "boundary": scorer.boundary.identity(private, scorer.limits),
            "timeout": scorer.timeout,
        }
    )
    assert legacy != scorer.identity
    with pytest.raises(StoreError, match="registration"):
        scorer(replace(grant, scorer_digest=legacy), model)
    assert not reads and not (private / grant.digest).exists()


def test_changed_scorer_source_changes_registration_before_private_access(tmp_path, monkeypatch):
    _, _, model, scorer, grant, _, reads, construct = fixture(tmp_path, monkeypatch)
    source = tmp_path / "changed-source"
    source.mkdir(mode=0o700)
    parent = source / "private_scoring.py"
    parent.write_bytes(Path(module.__file__).read_bytes() + b"\n# authored changed controller\n")
    (source / "private_score_worker.py").write_bytes(scorer.worker_bytes)
    monkeypatch.setattr(module, "__file__", str(parent))
    changed = construct()
    assert changed.identity != scorer.identity
    with pytest.raises(StoreError, match="registration"):
        changed(grant, model)
    assert not reads
