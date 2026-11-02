"""Saved actual acknowledgment loss retains charges and cannot redispatch."""

from pathlib import Path
import shutil
import socket
import subprocess
import time

import numpy as np
import pytest

from examples.utility import guest_response_loss_reader as module

ROOT = Path(__file__).parents[1] / "examples/utility/verification-guest-response-loss-v1"
DIGEST = "1354b94557544a8713f1b06a1500ec657ac25b8a213f80accddd7f6cb5273124"


def relocated(tmp_path):
    target = tmp_path / "proof"
    shutil.copytree(ROOT, target)
    target.chmod(0o700)
    for path in target.rglob("*"):
        if path.is_dir():
            path.chmod(0o700)
    return target


def test_relocated_proof_retains_started_attempt_without_model_result(tmp_path, monkeypatch):
    proof = relocated(tmp_path)
    expected = module.read_completion(proof, expected_digest=DIGEST)

    def forbidden(*args, **kwargs):
        raise AssertionError("saved response loss used execution, clock, network or array load")

    with monkeypatch.context() as patch:
        for owner, name in (
            (subprocess, "Popen"),
            (socket, "socket"),
            (np, "load"),
            (time, "monotonic"),
            (time, "time"),
        ):
            patch.setattr(owner, name, forbidden)
        assert module.read_completion(proof, expected_digest=DIGEST) == expected
    assert [r["charged_inference_starts"] for r in expected["results"]] == [0, 1]
    assert all(r["retry_daemon_requests"] == 0 for r in expected["results"])
    assert expected["new_container_starts"] == 0


def test_changed_actual_acknowledgment_bytes_refuse(tmp_path):
    proof = relocated(tmp_path)
    path = proof / "lost_create_response/api-observations/withheld-response-body.bin"
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ValueError, match="actual response"):
        module.read_completion(proof, expected_digest=DIGEST)


@pytest.mark.parametrize(
    "case,name",
    [
        ("lost_create_response", "daemon-create-response.json"),
        ("lost_start_response", "control/guest-dispatch/start-response.json"),
        ("lost_start_response", "bootstrap-capture.json"),
    ],
)
def test_unobserved_confirmation_cannot_be_added_to_original_owner(tmp_path, case, name):
    proof = relocated(tmp_path)
    (proof / case / "owner" / name).write_text("{}")
    with pytest.raises(ValueError, match="committed"):
        module.read_completion(proof, expected_digest=DIGEST)


def test_missing_original_transfer_refuses_even_before_created_observation(tmp_path):
    proof = relocated(tmp_path)
    owner = proof / "lost_create_response/owner"
    package = module.fixture.read(owner, "input-package.json")
    (owner / package["archive"]["path"]).unlink()
    with pytest.raises(ValueError):
        module.read_completion(proof, expected_digest=DIGEST)
