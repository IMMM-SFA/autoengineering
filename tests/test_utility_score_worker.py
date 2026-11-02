"""Public scoring format/math tests; these do not qualify OS resource isolation."""
import json
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.mark.parametrize("labels,mask,status,value", [
    ([1., 5.], [True, True], "success", 1.),
    ([1., 5.], [False, False], "insufficient_data", None),
    (["PRIVATE-LABEL-CANARY", 5.], [True, True], "infrastructure_failure", None),
])
def test_standalone_score_worker_never_emits_private_diagnostics(tmp_path, labels, mask, status, value):
    from autoengineering.utility import private_score_worker
    source = Path(private_score_worker.__file__)
    (tmp_path / "score.py").write_bytes(source.read_bytes())
    (tmp_path / "job.json").write_text(json.dumps({"prediction": [2., 4.], "outcome": "rmse", "units": "W"}))
    (tmp_path / "labels.json").write_text(json.dumps({"labels": labels, "mask": mask}))
    result = subprocess.run([sys.executable, "-I", "-S", str(tmp_path / "score.py")],
                            text=True, capture_output=True, timeout=5, check=True)
    assert json.loads(result.stdout) == {"status": status, "outcome": "rmse", "units": "W",
                                         "value": value, "feasible": True if value is not None else None}
    assert "PRIVATE-LABEL-CANARY" not in result.stdout + result.stderr
