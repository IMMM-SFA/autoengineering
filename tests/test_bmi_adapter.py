"""Daily BMI exchange, lifecycle and metadata rejection checks."""
from dataclasses import replace

import numpy as np
import pytest

from autoengineering.adapters.bmi import BmiAdapter
from autoengineering.adapters.contracts import PrepareContext
from autoengineering.campaign.records import ArtifactRef, ModelSnapshot, PortContract, TimeContract


class Model:
    def __init__(self):
        self.time = 0.
        self.value = np.zeros(1)
        self.closed = 0
        self.units = "mm"
        self.step = 1.

    def initialize(self):
        pass

    def get_input_var_names(self):
        return ("forcing",)

    def get_output_var_names(self):
        return ("flow",)

    def get_var_grid(self, name):
        return 0

    def get_grid_type(self, grid):
        return "scalar"

    def get_grid_rank(self, grid):
        return 0

    def get_grid_size(self, grid):
        return 1

    def get_var_type(self, name):
        return "float64"

    def get_var_units(self, name):
        return self.units

    def get_start_time(self):
        return 0.

    def get_current_time(self):
        return self.time

    def get_end_time(self):
        return 3.

    def get_time_step(self):
        return 1.

    def get_time_units(self):
        return "d"

    def set_value(self, name, value):
        self.value[:] = value
        value[:] = -999  # A BMI implementation may retain or mutate exchange storage.

    def update(self):
        self.value *= 2
        self.time += self.step

    def get_value_ptr(self, name):
        return self.value

    def finalize(self):
        self.closed += 1
        self.value[:] = -1


def context():
    time = TimeContract(
        ("2000-01-01", "2000-01-02", "2000-01-03"), "interval_total", "P1D",
        "proleptic_gregorian", "start", (False,) * 3, (True,) * 3,
    )
    port = PortContract("forcing", ("time",), "mm", "float", (), "scalar", "a" * 64, time)
    source = ArtifactRef("model.py", "a" * 64, 1, "text/plain", "test", {})
    snapshot = ModelSnapshot(
        "a" * 64, {"model": "test"}, (source,), "a" * 64,
        (port,), (replace(port, name="flow"),),
    )
    return PrepareContext(snapshot, {}, 0, "scratch", ())


def test_exchange_copies_and_single_attempt():
    model = Model()
    adapter = BmiAdapter(lambda ctx: model, origin="2000-01-01")
    handle = adapter.prepare(context())
    forcing = np.array([1., 2., 3.])
    outputs = adapter.run(handle, {"forcing": forcing})
    adapter.cleanup(handle)
    adapter.cleanup(handle)
    np.testing.assert_array_equal(forcing, [1, 2, 3])
    np.testing.assert_array_equal(outputs["flow"], [2, 4, 6])
    assert not outputs["flow"].flags.writeable
    assert model.closed == 1
    with pytest.raises(ValueError):
        adapter.run(handle, {"forcing": forcing})


@pytest.mark.parametrize("step", [0., 2., float("nan")])
def test_bad_advancement(step):
    model = Model()
    model.step = step
    adapter = BmiAdapter(lambda ctx: model, origin="2000-01-01")
    handle = adapter.prepare(context())
    try:
        with pytest.raises(ValueError, match="advance"):
            adapter.run(handle, {"forcing": np.ones(3)})
    finally:
        adapter.cleanup(handle)
    assert model.closed == 1


def test_bad_metadata_finalizes_before_execution():
    model = Model()
    model.units = "m"
    adapter = BmiAdapter(lambda ctx: model, origin="2000-01-01")
    with pytest.raises(ValueError, match="units"):
        adapter.prepare(context())
    assert model.time == 0 and model.closed == 1


def test_partial_initialization_and_cleanup_failure_keep_primary():
    class Broken(Model):
        def initialize(self):
            raise RuntimeError("primary")

        def finalize(self):
            super().finalize()
            raise RuntimeError("cleanup")

    model = Broken()
    adapter = BmiAdapter(lambda ctx: model, origin="2000-01-01")
    with pytest.raises(RuntimeError, match="primary") as error:
        adapter.prepare(context())
    assert model.closed == 1
    assert "cleanup" in error.value.__notes__[0]


def test_wrong_origin_rejects_before_stepping():
    model = Model()
    adapter = BmiAdapter(lambda ctx: model, origin="2000-01-02")
    with pytest.raises(ValueError, match="origin"):
        adapter.prepare(context())
    assert model.time == 0 and model.closed == 1


@pytest.mark.parametrize("method,value", [
    ("get_grid_type", "uniform_rectilinear"), ("get_grid_rank", 1),
    ("get_grid_size", 2), ("get_var_type", "float32"),
    ("get_input_var_names", ("forcing", "extra")),
    ("get_output_var_names", ()), ("get_time_units", "h"),
    ("get_time_step", 0.5), ("get_end_time", 4.),
])
def test_unsupported_metadata_rejected_before_update(method, value):
    model = Model()
    setattr(model, method, lambda *args: value)
    adapter = BmiAdapter(lambda ctx: model, origin="2000-01-01")
    with pytest.raises(ValueError):
        adapter.prepare(context())
    assert model.time == 0 and model.closed == 1


def test_nonfinite_output_is_rejected():
    model = Model()
    adapter = BmiAdapter(lambda ctx: model, origin="2000-01-01")
    handle = adapter.prepare(context())
    original = model.update

    def update():
        original()
        model.value[:] = np.nan

    model.update = update
    try:
        with pytest.raises(ValueError, match="nonfinite"):
            adapter.run(handle, {"forcing": np.ones(3)})
    finally:
        adapter.cleanup(handle)
    assert model.closed == 1


def test_local_reservoir_direct_driver_parity():
    pytest.importorskip("bmipy")
    from examples.local_models.bmi_chain import run_components
    from examples.local_models.bmi_components import LinearReservoirBmi

    ctx = context()
    time = replace(ctx.model.inputs[0].time,
                   dates=("2000-01-02", "2000-01-03", "2000-01-04"),
                   semantics="interval_mean", timestamp="end")
    port = replace(ctx.model.inputs[0], name="excess_water", units="mm d-1", time=time)
    flow = replace(ctx.model.outputs[0], units="mm d-1", time=time)
    storage = replace(flow, name="reservoir_storage", units="mm",
                      time=replace(time, semantics="instantaneous"))
    ctx = replace(ctx, model=replace(ctx.model, inputs=(port,), outputs=(flow, storage)))
    params = {"recession": 0.7, "end_time": 3}
    forcing = {"excess_water": np.array([1., 0., 3.])}
    direct = run_components(
        {"reservoir": LinearReservoirBmi(params)}, [], {"reservoir": forcing}, 3,
    )["reservoir"]
    adapter = BmiAdapter(lambda ctx: LinearReservoirBmi(params), origin="2000-01-01")
    handle = adapter.prepare(ctx)
    try:
        wrapped = adapter.run(handle, forcing)
    finally:
        adapter.cleanup(handle)
    for name in direct:
        # Identical kernel and update order require exact float64 agreement.
        np.testing.assert_array_equal(wrapped[name], direct[name])


def test_instantaneous_output_is_collected_at_end_not_start():
    ctx = context()
    model = Model()
    invalid = replace(ctx.model.outputs[0], time=replace(ctx.model.outputs[0].time,
                                                        semantics="instantaneous"))
    adapter = BmiAdapter(lambda c: model, origin="2000-01-01")
    with pytest.raises(ValueError, match="outputs require end"):
        adapter.prepare(replace(ctx, model=replace(ctx.model, outputs=(invalid,))))
    assert model.time == 0 and model.closed == 1

    end = replace(ctx.model.inputs[0].time,
                  dates=("2000-01-02", "2000-01-03", "2000-01-04"), timestamp="end")
    input_port = replace(ctx.model.inputs[0], time=end)
    output_port = replace(ctx.model.outputs[0], time=replace(end, semantics="instantaneous"))
    ctx = replace(ctx, model=replace(ctx.model, inputs=(input_port,), outputs=(output_port,)))
    model = Model()
    adapter = BmiAdapter(lambda c: model, origin="2000-01-01")
    handle = adapter.prepare(ctx)
    try:
        values = adapter.run(handle, {"forcing": np.array([1., 2., 3.])})
        np.testing.assert_array_equal(values["flow"], [2., 4., 6.])
    finally:
        adapter.cleanup(handle)
