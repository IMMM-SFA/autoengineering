"""Saved exact-child loss proof cannot replace identities or restart inference."""

from pathlib import Path
import shutil
import socket
import subprocess
import time

import numpy as np
import pytest

from examples.utility import guest_owner_loss_reader as module

ROOT = Path(__file__).parents[1] / "examples/utility/verification-guest-owner-loss-v1"
DIGEST = "b4b98be86d75ebda423dfc0ca2cb7e865fdea16d5227bb67052a7aa901015466"


def relocated(tmp_path):
    target = tmp_path / "proof"
    shutil.copytree(ROOT, target)
    target.chmod(0o700)
    for path in target.rglob("*"):
        if path.is_dir():
            path.chmod(0o700)
    return target


def test_relocation_replays_capture_without_execution_array_loading_or_clocks(
    tmp_path, monkeypatch
):
    proof = relocated(tmp_path)
    expected = module.read_completion(proof, expected_digest=DIGEST)

    def forbidden(*args, **kwargs):
        raise AssertionError("saved owner loss used execution, network, arrays or clocks")

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
    assert sum(r["charged_inference_starts"] for r in expected["results"]) == 2
    assert sum(r["captured_result_replayed"] for r in expected["results"]) == 1
    assert expected["new_container_starts"] == expected["new_processes"] == 0


@pytest.mark.parametrize(
    "case,name,field",
    [
        ("owner_loss_running", "owner-kill-intent.json", "pid"),
        ("owner_loss_before_watchdog_ready", "child-stopped.json", "returncode"),
        ("watchdog_child_loss_before_start", "stage-ready.json", "watchdog_pid"),
        ("owner_loss_after_capture", "stage-ready.json", "journal_head"),
    ],
)
def test_changed_exact_process_or_transition_refuses(tmp_path, case, name, field):
    proof = relocated(tmp_path)
    root = proof / case
    value = module.fixture.read(root, name)
    value[field] = "0" * 64 if field == "journal_head" else 0
    (root / name).unlink()
    module.fixture.save(root, name, value)
    with pytest.raises(ValueError):
        module.read_completion(proof, expected_digest=DIGEST)


def test_missing_captured_output_cannot_be_filled_by_new_inference(tmp_path):
    proof = relocated(tmp_path)
    suite = proof / "owner_loss_after_capture/suite"
    arrays = list(suite.rglob("outputs.npz"))
    assert len(arrays) == 1
    arrays[0].unlink()
    with pytest.raises(ValueError):
        module.read_completion(proof, expected_digest=DIGEST)
