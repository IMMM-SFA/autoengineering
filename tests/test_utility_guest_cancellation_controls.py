"""Cancellation qualification refuses container starts and repeated mutations."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from examples.utility import guest_cancellation_controls as module


class API:
    def __init__(self):
        self.calls = []

    def _request(self, method, path, value=None, *, deadline, cancelled=None):
        self.calls.append((method, path))
        return 201, b"authored unit response"


def test_start_is_refused_before_transport(tmp_path):
    api = API()
    observer = module.ObservedAPI(api, tmp_path / "api")
    with pytest.raises(RuntimeError, match="START"):
        api._request("POST", "/containers/" + "1" * 64 + "/start", deadline=1)
    assert not api.calls
    assert observer.starts == 1


@pytest.mark.parametrize(
    "method,path",
    [("POST", "/containers/create?name=owned"), ("DELETE", "/containers/" + "1" * 64)],
)
def test_second_mutation_is_refused_and_first_response_is_preserved(tmp_path, method, path):
    api = API()
    observer = module.ObservedAPI(api, tmp_path / "api")
    assert api._request(method, path, deadline=1) == (201, b"authored unit response")
    with pytest.raises(RuntimeError, match="second"):
        api._request(method, path, deadline=1)
    assert api.calls == [(method, path)]
    assert observer.calls == 1
    assert module.fixture.read(tmp_path / "api", "001-response.json")["status"] == 201


def test_cancellation_persists_exact_transition_once(tmp_path, monkeypatch):
    grant = SimpleNamespace(digest="1" * 64)
    owner_root = tmp_path / "work" / grant.digest
    owner_root.mkdir(parents=True)
    (owner_root / "owner.json").write_text("authored sentinel")
    state = SimpleNamespace(phase="created", events=[SimpleNamespace(digest="2" * 64)])
    owner = SimpleNamespace(manifest=SimpleNamespace(digest="3" * 64), replay=lambda: state)
    monkeypatch.setattr(module, "GuestOwnerJournal", lambda *a, **kw: owner)
    cancel = module.Cancellation(
        tmp_path, SimpleNamespace(root=Path("unused")), grant, "start_intent"
    )
    assert not cancel()
    assert not (tmp_path / "cancellation-trigger.json").exists()
    state.phase = "start_intent"
    assert cancel()
    first = (tmp_path / "cancellation-trigger.json").read_bytes()
    state.phase = "started"
    assert cancel()
    assert (tmp_path / "cancellation-trigger.json").read_bytes() == first
    assert module.fixture.read(tmp_path, "cancellation-trigger.json")["event_digest"] == "2" * 64
