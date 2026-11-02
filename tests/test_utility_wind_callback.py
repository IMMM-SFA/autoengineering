"""Wind translation preserves typed callback receipts and rejects unsupported options."""

from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from autoengineering.campaign.artifacts import reference
from autoengineering.utility.callback_native import (
    CallbackDriverJob,
    CallbackDriverSpec,
    validate_callback_result,
)
from autoengineering.utility.engineering_process import execution_identity
from examples.utility.wind_callback import execute
from examples.utility.wind_proposal import WindNativeProposal
from test_utility_wind_proposal import result as native_result, specification
from test_utility_wind_process import setup


def test_wind_callback_rejects_changed_caps_before_native_call(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("changed caps invoked native wind")

    monkeypatch.setattr("examples.utility.wind_callback.propose", denied)
    spec = SimpleNamespace(
        options_json=specification().to_json(), callback_limits={"wake": 1, "gradient": 1}
    )
    with pytest.raises(ValueError, match="ceilings"):
        execute(SimpleNamespace(specification=spec))


def test_wind_callback_translates_raw_work_without_solver_diagnostics(tmp_path, monkeypatch):
    driver, _, source = setup(tmp_path)
    relative = "examples/utility/wind_callback.py"
    (source / relative).write_bytes((Path(__file__).resolve().parents[1] / relative).read_bytes())
    execution = driver.spec.execution
    refs = (
        *execution.sources,
        reference(source, relative, media_type="text/plain", producer="authored-fixture"),
    )
    identity = execution_identity(
        execution.entrypoint,
        refs,
        execution.lock,
        execution.scenarios,
        execution.timeout_seconds,
        execution.output_bytes,
        profile="supervised-engineering-v2",
    )
    execution = replace(
        execution, sources=refs, study=replace(execution.study, source_identity=identity)
    )
    native = replace(specification(), maximum_iterations=driver.spec.native.maximum_iterations)
    raw = replace(native_result(), maximum_iterations=native.maximum_iterations)
    proposal = WindNativeProposal("utility-wind-native-proposal-v1", native, raw)
    spec = CallbackDriverSpec(
        "utility-callback-driver-v1",
        execution,
        "examples.utility.wind_callback:execute",
        native.to_json(),
        {"wake": native.maximum_wake_calls, "gradient": native.maximum_gradient_calls},
        6.0,
        32768,
    )
    job = CallbackDriverJob(
        "utility-callback-job-v1", spec, str(source), str(tmp_path / "scratch"), "0" * 64
    )
    monkeypatch.setattr("examples.utility.wind_callback.propose", lambda options: proposal)
    value = execute(job)
    validate_callback_result(spec, job, value)
    assert value.configuration == proposal.configuration
    assert value.final_configuration == proposal.configuration
    assert [(c.kind, c.status) for c in value.calls] == [
        ("wake", "completed"),
        ("gradient", "failed"),
    ]
    assert value.calls[0].outputs == {"annual_energy": 1.0}
    assert value.calls[0].output_units == {"annual_energy": "GWh"}
    assert value.calls[1].outputs == {}
    assert not hasattr(value, "solves")
