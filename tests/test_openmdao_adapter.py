"""Whole-problem lifecycle and optional real OpenMDAO API parity."""
from dataclasses import replace
from types import SimpleNamespace

import numpy as np
import pytest

from autoengineering.adapters.openmdao import (
    OpenMdaoAdapter, SolveDiagnostics, VariableBinding,
)
from autoengineering.adapters.python import run_lifecycle
from test_bmi_adapter import context


def scalar_context():
    ctx = context()
    inputs = tuple(replace(p, dimensions=(), time=None) for p in ctx.model.inputs)
    outputs = tuple(replace(p, dimensions=(), time=None) for p in ctx.model.outputs)
    return replace(ctx, model=replace(ctx.model, inputs=inputs, outputs=outputs))


class Problem:
    def __init__(self):
        self.model = SimpleNamespace(get_io_metadata=self.metadata)
        self.values = {"x": np.zeros(1), "y": np.zeros(1)}
        self.calls = 0
        self.closed = 0
        self.unit = "mm"

    def metadata(self, **kwargs):
        return {name: {"units": self.unit, "shape": (1,)} for name in self.values}

    def setup(self):
        pass

    def final_setup(self):
        pass

    def set_val(self, name, value):
        self.values[name][:] = value
        value[:] = -1

    def get_val(self, name):
        return self.values[name]

    def run_model(self):
        self.calls += 1
        self.values["y"][:] = self.values["x"] * 2

    def run_driver(self):
        raise AssertionError("hidden optimization is forbidden")

    def cleanup(self):
        self.closed += 1
        self.values["y"][:] = -999


def adapter(problem, converged=True):
    return OpenMdaoAdapter(
        lambda ctx: problem,
        inputs={"forcing": VariableBinding("x", "mm")},
        outputs={"flow": VariableBinding("y", "mm")}, parameters={},
        inspector=lambda p: SolveDiagnostics(converged, 0., 1e-10, 1, p.calls, 0),
    )


def test_copies_and_cleanup():
    problem, ctx = Problem(), scalar_context()
    forcing = {"forcing": np.array(3.)}
    result = run_lifecycle(adapter(problem), ctx, forcing, ctx.model.inputs, ctx.model.outputs)
    assert result.outputs["flow"] == 6 and forcing["forcing"] == 3
    assert result.diagnostics["component_calls"] == 1
    assert not result.outputs["flow"].flags.writeable
    assert problem.closed == 1


def test_nonconverged_finite_output_fails():
    problem, ctx = Problem(), scalar_context()
    with pytest.raises(RuntimeError, match="did not converge"):
        run_lifecycle(
            adapter(problem, False), ctx, {"forcing": np.array(3.)},
            ctx.model.inputs, ctx.model.outputs,
        )
    assert problem.closed == 1 and problem.calls == 1


def test_metadata_failure_closes_partial_problem():
    problem = Problem()
    problem.unit = "m"
    with pytest.raises(ValueError, match="units"):
        adapter(problem).prepare(scalar_context())
    assert problem.closed == 1 and problem.calls == 0


def test_diagnostics_are_finite_and_consistent():
    for residual in (float("nan"), float("inf"), -1., 1.):
        with pytest.raises(ValueError):
            SolveDiagnostics(True, residual, 1e-10, 1, 1, 0)


def test_attempt_cannot_run_twice():
    problem, ctx = Problem(), scalar_context()
    wrapped = adapter(problem)
    handle = wrapped.prepare(ctx)
    try:
        wrapped.run(handle, {"forcing": np.array(3.)})
        with pytest.raises(ValueError, match="twice"):
            wrapped.run(handle, {"forcing": np.array(3.)})
    finally:
        wrapped.cleanup(handle)
    assert problem.calls == 1


def test_real_openmdao_scalar_api_parity():
    om = pytest.importorskip("openmdao.api")

    def factory(ctx):
        problem = om.Problem(reports=False)
        problem.model.add_subsystem(
            "scale", om.ExecComp("y=2*x", x={"units": "mm"}, y={"units": "mm"}),
            promotes=["*"],
        )
        return problem

    ctx = scalar_context()
    direct = factory(ctx)
    try:
        direct.setup()
        direct.set_val("x", 3.)
        direct.run_model()
        reference = direct.get_val("y").copy()
    finally:
        direct.cleanup()
    wrapped = OpenMdaoAdapter(
        factory, inputs={"forcing": VariableBinding("x", "mm")},
        outputs={"flow": VariableBinding("y", "mm")}, parameters={},
        inspector=lambda p: SolveDiagnostics(True, 0., 0., 1, p.model.scale.iter_count, 0),
    )
    result = run_lifecycle(
        wrapped, ctx, {"forcing": np.array(3.)}, ctx.model.inputs, ctx.model.outputs,
    )
    np.testing.assert_array_equal(result.outputs["flow"], reference[0])


def test_real_openmdao_driver_scaling_does_not_change_physical_output():
    om = pytest.importorskip("openmdao.api")

    def factory(ctx):
        p = om.Problem(reports=False)
        p.model.add_subsystem("scale", om.ExecComp(
            "y=2*x", x={"units": "mm"}, y={"units": "mm", "ref": 1000.}), promotes=["*"])
        p.model.add_design_var("x", lower=0., upper=10., ref=10.)
        p.model.add_objective("y", ref=1000.)
        return p

    ctx = scalar_context()
    wrapped = OpenMdaoAdapter(
        factory, inputs={"forcing": VariableBinding("x", "mm")},
        outputs={"flow": VariableBinding("y", "mm")}, parameters={},
        inspector=lambda p: SolveDiagnostics(True, 0., 0., 1, p.model.scale.iter_count, 0),
    )
    result = run_lifecycle(wrapped, ctx, {"forcing": np.array(3.)},
                           ctx.model.inputs, ctx.model.outputs)
    assert result.outputs["flow"] == 6.
