"""Lifecycle isolation, exact interfaces, training and causal model state."""

from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from autoengineering.adapters.contracts import (
    AdapterRegistration,
    AdapterRegistry,
    PrepareContext,
    TrainingResult,
    validate_arrays,
)
from autoengineering.adapters.python import PythonAdapter, run_lifecycle
from autoengineering.campaign.acceptance import CheckContext, DEFAULT_CHECKS
from autoengineering.campaign.records import PortContract, TimeContract
from autoengineering.campaign.serialization import digest
from autoengineering.campaign.spec import CheckSpec
from examples.campaign_contracts.build_fixture import ROOT, fixture
from examples.campaign_contracts.hydrology import HydrologyAdapter
from examples.local_models.kernels import hydro_model


def context(model=None, parameters=None):
    spec = fixture()
    return PrepareContext(
        model or spec.baseline.model,
        parameters or spec.baseline.parameters,
        17,
        "scratch",
        ("fitting",),
    )


def test_interface_requires_exact_metadata_and_isolates_caller_arrays():
    contract = fixture().baseline.model.inputs
    source = np.array(2.0)
    result = validate_arrays({"forcing": source}, contract, contract)
    assert not result["forcing"].flags.writeable
    source[...] = 9
    assert result["forcing"] == 2
    wrong = (replace(contract[0], units="m/day"),)
    with pytest.raises(ValueError, match="units"):
        validate_arrays({"forcing": source}, contract, wrong)
    with pytest.raises(ValueError, match="missing"):
        validate_arrays({}, contract, contract)
    with pytest.raises(ValueError, match="dtype"):
        validate_arrays({"forcing": np.array(True)}, contract, contract)
    with pytest.raises(ValueError, match="shape"):
        validate_arrays({"forcing": np.array([2.0])}, contract, contract)


def test_shifted_dates_and_reordered_coordinates_do_not_pass_same_shape():
    time = TimeContract(
        ("2019-01-01", "2019-01-02"),
        "interval_total",
        "P1D",
        "proleptic_gregorian",
        "start",
        (False, False),
        (True, True),
    )
    port = PortContract(
        "p",
        ("time",),
        "mm",
        "float",
        ("north", "south"),
        "grid-v1",
        digest(["north", "south"]),
        time,
    )
    shifted = replace(time, dates=("2019-01-02", "2019-01-03"))
    for other in (replace(port, time=shifted), replace(port, coordinates=("south", "north"))):
        with pytest.raises(ValueError, match="differ"):
            validate_arrays({"p": np.ones(2)}, (port,), (other,))


def test_success_optional_training_and_cleanup(tmp_path):
    ctx = context()
    calls = []

    class Adapter(PythonAdapter):
        def cleanup(self, handle):
            super().cleanup(handle)
            calls.append(handle.closed)

    def train(handle, fitting):
        assert set(fitting) == {"labels"}
        assert handle.context.permitted_data_ids == ("fitting",)
        from autoengineering.campaign.artifacts import reference

        target = tmp_path / "trained.txt"
        target.write_text(str(float(fitting["labels"].mean())))
        artifact = reference(tmp_path, target.name, media_type="text/plain", producer="training")
        return TrainingResult("trained", artifact, 1.0)

    adapter = Adapter(
        lambda forcing, params: {"prediction": forcing["forcing"] * params["multiplier"]},
        lambda params: None,
        trainer=train,
    )
    result = run_lifecycle(
        adapter,
        ctx,
        {"forcing": np.array(2.0)},
        ctx.model.inputs,
        ctx.model.outputs,
        fitting_data={"labels": np.array([3.0, 4.0])},
    )
    assert result.outputs["prediction"] == 2
    assert result.training.status == "trained"
    assert result.training.cost == 1
    assert calls == [True]


@pytest.mark.parametrize("failure", ["prepare", "validate", "run", "inspect", "mutation"])
def test_cleanup_after_every_failure_and_input_mutation(failure):
    calls = []

    class Adapter(PythonAdapter):
        def prepare(self, ctx):
            if failure == "prepare":
                raise ValueError("preparation failed")
            return super().prepare(ctx)

        def validate(self, handle):
            if failure == "validate":
                raise ValueError("validation failed")

        def run(self, handle, inputs):
            if failure == "run":
                raise ValueError("run failed")
            if failure == "mutation":
                inputs["forcing"].setflags(write=True)
                inputs["forcing"][...] = 99
            return {"prediction": np.array(2.0)}

        def inspect(self, handle, outputs):
            if failure == "inspect":
                raise ValueError("inspection failed")
            return {}

        def cleanup(self, handle):
            calls.append(handle)

    ctx = context()
    original = np.array(2.0)
    with pytest.raises(ValueError):
        run_lifecycle(
            Adapter(lambda *_: None, lambda _: None),
            ctx,
            {"forcing": original},
            ctx.model.inputs,
            ctx.model.outputs,
        )
    assert len(calls) == 1
    assert original == 2
    assert (calls[0] is None) == (failure == "prepare")


def test_registry_has_no_worker_import_path_and_requires_dependency_closure():
    spec = fixture()
    registry = AdapterRegistry(
        (AdapterRegistration("linear", "1", lambda: object(), (spec.provenance.sources[0].path,)),)
    )
    registry.validate("linear", spec.baseline.model, ROOT)
    with pytest.raises(ValueError, match="registered"):
        registry.create("untrusted.module:callable")
    bad = AdapterRegistry((AdapterRegistration("linear", "1", lambda: object(), ("missing.py",)),))
    with pytest.raises(ValueError, match="closure"):
        bad.validate("linear", spec.baseline.model, ROOT)


def hydro_context(pet="hamon", capacity=100.0, recession=0.7):
    model = fixture().baseline.model
    # Synthetic arrays test the equations without consuming the real-data run allowance.
    time = TimeContract(
        tuple(pd.date_range("2019-01-01", periods=12).strftime("%Y-%m-%d")),
        "interval_mean",
        "P1D",
        "proleptic_gregorian",
        "start",
        (False,) * 12,
        (True,) * 12,
    )

    def port(name, units):
        return PortContract(name, ("time",), units, "numeric", (), "basin", digest([]), time)

    inputs = tuple(
        port(name, units)
        for name, units in (
            ("precip_mm", "mm/day"),
            ("tmean_c", "degC"),
            ("tmax_c", "degC"),
            ("tmin_c", "degC"),
            ("day_of_year", "day"),
        )
    )
    outputs = tuple(port(name, "mm") for name in ("prediction", "soil", "reservoir", "aet", "pet"))
    outputs += tuple(
        PortContract(name, (), "mm", "float", (), "basin", digest([]), None)
        for name in ("initial_soil", "initial_reservoir")
    )
    model = replace(model, inputs=inputs, outputs=outputs)
    return context(model, {"pet": pet, "capacity": capacity, "recession": recession})


def forcing_data():
    return {
        "precip_mm": np.array([0.0, 80.0, 0.0, 3.0, 0.0, 90.0, 1.0, 0.0, 0.0, 0.0, 20.0, 0.0]),
        "tmean_c": np.full(12, 15.0),
        "tmax_c": np.full(12, 20.0),
        "tmin_c": np.full(12, 10.0),
        "day_of_year": np.arange(1, 13),
    }


@pytest.mark.parametrize("pet", ["hamon", "hargreaves"])
def test_hydrology_direct_parity_balance_and_continuity(pet):
    ctx = hydro_context(pet)
    arrays = forcing_data()
    data = pd.DataFrame({name: value for name, value in arrays.items() if name != "day_of_year"})
    data["date"] = pd.date_range("2019-01-01", periods=12)
    expected = hydro_model(data, dict(ctx.parameters))
    adapter = HydrologyAdapter()
    result = run_lifecycle(adapter, ctx, arrays, ctx.model.inputs, ctx.model.outputs)
    for name in ("prediction", "pet", "soil", "aet"):
        np.testing.assert_allclose(result.outputs[name], expected[name], rtol=0, atol=1e-12)
    check = CheckSpec("daily_balance", "1", True, "whole_model", {})
    record = DEFAULT_CHECKS.evaluate(check, CheckContext(result.outputs, arrays, ctx.parameters))
    assert record.status == "pass"
    handle = adapter.prepare(ctx)
    first = adapter.run(handle, {name: value[:7] for name, value in arrays.items()})
    second = adapter.run(handle, {name: value[7:] for name, value in arrays.items()})
    np.testing.assert_allclose(
        np.r_[first["prediction"], second["prediction"]], expected["prediction"]
    )
    assert second["initial_soil"] == first["soil"][-1]
    fresh = adapter.prepare(ctx)
    assert fresh.soil == ctx.parameters["capacity"] / 2
    assert fresh.reservoir == 0
    adapter.cleanup(handle)
    adapter.cleanup(handle)
    adapter.cleanup(fresh)


def test_missing_temperature_invalid_parameters_and_future_causality():
    arrays = forcing_data()
    ctx = hydro_context()
    with pytest.raises(ValueError, match="missing"):
        run_lifecycle(
            HydrologyAdapter(),
            ctx,
            {k: v for k, v in arrays.items() if k != "tmax_c"},
            ctx.model.inputs,
            ctx.model.outputs,
        )
    for capacity in (False, 0.0, 201.0):
        with pytest.raises(ValueError):
            run_lifecycle(
                HydrologyAdapter(),
                hydro_context(capacity=capacity),
                arrays,
                ctx.model.inputs,
                ctx.model.outputs,
            )
    before = run_lifecycle(HydrologyAdapter(), ctx, arrays, ctx.model.inputs, ctx.model.outputs)
    arrays["precip_mm"][8:] += 100
    after = run_lifecycle(HydrologyAdapter(), ctx, arrays, ctx.model.inputs, ctx.model.outputs)
    np.testing.assert_array_equal(before.outputs["prediction"][:8], after.outputs["prediction"][:8])
