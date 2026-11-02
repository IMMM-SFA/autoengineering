"""Authored HTTP streams only; no public archive acquisition in unit tests."""

from email.message import Message
import io
import shutil
import socket
import subprocess
import time

import pytest

from autoengineering.campaign.serialization import digest
from examples.utility import guest_archive_download as module
import test_utility_guest_image_context as fixture


class Response(io.BytesIO):
    status = 200

    def __init__(self, content):
        super().__init__(content)
        self.headers = Message()
        self.headers["Content-Length"] = str(len(content))


def prepared(tmp_path, monkeypatch):
    plan_root, plan, original = fixture.prepared(tmp_path, monkeypatch)
    cache = tmp_path / "download"
    request = module.prepare_request(plan_root, expected_plan_digest=digest(plan), cache=cache)
    calls = []

    def respond(opener, item, remaining):
        calls.append(item["url"])
        return Response((original / item["path"]).read_bytes())

    monkeypatch.setattr(module, "_open", respond)
    return request, cache, calls


def test_exact_archive_request_downloads_once_and_cold_verifies(tmp_path, monkeypatch):
    request, cache, calls = prepared(tmp_path, monkeypatch)

    def forbidden(*args, **kwargs):
        raise AssertionError("fixture downloader tried execution or a real network connection")

    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(module, "CHUNK", 7)
    result = module.download(request, expected_digest=digest(request), cache=cache)
    assert len(calls) == request["max_file_gets"] == 9
    assert result["received_payload_bytes"] == request["max_payload_bytes"]
    assert not any(result[k] for k in ("installed", "image_built", "runtime_qualified"))
    assert module.verify(cache, expected_digest=digest(result)) == result
    with pytest.raises(ValueError, match="already consumed"):
        module.download(request, expected_digest=digest(request), cache=cache)
    assert len(calls) == 9
    elsewhere = tmp_path / "elsewhere"
    with pytest.raises(ValueError, match="another target"):
        module.download(request, expected_digest=digest(request), cache=elsewhere)
    assert not elsewhere.exists()


@pytest.mark.parametrize(
    "problem",
    [
        "status",
        "size",
        "duplicate_length",
        "chunked",
        "encoded",
        "truncated",
        "hash",
        "lost_response",
    ],
)
def test_failed_response_retains_attempt_and_never_retries(tmp_path, monkeypatch, problem):
    request, cache, calls = prepared(tmp_path, monkeypatch)
    original = module._open

    def respond(opener, item, remaining):
        response = original(opener, item, remaining)
        if problem == "status":
            response.status = 503
        elif problem == "size":
            response.headers.replace_header("Content-Length", str(item["size_bytes"] + 1))
        elif problem == "duplicate_length":
            response.headers["Content-Length"] = str(item["size_bytes"])
        elif problem == "chunked":
            response.headers["Transfer-Encoding"] = "chunked"
        elif problem == "encoded":
            response.headers["Content-Encoding"] = "gzip"
        elif problem == "truncated":
            response = Response(response.getvalue()[:-1])
            response.headers.replace_header("Content-Length", str(item["size_bytes"]))
        elif problem == "hash":
            response = Response(b"X" * item["size_bytes"])
        else:
            raise OSError("authored lost HTTP response")
        return response

    monkeypatch.setattr(module, "_open", respond)
    with pytest.raises((ValueError, OSError)):
        module.download(request, expected_digest=digest(request), cache=cache)
    assert len(calls) == 1 and (cache / "failure.json").exists()
    assert (cache / "requests/0001.json").exists()
    assert not (cache / "complete.json").exists()
    with pytest.raises(ValueError, match="cannot resume or retry"):
        module.download(request, expected_digest=digest(request), cache=cache)
    assert len(calls) == 1


@pytest.mark.parametrize(
    "stage",
    ["archive_intended", "before_archive_get", "archive_saved", "before_archive_completion"],
)
def test_owner_loss_cannot_restart_consumed_download(tmp_path, monkeypatch, stage):
    request, cache, calls = prepared(tmp_path, monkeypatch)

    def fail(point):
        if point == stage:
            raise KeyboardInterrupt("authored owner loss")

    with pytest.raises(KeyboardInterrupt):
        module.download(request, expected_digest=digest(request), cache=cache, fault=fail)
    assert (cache / "control/intent.json").exists()
    assert not (cache / "complete.json").exists()
    count = len(calls)
    with pytest.raises(ValueError, match="already consumed"):
        module.download(request, expected_digest=digest(request), cache=cache)
    assert len(calls) == count


def test_original_deadline_stops_new_gets(tmp_path, monkeypatch):
    request, cache, calls = prepared(tmp_path, monkeypatch)
    clock = [100.0]
    monkeypatch.setattr(module.time, "monotonic", lambda: clock[0])

    def expire(stage):
        if stage == "archive_saved":
            clock[0] += module.SECONDS

    with pytest.raises(TimeoutError):
        module.download(request, expected_digest=digest(request), cache=cache, fault=expire)
    assert len(calls) == 1 and not (cache / "complete.json").exists()


def test_completed_cache_relocates_without_source_clock_or_network(tmp_path, monkeypatch):
    request, cache, calls = prepared(tmp_path, monkeypatch)
    result = module.download(request, expected_digest=digest(request), cache=cache)
    relocated = tmp_path / "relocated"
    shutil.copytree(cache, relocated)
    shutil.rmtree(cache)

    def forbidden(*args, **kwargs):
        raise AssertionError("cold cache reader tried network, execution or clock")

    monkeypatch.setattr(module, "_open", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(time, "time", forbidden)
    monkeypatch.setattr(time, "monotonic", forbidden)
    assert module.verify(relocated, expected_digest=digest(result)) == result
    payload = relocated / request["payloads"][0]["path"]
    payload.write_bytes(b"corrupt")
    with pytest.raises(ValueError):
        module.verify(relocated, expected_digest=digest(result))


@pytest.mark.parametrize(
    "url",
    [
        "http://conda.anaconda.org/conda-forge/linux-64/x.conda",
        "https://example.com/conda-forge/linux-64/x.conda",
        "https://conda.anaconda.org/conda-forge/linux-64/x.conda?token=secret",
        "https://conda.anaconda.org/conda-forge/linux-64/%2e%2e.conda",
    ],
)
def test_unreviewed_origins_and_paths_refuse_before_cache(tmp_path, monkeypatch, url):
    request, cache, calls = prepared(tmp_path, monkeypatch)
    request["image_plan"]["payloads"][0]["url"] = url
    with pytest.raises(ValueError):
        module.download(request, expected_digest=digest(request), cache=cache)
    assert not cache.exists() and not calls


def test_redirect_handler_never_follows_another_origin():
    with pytest.raises(ValueError, match="redirects"):
        module._NoRedirect().redirect_request(
            None, None, 302, "redirect", {}, "https://example.com/"
        )


def test_lost_completion_acknowledgement_replays_original_cache(tmp_path, monkeypatch):
    from autoengineering.campaign.serialization import unique_json

    request, cache, calls = prepared(tmp_path, monkeypatch)

    def fail(stage):
        if stage == "after_archive_completion":
            raise RuntimeError("authored lost completion acknowledgement")

    with pytest.raises(RuntimeError):
        module.download(request, expected_digest=digest(request), cache=cache, fault=fail)
    result = unique_json((cache / "complete.json").read_text())
    assert module.verify(cache, expected_digest=digest(result)) == result
    assert len(calls) == 9 and not (cache / "failure.json").exists()


@pytest.mark.parametrize("extra", ["requests/9999.json", "failure.json", "partial/extra.part"])
def test_completed_cache_cannot_hide_additional_evidence(tmp_path, monkeypatch, extra):
    request, cache, _ = prepared(tmp_path, monkeypatch)
    result = module.download(request, expected_digest=digest(request), cache=cache)
    (cache / extra).write_text("{}")
    with pytest.raises(ValueError, match="unreviewed"):
        module.verify(cache, expected_digest=digest(result))
