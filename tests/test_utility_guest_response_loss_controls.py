"""Acknowledgment loss is injected only after one real transport success."""

import json

import pytest

from examples.utility import guest_response_loss_controls as module


class API:
    def __init__(self, status):
        self.calls = []
        self.status = status

    def _request(self, method, path, value=None, *, deadline, cancelled=None):
        self.calls.append((method, path))
        return self.status, json.dumps(
            {"Id": "1" * 64, "Warnings": []}
        ).encode() if self.status == 201 else b""


@pytest.mark.parametrize(
    "case,status,path",
    [
        ("lost_create_response", 201, "/containers/create?name=owned"),
        ("lost_start_response", 204, "/containers/" + "1" * 64 + "/start"),
    ],
)
def test_success_is_saved_and_withheld_once_with_retry_blocked(tmp_path, case, status, path):
    api = API(status)
    wrapper = module.ObservedAPI(api, tmp_path / "api", case)
    with pytest.raises(module.ResponseLost, match=case):
        api._request("POST", path, deadline=1)
    record = module.fixture.read(tmp_path / "api", "withheld-response.json")
    raw = module.fixture.raw(tmp_path / "api", "withheld-response-body.bin")
    assert record["status"] == status
    assert record["body_sha256"] == module.hashlib.sha256(raw).hexdigest()
    with pytest.raises(RuntimeError, match="repeated"):
        api._request("POST", path, deadline=1)
    assert api.calls == [("POST", path)]
    assert wrapper.dropped


def test_failed_daemon_response_cannot_be_called_successful_loss(tmp_path):
    api = API(500)
    wrapper = module.ObservedAPI(api, tmp_path / "api", "lost_create_response")
    with pytest.raises(ValueError, match="expected first success"):
        api._request("POST", "/containers/create?name=owned", deadline=1)
    assert not wrapper.dropped
    assert not (tmp_path / "api/withheld-response.json").exists()


def test_create_loss_case_refuses_start_before_transport(tmp_path):
    api = API(204)
    wrapper = module.ObservedAPI(api, tmp_path / "api", "lost_create_response")
    with pytest.raises(RuntimeError, match="START"):
        api._request("POST", "/containers/" + "1" * 64 + "/start", deadline=1)
    assert api.calls == []
    assert wrapper.starts == 1
