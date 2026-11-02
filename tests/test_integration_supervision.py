"""Local process limits and observed descendant cleanup, without models."""
import json
import sys

import pytest

pytest.importorskip("psutil")

from autoengineering.integrations.supervision import supervise


def call(tmp_path, code, *, timeout=3., memory=256*1024*1024):
    tmp_path.chmod(0o700)
    return supervise((sys.executable, "-c", code), tmp_path, tmp_path,
                     timeout_seconds=timeout, max_rss_bytes=memory, poll_seconds=.01)


def test_success_and_receipt(tmp_path):
    result = call(tmp_path, "print('done')")
    assert result["status"] == "success" and result["stopped"]
    assert json.loads((tmp_path / "supervision.json").read_text()) == result
    assert (tmp_path / "stdout.log").read_text().strip() == "done"


def test_deadline_is_not_a_model_result(tmp_path):
    result = call(tmp_path, "import time;time.sleep(10)", timeout=.2)
    assert result["status"] == "deadline" and result["stopped"]
    assert result["exit_code"] != 0
    assert result["recovery"].startswith("reconcile")


def test_descendant_memory_is_accounted_and_stopped(tmp_path):
    code = """import subprocess,sys,time
p=subprocess.Popen([sys.executable,'-c','import time;x=bytearray(80*1024*1024);time.sleep(10)'])
time.sleep(10)
"""
    result = call(tmp_path, code, memory=40*1024*1024)
    assert result["status"] == "memory_ceiling" and result["stopped"]
    assert result["observed_processes"] >= 2
    assert result["peak_sampled_tree_rss_bytes"] > 40*1024*1024


def test_permission_fallback_still_observes_live_identity(monkeypatch):
    import os
    import psutil
    from autoengineering.integrations.supervision import process_rss

    process = psutil.Process(os.getpid())

    def denied():
        raise psutil.AccessDenied(process.pid)

    monkeypatch.setattr(process, "memory_info", denied)
    assert process_rss(process) > 0


def test_unobservable_live_memory_does_not_become_zero(monkeypatch):
    import os
    import psutil
    from types import SimpleNamespace
    from autoengineering.integrations import supervision

    process = psutil.Process(os.getpid())

    def denied():
        raise psutil.AccessDenied(process.pid)

    monkeypatch.setattr(process, "memory_info", denied)
    monkeypatch.setattr(supervision.subprocess, "run",
                        lambda *a, **k: SimpleNamespace(returncode=1, stdout=""))
    with pytest.raises(psutil.AccessDenied):
        supervision.process_rss(process)
