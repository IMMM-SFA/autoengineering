"""Optional native control, using authored drivers and authored selection evidence."""

from importlib.util import find_spec
from importlib.metadata import version
import json
import math
import platform
import time

import pytest

from autoengineering.campaign.artifacts import read_bytes
from autoengineering.campaign.serialization import digest
from autoengineering.campaign.store import StoreError
from examples.utility import wind_annual_callback as callback
from examples.utility import wind_annual_source as source
from test_utility_wind_annual_callback import setup, lose_score_publication


@pytest.mark.skipif(find_spec("py_wake") is None, reason="native annual wind needs optional PyWake")
def test_native_callback_score_commit_loss_and_metadata_only_recovery(tmp_path, monkeypatch):
    cache = tmp_path / "matplotlib-cache"
    cache.mkdir(mode=0o700)
    monkeypatch.setenv("MPLCONFIGDIR", str(cache))
    context = setup(tmp_path, monkeypatch, native=True)
    request = {
        "schema": "utility-wind-annual-native-control-v1",
        "scope": "authored constant drivers and authored selection fixture; not independent data",
        "physical_model_starts_reserved": 3,
        "private_payload_reads_reserved": 3,
        "private_bytes_reserved": 420864,
        "automatic_retries": 0,
        "fault": "confirmation_score_created",
        "leap_year_ratio_relative_tolerance": 1e-12,
        "same_hour_count_absolute_tolerance_gwh": 1e-12,
        "grant": context["grant"].to_dict(),
        "model_artifact": context["model"].to_dict(),
        "source_binding_artifact": context["scorer"].binding_artifact.to_dict(),
        "policy": context["scorer"].policy.to_dict(),
        "geometry": context["scorer"].geometry.to_dict(),
        "expected_model": context["scorer"].expected_model.to_dict(),
    }
    (tmp_path / "native-request.json").write_text(json.dumps(request, indent=2) + "\n")
    began = time.perf_counter()
    lose_score_publication(context)
    execution_interval = time.perf_counter() - began
    assert len(context["calls"]) == len(context["reads"]) == 3
    assert all(call["x"][0] == 10.0 for call in context["calls"])
    artifact = context["scorer"].public_work(context["grant"], context["model"])
    work = callback.AnnualWindWork.from_json(read_bytes(context["store"].root, artifact).decode())
    assert work.attempted_model_starts == work.completed_model_starts == 3
    assert work.score.status == "success" and work.score.value > 0
    values = [item.energy_gwh for item in work.run.results]
    assert values[0] / values[1] == pytest.approx(8784 / 8760, rel=1e-12)
    assert values[1] == pytest.approx(values[2], rel=0, abs=1e-12)
    assert work.score.value == math.fsum(values) / 3
    with pytest.raises(StoreError, match="retry refused"):
        context["service"].confirm(context["grant"])

    def denied(*args, **kwargs):
        pytest.fail("native result recovery attempted a dependency, private source or model")

    monkeypatch.setattr(source, "open_for_confirmation", denied)
    monkeypatch.setattr(callback.kernel, "score_annual", denied)
    monkeypatch.setattr(callback.kernel.wind_hourly, "_backend", denied)
    monkeypatch.setattr(callback, "version", denied)
    began = time.perf_counter()
    receipt = context["service"].recover(context["grant"])
    recovery_interval = time.perf_counter() - began
    assert receipt.score == work.score
    assert receipt.recovery is not None and receipt.measurement is None
    events = len(context["store"].replay()["events"])
    assert context["service"].confirm(context["grant"]) == receipt
    assert context["service"].recover(context["grant"]) == receipt
    assert len(context["store"].replay()["events"]) == events
    assert len(context["calls"]) == len(context["reads"]) == 3
    (tmp_path / "native-receipt.json").write_text(receipt.to_json() + "\n")
    result = {
        "schema": "utility-wind-annual-native-result-v1",
        "status": "passed",
        "request_digest": digest(request),
        "grant_digest": context["grant"].digest,
        "work_artifact": artifact.to_dict(),
        "recovered_receipt_digest": receipt.digest,
        "annual_energy_gwh": values,
        "mean_annual_energy_gwh": work.score.value,
        "physical_model_starts": 3,
        "completed_physical_model_starts": 3,
        "private_payload_reads": 3,
        "verified_private_bytes": 420864,
        "new_model_starts_on_recovery_or_replay": 0,
        "new_source_reads_on_recovery_or_replay": 0,
        "execution_and_fault_interval_seconds": execution_interval,
        "recovery_interval_seconds": recovery_interval,
        "cpu_seconds": None,
        "rss_bytes": None,
        "inner_wake_work": None,
        "recovered_callback_measurement": None,
        "full_cost_evidence": False,
        "private_boundary_qualified": False,
        "task_admitted": False,
        "raw_source_version_comparability": False,
        "source_scope": request["scope"],
        "environment": {
            "python": platform.python_version(),
            "system": platform.system(),
            "machine": platform.machine(),
            "py-wake": version("py-wake"),
            "numpy": version("numpy"),
            "scipy": version("scipy"),
        },
    }
    (tmp_path / "native-result.json").write_text(json.dumps(result, indent=2) + "\n")
