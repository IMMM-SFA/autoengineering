import json
import os
from pathlib import Path
import sys

import numpy as np
import pytest

from examples.utility.consolidated_runtime import SelectionBudget, SelectionSupervisor, solar, wind


def test_supervisor_timeout_stays_charged_and_cannot_retry(tmp_path):
    tmp_path.chmod(0o700)
    worker = SelectionSupervisor(tmp_path, "a" * 64, SelectionBudget(0.2, 2))
    result = worker.run(
        "slow",
        (sys.executable, "-c", "import time; time.sleep(10)"),
        cwd=Path.cwd(),
        environment={"PATH": os.defpath},
        seconds=0.2,
    )
    assert result.status == "timeout"
    assert result.stopped
    with pytest.raises(ValueError, match="redispatched"):
        worker.run("slow", (), cwd=Path.cwd(), environment={}, seconds=0.1)
    resumed = SelectionSupervisor(tmp_path, "a" * 64, SelectionBudget(0.2, 2))
    with pytest.raises(ValueError, match="exhausted"):
        resumed.run("next", (), cwd=Path.cwd(), environment={}, seconds=0.1)
    assert json.loads((tmp_path / "slow-intent.json").read_text())["seconds_reserved"] == 0.2
    with pytest.raises(ValueError, match="cannot change"):
        SelectionSupervisor(tmp_path, "a" * 64, SelectionBudget(1, 2))


def test_supervisor_uncertain_attempt_is_charged(tmp_path, monkeypatch):
    tmp_path.chmod(0o700)
    worker = SelectionSupervisor(tmp_path, "a" * 64, SelectionBudget(1, 2))

    def fail(*args, **kwargs):
        raise RuntimeError("injected owner loss")

    monkeypatch.setattr("examples.utility.consolidated_runtime.supervise_process", fail)
    with pytest.raises(RuntimeError):
        worker.run("lost", (), cwd=Path.cwd(), environment={}, seconds=1, kind="host")
    with pytest.raises(ValueError, match="exhausted"):
        worker.run("next", (), cwd=Path.cwd(), environment={}, seconds=1)


def test_solar_runtime_uses_common_mask_and_parameter_domain():
    data = {
        "mask": np.ones(200, dtype=bool),
        "labels_kw": np.full(200, 50.0),
        "poa": np.full(200, 500.0),
        "ambient_c": np.full(200, 20.0),
        "wind_m_s": np.full(200, 1.0),
    }
    result = solar(data, {"scale": 0.7})
    assert result["model_starts"] == 1 and result["rows"] == 200
    with pytest.raises(ValueError):
        solar(data, {"scale": 2})
    with pytest.raises(ValueError):
        solar(data, {"scale": 0.7, "module": "different"})


def test_wind_selection_does_not_accept_confirmation_years():
    from types import SimpleNamespace

    with pytest.raises(ValueError, match="development years"):
        wind([SimpleNamespace(year=y) for y in (2012, 2013)], {})
