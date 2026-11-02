"""Fixed output capture checks; local fixtures do not qualify a Linux runtime."""

import json
import os
from pathlib import Path
import signal

import pytest

from autoengineering.utility import private_container_worker as worker


@pytest.mark.skipif(os.name != "posix", reason="requires fork and file-size rlimits")
@pytest.mark.parametrize(
    "mode,size,signum,limited",
    [
        ("output-small", 4096, None, False),
        ("output-overrun", 16384, signal.SIGXFSZ, True),
    ],
)
def test_aggregate_regular_file_cap_for_stdout_and_stderr(tmp_path, mode, size, signum, limited):
    result = worker.capture_fixed_worker(tmp_path, mode)
    assert result["captured_bytes"] == size
    assert result["child_signal"] == signum
    assert result["output_limited"] is limited
    assert result["private_scoring_qualified"] is False


@pytest.mark.skipif(os.name != "posix", reason="requires fork and file-size rlimits")
def test_pinned_worker_score_uses_bounded_descriptor_even_under_pytest_capture(tmp_path):
    source = Path(worker.__file__).with_name("private_score_worker.py").read_bytes()
    (tmp_path / "private_score_worker.py").write_bytes(source)
    (tmp_path / "job.json").write_text(
        json.dumps(
            {
                "outcome": "rmse",
                "units": "1",
                "prediction": [0.0, 1.0],
            }
        )
    )
    (tmp_path / "labels.json").write_text(json.dumps({"labels": [1.0, 2.0], "mask": [True, True]}))
    result = worker.capture_fixed_worker(tmp_path, "score")
    assert result["score"]["value"] == 1.0
    assert result["child_exit_code"] == 0
    assert result["output_limited"] is False


def test_modified_worker_refused_before_fork(tmp_path, monkeypatch):
    (tmp_path / "private_score_worker.py").write_text("raise AssertionError('not pinned')")
    monkeypatch.setattr(os, "fork", lambda: pytest.fail("modified worker must not run"))
    with pytest.raises(ValueError, match="hash differs"):
        worker.capture_fixed_worker(tmp_path, "score")


def test_other_mode_cannot_run_arbitrary_code(tmp_path, monkeypatch):
    monkeypatch.setattr(os, "fork", lambda: pytest.fail("unknown mode must not fork"))
    with pytest.raises(ValueError, match="unsupported"):
        worker.capture_fixed_worker(tmp_path, "arbitrary")


def test_cli_refuses_other_platform_before_work(monkeypatch, capsys):
    monkeypatch.setattr(worker.sys, "platform", "unsupported")
    monkeypatch.setattr(worker, "capture_fixed_worker", lambda *_: pytest.fail("must refuse first"))
    assert worker.main(["output-overrun"]) == 2
    assert json.loads(capsys.readouterr().out)["private_scoring_qualified"] is False
