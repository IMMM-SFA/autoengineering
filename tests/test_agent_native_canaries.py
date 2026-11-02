"""Canary parser and preflight tests. Actual OS probes use an explicit command."""

import json
import hashlib
import ctypes
import os
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from autoengineering.agents.hosts import native_canaries as module


@pytest.mark.parametrize(
    "value",
    [
        [True] * (len(module.FIELDS) - 1),
        [True] * (len(module.FIELDS) + 1),
        [1] * len(module.FIELDS),
        {},
        None,
    ],
)
def test_canary_decoder_rejects_incomplete_or_nonboolean_observations(value):
    with pytest.raises(ValueError):
        module.decode_observations(json.dumps(value).encode())


def test_canary_decoder_preserves_failure_and_checks_every_observation():
    values = [True] * len(module.FIELDS)
    values[2] = False
    result = module.decode_observations(json.dumps(values).encode())
    assert result["evaluator_read_denied"] is False
    assert set(result) == set(module.FIELDS)


def test_unsupported_platform_does_not_create_output(tmp_path, monkeypatch):
    monkeypatch.setattr(module.sys, "platform", "linux")
    output = tmp_path / "probe"
    with pytest.raises(ValueError, match="macOS"):
        module.probe_native_policy(output)
    assert not output.exists()


def test_pinned_recovery_rejects_changed_receipt_without_launch(tmp_path, monkeypatch):
    tmp_path.chmod(0o700)
    (tmp_path / "receipt.json").write_bytes(b"{}")
    monkeypatch.setattr(module, "supervise_process", lambda *a, **k: pytest.fail("relaunch"))
    with pytest.raises(ValueError, match="pinned"):
        module.recover_native_policy_probe(tmp_path, expected_digest="0" * 64)


def test_probe_never_reuses_a_nonempty_output(monkeypatch):
    monkeypatch.setattr(module.sys, "platform", "darwin")
    monkeypatch.setattr(module, "supervise_process", lambda *a, **k: pytest.fail("launch"))
    # Stay within macOS's Unix socket path limit even when pytest's own
    # temporary root is under the longer /private/var/folders hierarchy.
    with TemporaryDirectory(prefix="native-canary-test-", dir="/private/tmp") as temporary:
        output = Path(temporary) / "old"
        output.mkdir(mode=0o700)
        marker = output / "keep"
        marker.write_bytes(b"original")
        with pytest.raises(FileExistsError):
            module.probe_native_policy(output, compiler=Path(__file__))
        assert marker.read_bytes() == b"original"


def test_partial_permission_receipt_cannot_qualify_a_native_host(tmp_path):
    from autoengineering.agents.hosts.native_profile import verify_native_profile

    tmp_path.chmod(0o700)
    raw = json.dumps(
        {"version": module.VERSION, "status": "passed", "host_qualified": False}
    ).encode()
    (tmp_path / "qualification.json").write_bytes(raw)
    with pytest.raises(ValueError, match="incomplete"):
        verify_native_profile(tmp_path, expected_digest=hashlib.sha256(raw).hexdigest())


@pytest.mark.skipif(module.sys.platform != "darwin", reason="macOS synthetic IPC fixture")
def test_synthetic_shared_memory_is_owned_and_removed():
    shared = module._SharedCanary()
    try:
        descriptor = shared.library.shm_open(shared.name.encode(), os.O_RDONLY, ctypes.c_uint(0))
        assert descriptor >= 0
        try:
            assert os.fstat(descriptor).st_mode & 0o777 == 0o600
        finally:
            os.close(descriptor)
        assert not module._SharedCanary.absent(shared.name)
    finally:
        assert shared.close()
    assert module._SharedCanary.absent(shared.name)


@pytest.mark.parametrize(
    "name", ["apple.cfprefs.real", "other", "apple.cfprefs.ae.12345678/", None]
)
def test_recovery_never_opens_unrelated_shared_memory(name):
    with pytest.raises(ValueError, match="synthetic"):
        module._SharedCanary.absent(name)
