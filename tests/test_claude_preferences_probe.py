"""Preference diagnostic input controls. No preference is read or written here."""

import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import probe_claude_preferences as probe


def test_owned_domain_and_observation_roundtrip():
    probe._validate_domain(probe.PREFIX + "a" * 32, "b" * 32)
    record = {"present": 0, "visible": 0, "synchronized": -1}
    assert probe._decode(json.dumps(record).encode()) == record


@pytest.mark.parametrize(
    "domain,marker",
    [
        ("com.apple.finder", "b" * 32),
        (probe.PREFIX + "a" * 31, "b" * 32),
        (probe.PREFIX + "z" * 32, "b" * 32),
        (probe.PREFIX + "a" * 32, "bad"),
        (probe.PREFIX + "a" * 32 + "/escape", "b" * 32),
    ],
)
def test_existing_domains_or_unbounded_values_are_refused(domain, marker):
    with pytest.raises(ValueError, match="owned random"):
        probe._validate_domain(domain, marker)


@pytest.mark.parametrize(
    "value",
    [
        {"present": True, "visible": 0, "synchronized": -1},
        {"present": 0, "visible": 1, "synchronized": -1},
        {"present": 0, "visible": 0, "synchronized": True},
        {"present": 0, "visible": 0, "synchronized": 9},
        {"present": 0, "visible": 0, "synchronized": -1, "extra": 1},
    ],
)
def test_invalid_observations_cannot_be_passed_as_controls(value):
    with pytest.raises(ValueError):
        probe._decode(json.dumps(value).encode())


def test_unsupported_platform_refuses_before_output_or_process(tmp_path, monkeypatch):
    monkeypatch.setattr(probe.sys, "platform", "linux")
    monkeypatch.setattr(probe.subprocess, "run", lambda *_a, **_k: pytest.fail("process launched"))
    output = tmp_path / "new"
    with pytest.raises(ValueError, match="macOS ARM64"):
        probe.probe(output)
    assert not output.exists()


@pytest.mark.parametrize("symlink", [False, True])
def test_existing_or_symlink_output_refuses_before_process(tmp_path, monkeypatch, symlink):
    monkeypatch.setattr(probe.sys, "platform", "darwin")
    monkeypatch.setattr(probe.platform, "machine", lambda: "arm64")
    monkeypatch.setattr(probe.subprocess, "run", lambda *_a, **_k: pytest.fail("process launched"))
    target = tmp_path / "existing"
    target.mkdir()
    output = tmp_path / "linked" if symlink else target
    if symlink:
        output.symlink_to(target, target_is_directory=True)
    with pytest.raises(ValueError, match="fresh nonsymlink"):
        probe.probe(output)
    assert list(target.iterdir()) == []


def test_cleanup_removes_only_empty_owned_domain(tmp_path):
    import plistlib

    domain = probe.PREFIX + "a" * 32
    path = tmp_path / (domain + ".plist")
    path.write_bytes(plistlib.dumps({}))
    assert probe._remove_empty_domain(tmp_path, domain)
    assert not path.exists()
    assert probe._remove_empty_domain(tmp_path, domain) is False


@pytest.mark.parametrize("problem", ["nonempty", "large", "symlink", "hardlink", "fifo"])
def test_cleanup_refuses_changed_or_nonregular_storage(tmp_path, problem):
    import os
    import plistlib

    domain = probe.PREFIX + "a" * 32
    path = tmp_path / (domain + ".plist")
    if problem == "symlink":
        other = tmp_path / "other.plist"
        other.write_bytes(plistlib.dumps({}))
        path.symlink_to(other)
    elif problem == "fifo":
        os.mkfifo(path, 0o600)
    else:
        path.write_bytes(
            plistlib.dumps({"unexpected": "preserve"})
            if problem == "nonempty"
            else b"x" * 4097
            if problem == "large"
            else plistlib.dumps({})
        )
        if problem == "hardlink":
            os.link(path, tmp_path / "other.plist")
    with pytest.raises((ValueError, OSError)):
        probe._remove_empty_domain(tmp_path, domain)
    assert path.exists()


def test_flush_wait_accepts_only_transient_owned_canary(tmp_path, monkeypatch):
    seen = []

    def transient(*_args, **_kwargs):
        seen.append(1)
        if len(seen) == 1:
            raise probe.PendingPreferenceFlush("owned")
        return True

    monkeypatch.setattr(probe, "_remove_empty_domain", transient)
    monkeypatch.setattr(probe.time, "sleep", lambda _: None)
    result = probe._wait_remove_empty_domain(tmp_path, probe.PREFIX + "a" * 32, "b" * 32)
    assert result["removed"] and result["deferred_flush_observations"] == 1


def test_flush_wait_times_out_without_deleting_canary(tmp_path):
    import plistlib

    domain, marker = probe.PREFIX + "a" * 32, "b" * 32
    path = tmp_path / (domain + ".plist")
    raw = plistlib.dumps({"AEQualificationCanary": marker})
    path.write_bytes(raw)
    with pytest.raises(ValueError, match="did not flush"):
        probe._wait_remove_empty_domain(tmp_path, domain, marker, timeout_seconds=0)
    assert path.read_bytes() == raw


def test_flush_wait_never_removes_unexpected_preference_value(tmp_path):
    import plistlib

    domain = probe.PREFIX + "a" * 32
    path = tmp_path / (domain + ".plist")
    raw = plistlib.dumps({"unrelated": "preserve"})
    path.write_bytes(raw)
    with pytest.raises(ValueError, match="not empty"):
        probe._wait_remove_empty_domain(tmp_path, domain, "b" * 32)
    assert path.read_bytes() == raw


def test_cleanup_reconciliation_refuses_wrong_scope_before_any_cleanup(tmp_path, monkeypatch):
    domain = probe.PREFIX + "a" * 32
    (tmp_path / "scope.json").write_text(json.dumps({"domain": domain, "marker": "b" * 32}))
    monkeypatch.setattr(
        probe, "_wait_remove_empty_domain", lambda *_a, **_k: pytest.fail("cleanup attempted")
    )
    with pytest.raises(ValueError, match="scope differs"):
        probe.reconcile_cleanup(tmp_path, expected_scope_sha256="0" * 64)
