"""Malformed output cannot become an accepted or recovered private score."""

from __future__ import annotations

import copy
import json

import pytest

from autoengineering.utility import private_container_runtime as module
from test_utility_private_container_runtime import H, saved


def replace_output(folder, raw):
    (folder / "stdout.bin").write_bytes(raw)
    result_path = folder / "result.json"
    result = json.loads(result_path.read_bytes())
    result.update(stdout_sha256=module.sha(raw), result=json.loads(raw))
    result_path.write_text(json.dumps(result))


def test_duplicate_output_key_refuses_even_with_matching_saved_digest(tmp_path):
    runtime, folder, job_sha = saved(tmp_path)
    raw = (folder / "stdout.bin").read_bytes()
    raw = raw.replace(b'"child_exit_code":0', b'"child_exit_code":70,"child_exit_code":0')
    replace_output(folder, raw)
    with pytest.raises(module.Refused):
        runtime.recover(tmp_path, job_sha256=job_sha, labels_sha256=H)


@pytest.mark.parametrize(
    "change",
    [
        lambda v: v.update(child_exit_code=False),
        lambda v: v.update(captured_bytes=True),
        lambda v: v.update(output_limit_bytes=16384.0),
        lambda v: v.update(unexpected="unapproved private text"),
        lambda v: v.update(private_scoring_qualified=True),
        lambda v: v["score"].update(value=True),
        lambda v: v["score"].update(value=-1.0),
        lambda v: v["score"].update(value=float("nan")),
        lambda v: v["score"].update(value=float("inf")),
        lambda v: v["score"].update(feasible=1),
        lambda v: v["score"].update(status="unrecognized"),
        lambda v: v["score"].update(outcome="energy"),
        lambda v: v["score"].update(units=""),
        lambda v: v["score"].update(private_detail="unapproved private text"),
        lambda v: v["score"].update(status="infrastructure_failure"),
    ],
)
def test_malformed_saved_output_refuses_without_api(tmp_path, monkeypatch, change):
    runtime, folder, job_sha = saved(tmp_path)
    output = json.loads((folder / "stdout.bin").read_bytes())
    change(output)
    replace_output(folder, json.dumps(output).encode())
    monkeypatch.setattr(module.API, "request", lambda *_a, **_k: pytest.fail("used daemon"))
    with pytest.raises(module.Refused):
        runtime.recover(tmp_path, job_sha256=job_sha, labels_sha256=H)


@pytest.mark.parametrize("status", ["success", "infrastructure_failure", "insufficient_data"])
def test_fixed_worker_statuses_preserve_failure_semantics(tmp_path, status):
    runtime, folder, job_sha = saved(tmp_path)
    output = json.loads((folder / "stdout.bin").read_bytes())
    score = output["score"]
    score.update(status=status)
    if status != "success":
        score.update(value=None, feasible=None)
    replace_output(folder, module.encode(output))
    assert runtime.recover(tmp_path, job_sha256=job_sha, labels_sha256=H) == score


def test_duplicate_saved_receipt_key_refuses(tmp_path):
    runtime, folder, job_sha = saved(tmp_path)
    path = folder / "cleanup.json"
    raw = path.read_bytes().replace(b'"removed":true', b'"removed":false,"removed":true')
    path.write_bytes(raw)
    with pytest.raises(module.Refused):
        runtime.recover(tmp_path, job_sha256=job_sha, labels_sha256=H)


def test_output_parser_uses_same_validation_for_live_and_saved_output(tmp_path):
    _, folder, _ = saved(tmp_path)
    raw = (folder / "stdout.bin").read_bytes()
    valid = module.validate_output(raw)
    for change in (lambda v: v.update(child_exit_code=False), lambda v: v.update(extra=True)):
        output = copy.deepcopy(valid)
        change(output)
        with pytest.raises(module.Refused):
            module.validate_output(module.encode(output))


@pytest.mark.parametrize(
    "raw",
    [b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":1e9999}', b'{"x":' + b"9" * 400 + b"}", b"{", b"\xff"],
)
def test_invalid_json_never_exposes_raw_private_content(raw):
    with pytest.raises(module.Refused) as error:
        module.decode(raw)
    assert raw.decode(errors="replace") not in str(error.value)


def test_api_inspection_rejects_duplicate_identity_before_use(monkeypatch):
    monkeypatch.setattr(module.API, "request", lambda *_a, **_k: (200, b'{"Id":"one","Id":"two"}'))
    with pytest.raises(module.Refused):
        module.API("/private/tmp/authored.sock").inspect("a" * 64)
