"""Owner-loss qualification cannot create/start twice or accept changed child code."""

import hashlib
from pathlib import Path

import pytest

from examples.utility import guest_owner_loss_controls as module


class API:
    def __init__(self):
        self.calls = []

    def _request(self, method, path, value=None, *, deadline, cancelled=None):
        self.calls.append((method, path))
        return 204, b""


@pytest.mark.parametrize(
    "method,path",
    [
        ("POST", "/containers/create?name=owned"),
        ("POST", "/containers/" + "1" * 64 + "/start"),
        ("DELETE", "/containers/" + "1" * 64),
    ],
)
def test_owned_operation_cannot_be_sent_twice(tmp_path, method, path):
    api = API()
    journal = module.APIJournal(api, tmp_path / "api", starts_allowed=1, create_allowed=1)
    assert api._request(method, path, deadline=1) == (204, b"")
    with pytest.raises(RuntimeError, match="repeated"):
        api._request(method, path, deadline=1)
    assert api.calls == [(method, path)]
    assert journal.calls == 1


def test_parent_cleanup_has_no_create_or_start_authority(tmp_path):
    api = API()
    module.APIJournal(api, tmp_path / "api", starts_allowed=0, create_allowed=0)
    for path in ("/containers/create?name=owned", "/containers/" + "1" * 64 + "/start"):
        with pytest.raises(RuntimeError, match="unallowed"):
            api._request("POST", path, deadline=1)
    assert api.calls == []


def test_changed_child_controller_or_nonce_refuses_before_context(tmp_path, monkeypatch):
    tmp_path.chmod(0o700)
    expected = hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest()

    def forbidden(*args, **kwargs):
        pytest.fail("changed child entered execution context")

    monkeypatch.setattr(module, "context", forbidden)
    with pytest.raises(ValueError, match="controller"):
        module.child(
            tmp_path, case="owner_loss_running", nonce="a" * 32, controller_sha256="0" * 64
        )
    module.fixture.save(
        tmp_path,
        "child-intent.json",
        {
            "case": "owner_loss_running",
            "nonce": "b" * 32,
            "controller_sha256": expected,
        },
    )
    with pytest.raises(ValueError, match="original intent"):
        module.child(
            tmp_path, case="owner_loss_running", nonce="a" * 32, controller_sha256=expected
        )
