"""Saved parity verifies arrays and rejects changed evidence without execution."""

from pathlib import Path
import shutil
import socket
import subprocess

import pytest

from examples.utility import guest_parity_reader as module

ROOT = Path(__file__).parents[1] / "examples/utility/verification-guest-prediction-parity-v1"
DIGEST = "d01f44b5195cca2ece81f49d2276e4641e8f9796570c7c72800fedb3eaba9f35"


def test_relocated_parity_recomputes_without_process_or_network(tmp_path, monkeypatch):
    proof = tmp_path / "relocated"
    shutil.copytree(ROOT, proof)

    def forbidden(*args, **kwargs):
        pytest.fail("saved parity attempted execution or network")

    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    result = module.read_completion(proof, expected_digest=DIGEST)
    assert result["all_outputs_within_tolerance"]
    assert result["prediction_vector"]["within_tolerance"]
    assert not result["prediction_document_exact"]
    assert result["new_processes"] == 0


@pytest.mark.parametrize(
    "name",
    [
        "native-outputs.npz",
        "guest-outputs.npz",
        "runner.py.txt",
        "native-predictions.json",
        "supervisor-result.json",
    ],
)
def test_changed_saved_evidence_is_refused(tmp_path, name):
    proof = tmp_path / "proof"
    shutil.copytree(ROOT, proof)
    path = proof / name
    if name == "supervisor-result.json":
        value = module.fixture.read(proof, name)
        value["stopped"] = False
        path.unlink()
        module.fixture.save(proof, name, value)
    else:
        path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ValueError):
        module.read_completion(proof, expected_digest=DIGEST)
