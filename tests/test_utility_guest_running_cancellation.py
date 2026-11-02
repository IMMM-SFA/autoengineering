"""Running cancellation requires the original live boundary and one trigger."""

from types import SimpleNamespace

import pytest

from examples.utility import guest_running_cancellation as module


def setup(tmp_path, monkeypatch, phase="created", running=True):
    grant = SimpleNamespace(digest="1" * 64)
    owner_root = tmp_path / "work" / grant.digest
    owner_root.mkdir(parents=True)
    (owner_root / "owner.json").write_text("authored metadata sentinel")
    state = SimpleNamespace(
        phase=phase,
        observations={"started": {"State": {"Running": running}}},
        events=[SimpleNamespace(digest="2" * 64)],
    )
    owner = SimpleNamespace(manifest=SimpleNamespace(digest="3" * 64), replay=lambda: state)
    monkeypatch.setattr(module, "GuestOwnerJournal", lambda *a, **kw: owner)
    return module.RunningCancellation(tmp_path, SimpleNamespace(root=tmp_path), grant), state


def test_not_started_does_not_signal_cancellation(tmp_path, monkeypatch):
    control, state = setup(tmp_path, monkeypatch)
    assert not control()
    assert not (tmp_path / "cancellation-trigger.json").exists()
    state.phase = "started"
    assert control()
    original = (tmp_path / "cancellation-trigger.json").read_bytes()
    state.phase = "cleaned"
    assert control()
    assert (tmp_path / "cancellation-trigger.json").read_bytes() == original


def test_terminal_fast_worker_cannot_be_called_running_cancellation(tmp_path, monkeypatch):
    control, _ = setup(tmp_path, monkeypatch, phase="started", running=False)
    with pytest.raises(ValueError, match="actually running"):
        control()
    assert not control.triggered
    assert not (tmp_path / "cancellation-trigger.json").exists()


def test_uninitialized_owner_is_not_cancelled(tmp_path):
    control = module.RunningCancellation(
        tmp_path, SimpleNamespace(root=tmp_path), SimpleNamespace(digest="1" * 64)
    )
    assert not control()
