"""Authored runtime fixtures test access order, not container qualification."""

from dataclasses import replace
import json
from pathlib import Path

import pytest

from autoengineering.campaign.artifacts import put_bytes, reference
from autoengineering.campaign.serialization import digest
from autoengineering.campaign.store import StoreError
from autoengineering.utility import container_scoring as module
from autoengineering.utility.private_container_worker import capture_fixed_worker
from autoengineering.utility.contracts import ResourceCap
from autoengineering.utility.outcomes import OutcomeSpec
from autoengineering.utility.scoring import ConfirmationGrant, ConfirmationService
from test_utility_confirmation import selected_suite

H = "1" * 64


class AuthoredRuntime:
    identity = digest({"fixture": "not a qualified container runtime"})

    def __init__(self):
        self.starts = 0
        self.available = True
        self.fault = False

    def preflight(self):
        if not self.available:
            raise StoreError("authored changed daemon")
        return "1.53"

    def run(self, root, *, api_version, job_sha256, labels_sha256):
        assert api_version == "1.53"
        self.starts += 1
        work = root / "workspace"
        import hashlib

        assert hashlib.sha256((work / "job.json").read_bytes()).hexdigest() == job_sha256
        assert hashlib.sha256((work / "labels.json").read_bytes()).hexdigest() == labels_sha256
        (work / "private_score_worker.py").write_bytes(
            Path(module.__file__).with_name("private_score_worker.py").read_bytes()
        )
        result = capture_fixed_worker(work, "score")["score"]
        (root / "authored-result.json").write_text(json.dumps(result))
        if self.fault:
            raise KeyboardInterrupt("authored fault after saved original result")
        return result

    def recover(self, root, *, job_sha256, labels_sha256):
        return json.loads((root / "authored-result.json").read_bytes())


def fixture(tmp_path, monkeypatch, *, suite=False, prediction=None):
    tmp_path.chmod(0o700)
    if suite:
        store, manifest, contract = selected_suite(
            tmp_path, outcome_name="rmse", confirmation_active_time=128
        )
        public, model, selected = store.root, manifest.cells[0].model, store.replay()["frozen"]
    else:
        store = None
        public = tmp_path / "public"
        public.mkdir(mode=0o700)
        (public / "artifacts").mkdir(mode=0o700)
        model = put_bytes(
            public,
            b'{"authored":true}',
            name="model.json",
            media_type="application/json",
            producer="fixture",
        )
        selected = H
        contract = OutcomeSpec("engineering-outcome-v1", "rmse", "W", "minimize", "mean", H)
    private = tmp_path / "private"
    private.mkdir(mode=0o700)
    (private / "labels.json").write_text('{"labels":[1,5],"mask":[true,true]}')
    labels = reference(private, "labels.json", media_type="application/json", producer="fixture")
    predictions = put_bytes(
        public,
        json.dumps(
            {
                "model_sha256": model.sha256,
                "partition_digest": H,
                "selection_digest": selected,
                "prediction": [2, 4] if prediction is None else prediction,
            }
        ).encode(),
        name="predictions.json",
        media_type="application/json",
        producer="fixture",
    )
    runtime = AuthoredRuntime()

    def construct():
        return module.ContainerRMSEScorer(
            public,
            private,
            labels=labels,
            predictions=predictions,
            partition_digest=H,
            outcome_contract=contract,
            runtime=runtime,
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
            ResourceCap("active_time", "s", 64, "reservation"),
        ),
    )
    reads = []
    original = module.read_bytes

    def tracked(root, ref, **kwargs):
        if Path(root) == private:
            assert (private / grant.digest / "private-access.json").exists()
            if store is not None:
                state = store.replay()
                assert len(state["confirmation_accesses"]) == 1
                assert (
                    state["phase_used"][("fixed_evaluations", "confirmation", "scientific_starts")]
                    == 1
                )
            reads.append(ref.sha256)
        return original(root, ref, **kwargs)

    monkeypatch.setattr(module, "read_bytes", tracked)
    return store, scorer, runtime, grant, model, private, reads, construct, contract


def test_constructor_and_recovery_do_not_read_labels_or_start_runtime(tmp_path, monkeypatch):
    _, scorer, runtime, grant, model, private, reads, construct, _ = fixture(tmp_path, monkeypatch)
    assert not reads and runtime.starts == 0
    score = scorer(grant, model)
    assert score.value == 1 and len(reads) == 1 and runtime.starts == 1
    (private / "labels.json").unlink()
    (private / grant.digest / "workspace/labels.json").unlink()
    runtime.available = False
    assert construct().recover(grant, model) == score
    assert runtime.starts == 1 and len(reads) == 1
    with pytest.raises(StoreError, match="already exists"):
        scorer(grant, model)


@pytest.mark.parametrize("prediction", [[], [True, 1], ["not numeric", 1], {"array": [1]}])
def test_bad_public_prediction_refuses_before_label_access(tmp_path, monkeypatch, prediction):
    _, scorer, runtime, grant, model, _, reads, _, _ = fixture(
        tmp_path, monkeypatch, prediction=prediction
    )
    with pytest.raises(StoreError, match="public predictions"):
        scorer(grant, model)
    assert not reads and runtime.starts == 0


def test_changed_daemon_refuses_before_label_access(tmp_path, monkeypatch):
    _, scorer, runtime, grant, model, _, reads, _, _ = fixture(tmp_path, monkeypatch)
    runtime.available = False
    with pytest.raises(StoreError, match="changed daemon"):
        scorer(grant, model)
    assert not reads and runtime.starts == 0


def test_grant_must_cover_entire_reserved_lifecycle(tmp_path, monkeypatch):
    _, scorer, runtime, grant, model, _, reads, _, _ = fixture(tmp_path, monkeypatch)
    short = replace(
        grant, resources=(grant.resources[0], ResourceCap("active_time", "s", 10, "reservation"))
    )
    with pytest.raises(StoreError, match="64 reserved"):
        scorer(short, model)
    assert not reads and runtime.starts == 0


def test_suite_access_reservation_precedes_only_original_label_open(tmp_path, monkeypatch):
    store, scorer, runtime, grant, _, _, reads, _, contract = fixture(
        tmp_path, monkeypatch, suite=True
    )
    service = ConfirmationService(
        store, scorer, scorer_digest=scorer.identity, outcome_contract=contract
    )
    receipt = service.confirm(grant)
    assert service.confirm(grant) == receipt
    assert len(reads) == runtime.starts == 1


def test_stale_scorer_registration_refuses_before_private_read(tmp_path, monkeypatch):
    _, scorer, runtime, grant, model, _, reads, _, _ = fixture(tmp_path, monkeypatch)
    with pytest.raises(StoreError, match="registration"):
        scorer(replace(grant, scorer_digest="0" * 64), model)
    assert not reads and runtime.starts == 0


@pytest.mark.parametrize("name", ["private-access.json", "workspace/job.json"])
def test_recovery_binding_change_refuses_without_new_private_read(tmp_path, monkeypatch, name):
    _, scorer, runtime, grant, model, private, reads, _, _ = fixture(tmp_path, monkeypatch)
    scorer(grant, model)
    path = private / grant.digest / name
    path.write_text('{"changed":true}')
    with pytest.raises(StoreError, match="binding"):
        scorer.recover(grant, model)
    assert len(reads) == runtime.starts == 1
