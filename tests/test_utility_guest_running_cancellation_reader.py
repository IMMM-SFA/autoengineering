"""A cancelled started guest cannot acquire a vector, zero cost or fresh start."""

from pathlib import Path
import shutil
import socket
import subprocess
import time

import numpy as np
import pytest

from examples.utility import guest_running_cancellation_reader as module

ROOT = Path(__file__).parents[1] / "examples/utility/verification-guest-running-cancellation-v1"
DIGEST = "1109b241cabe528692c185095cff91674300e18b5cd47aa461002dff025a96ef"


def relocated(tmp_path):
    target = tmp_path / "proof"
    shutil.copytree(ROOT, target)
    target.chmod(0o700)
    for path in target.rglob("*"):
        if path.is_dir():
            path.chmod(0o700)
    return target


def test_saved_running_failure_replays_without_execution_arrays_or_clocks(tmp_path, monkeypatch):
    proof = relocated(tmp_path)
    expected = module.read_completion(proof, expected_digest=DIGEST)

    def forbidden(*args, **kwargs):
        raise AssertionError(
            "saved running cancellation attempted execution, clock, network or array load"
        )

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
    assert expected["status"] == "infrastructure_failure"
    assert expected["model_result"] is expected["lifecycle_seconds"] is None
    assert expected["charged_inference_starts"] == 1
    assert expected["new_container_starts"] == 0


@pytest.mark.parametrize(
    "field,value",
    [("running", False), ("boundary", "after_model_computation"), ("event_digest", "0" * 64)],
)
def test_changed_running_boundary_refuses(tmp_path, field, value):
    proof = relocated(tmp_path)
    marker = module.fixture.read(proof, "cancellation-trigger.json")
    marker[field] = value
    (proof / "cancellation-trigger.json").unlink()
    module.fixture.save(proof, "cancellation-trigger.json", marker)
    with pytest.raises(ValueError, match="transition"):
        module.read_completion(proof, expected_digest=DIGEST)
