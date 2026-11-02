"""Actual macOS process-boundary probes with synthetic private labels only."""
import json
import sys

import pytest

from autoengineering.campaign.artifacts import reference, put_bytes
from autoengineering.campaign.store import EventStore, StoreError
from autoengineering.utility.contracts import ResourceCap
from autoengineering.utility.outcomes import OutcomeSpec
from autoengineering.utility.private_scoring import PrivateRMSEScorer
from autoengineering.utility.scoring import ConfirmationGrant

pytestmark = pytest.mark.skipif(sys.platform != "darwin", reason="macOS boundary only")
H = "1" * 64


def setup(tmp_path, labels=None, *, create_scorer=True):
    tmp_path.chmod(0o700)
    public = EventStore.create(tmp_path / "public").root
    private = tmp_path / "private"
    private.mkdir(mode=0o700)
    (private / "labels.json").write_text(json.dumps({"labels": labels if labels is not None else [1., 5.], "mask": [True, True]}))
    label = reference(private, "labels.json", media_type="application/json", producer="synthetic-custodian")
    model = put_bytes(public, b'{"synthetic-model":true}', name="model.json",
                      media_type="application/json", producer="synthetic")
    predictions = put_bytes(public, json.dumps({"model_sha256": model.sha256, "partition_digest": H,
        "selection_digest": H, "prediction": [2., 4.]}).encode(), name="predictions.json", media_type="application/json", producer="synthetic")
    if not create_scorer:
        return public, private, model, None, None
    outcome = OutcomeSpec("engineering-outcome-v1", "rmse", "W", "minimize", "mean", H)
    try:
        scorer = PrivateRMSEScorer(public, private, labels=label, predictions=predictions,
                                  partition_digest=H, outcome_contract=outcome)
    except StoreError as error:
        if "memory boundary is unqualified" in str(error):
            pytest.skip("actual macOS data-memory limit unavailable; scorer correctly blocked")
        raise
    grant = ConfirmationGrant(H, H, H, scorer.identity, outcome.digest, model.sha256, H,
                              (ResourceCap("scientific_starts", "count", 1, "reservation"),
                               ResourceCap("active_time", "s", 6., "reservation")))
    return public, private, model, scorer, grant


def test_private_rmse_process_and_saved_score_recovery(tmp_path):
    public, private, model, scorer, grant = setup(tmp_path)
    score = scorer(grant, model)
    assert score.status == "success" and score.value == 1.
    assert scorer.recover(grant, model) == score
    with pytest.raises(StoreError, match="already exists"):
        scorer(grant, model)
    assert not (public / "labels.json").exists()
    assert (private / grant.digest / "process/completion.json").is_file()


def test_invalid_private_values_do_not_escape_in_output_or_public_files(tmp_path):
    public, private, model, scorer, grant = setup(tmp_path, ["PRIVATE-LABEL-CANARY", 5.])
    score = scorer(grant, model)
    assert score.status == "infrastructure_failure" and score.value is None
    process = private / grant.digest / "process"
    assert b"PRIVATE-LABEL-CANARY" not in (process / "stdout.bin").read_bytes()
    assert b"PRIVATE-LABEL-CANARY" not in (process / "stderr.bin").read_bytes()
    for path in public.rglob("*.json"):
        assert "PRIVATE-LABEL-CANARY" not in path.read_text()


def test_unprivileged_workspace_cannot_read_private_label_file(tmp_path):
    from autoengineering.agents.process import supervise_process
    from autoengineering.agents.sandbox import MacOSBoundary
    _, private, _, _, _ = setup(tmp_path, create_scorer=False)
    workspace = tmp_path / "unprivileged-worker"
    workspace.mkdir(mode=0o700)
    (workspace / "probe.py").write_text(
        "from pathlib import Path\n"
        "try:\n"
        f"    Path({str(private / 'labels.json')!r}).read_text()\n"
        "except PermissionError:\n"
        "    print('private-read-denied')\n"
        "else:\n"
        "    print('UNEXPECTED-PRIVATE-READ')\n")
    boundary = MacOSBoundary()
    # Authored OS read probe only. This deliberately tests the sandbox separately
    # from the unqualified data-memory wrapper and never admits a scorer.
    command = ("/usr/bin/sandbox-exec", "-p", boundary.profile(workspace), str(boundary.python),
               "-I", "-S", "-B", str(workspace / "probe.py"))
    result = supervise_process(command,
        directory=tmp_path / "probe-process", cwd=workspace, environment={}, nonce="private-canary-probe",
        stdin=b"", timeout_seconds=5., max_output_bytes=1024, on_launch=lambda _: None,
        parent_watchdog=True)
    assert result.stopped and result.returncode == 0
    assert result.stdout.strip() == b"private-read-denied"


def test_unavailable_memory_stops_before_private_reads(tmp_path, monkeypatch):
    import autoengineering.utility.private_scoring as module
    public, private, _, _, _ = setup(tmp_path, create_scorer=False)
    monkeypatch.setattr(module, "data_limit_available", lambda _: False)
    monkeypatch.setattr(module, "read_bytes", lambda *_: pytest.fail("private bytes accessed before qualification"))
    outcome = OutcomeSpec("engineering-outcome-v1", "rmse", "W", "minimize", "mean", H)
    with pytest.raises(StoreError, match="memory boundary is unqualified"):
        PrivateRMSEScorer(public, private, labels=None, predictions=None, partition_digest=H,
                          outcome_contract=outcome)
