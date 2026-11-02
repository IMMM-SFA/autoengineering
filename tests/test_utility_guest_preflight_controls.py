"""Preflight controls cannot silently cross their zero-access boundary."""

from pathlib import Path
import socket
import subprocess
import sys

import pytest

from autoengineering.utility.scoring import CompositeConfirmationGrant
from examples.utility import guest_preflight_controls as module


def test_guard_stops_array_socket_and_process_before_use(tmp_path):
    drivers = tmp_path / "drivers"
    drivers.mkdir()
    path = drivers / "reserved.npz"
    path.write_bytes(b"authored exposed sentinel")
    guard = module.Guard(drivers)
    sys.addaudithook(guard.audit)
    guard.active = True
    try:
        with pytest.raises(RuntimeError, match="driver_or_array_reads"):
            path.read_bytes()
        with pytest.raises(RuntimeError, match="sockets"):
            socket.socket()
        with pytest.raises(RuntimeError, match="processes"):
            subprocess.Popen([sys.executable, "-c", "raise SystemExit(99)"])
        with pytest.raises(RuntimeError, match="daemon"):
            guard.request("GET", "/version")
    finally:
        guard.active = False
    assert all(value == 1 for value in guard.counts.values())
    assert path.read_bytes() == b"authored exposed sentinel"


def test_negative_grants_preserve_original_fit_and_change_only_intended_binding():
    root = Path(__file__).parents[1] / "examples/utility/verification-guest-inference-smoke-v1"
    grant = CompositeConfirmationGrant.from_dict(module.fixture.read(root, "request.json")["grant"])
    original = grant.to_json()
    for case in module.CASES:
        changed = module.altered(grant, case)
        assert changed.inference.selected_state == grant.inference.selected_state
        assert changed.inference.forcing.artifact == grant.inference.forcing.artifact
        if case == "wrong_axis":
            old = grant.inference.forcing.ports[0].time
            new = changed.inference.forcing.ports[0].time
            assert new.dates[0] != old.dates[0]
            assert new.warmup_mask == old.warmup_mask
            assert new.scoring_mask == old.scoring_mask
        elif case == "wrong_fit_seed":
            assert changed.inference.seed == grant.inference.seed + 1
        elif case in ("wrong_source", "cancel_before_access"):
            assert changed == grant
        else:
            assert changed != grant
    assert grant.to_json() == original
    with pytest.raises(ValueError, match="unknown"):
        module.altered(grant, "unbounded")


def test_consumed_control_cannot_retry(tmp_path):
    tmp_path.chmod(0o700)
    q = {
        "scope_digest": module.digest(str(tmp_path)),
        "runner_sha256": module.hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest(),
        "expected_refusals": {k: [c.__name__, m] for k, (c, m) in module.CASES.items()},
        "case_requests": {},
    }
    for case in module.CASES:
        directory = tmp_path / case
        directory.mkdir(mode=0o700)
        module.fixture.save(directory, "request.json", {"case": case})
        q["case_requests"][case] = module.digest({"case": case})
    module.fixture.save(tmp_path, "request.json", q)
    module.fixture.save(tmp_path, "execution-intent.json", {"already_consumed": True})
    with pytest.raises(ValueError, match="consumed"):
        module.execute(tmp_path, expected_digest=module.digest(q))
