"""Coupled engineering parity at frozen current/voltage tolerances."""
import json
from pathlib import Path

import numpy as np
import pytest

from autoengineering.adapters.python import run_lifecycle


@pytest.mark.parametrize("current", [.01, .05, .1])
def test_real_circuit_direct_wrapped_parity(tmp_path, current):
    pytest.importorskip("openmdao")
    from examples.interoperability.circuit.fixture import VARIABLES, adapter, context
    from examples.interoperability.circuit.model import diagnostics, factory

    protocol = json.loads(Path("examples/interoperability/circuit/protocol.json").read_text())
    ctx = context(current, tmp_path)
    direct = factory(ctx)
    try:
        direct.setup()
        direct.final_setup()
        direct.set_val("source.I", current)
        direct.run_model()
        reference = {name: direct.get_val(variable).copy().item()
                     for name, (variable, units) in VARIABLES.items()}
        work = diagnostics(direct)
    finally:
        direct.cleanup()
    wrapped = run_lifecycle(adapter(), ctx, {}, (), ctx.model.outputs)
    for name, (_, units) in VARIABLES.items():
        atol = protocol["voltage_atol_V" if units == "V" else "current_atol_A"]
        np.testing.assert_allclose(wrapped.outputs[name], reference[name],
                                   atol=atol, rtol=protocol["parity_rtol"])
    assert work.converged and work.residual_norm <= protocol["kirchhoff_atol_A"]
    assert work.component_calls > 0 and work.derivative_calls > 0
    assert wrapped.diagnostics["converged"] == 1
    assert wrapped.diagnostics["component_calls"] == work.component_calls
    assert wrapped.diagnostics["derivative_calls"] == work.derivative_calls


def test_current_balance_alone_does_not_prove_convergence():
    from types import SimpleNamespace
    from examples.interoperability.circuit.model import diagnostics

    values = {"source.I": .05, "circuit.R1.I": .04, "circuit.R2.I": .01,
              "circuit.D1.I": .01, "circuit.n1.V": 4., "circuit.n2.V": .6}
    circuit = SimpleNamespace(nonlinear_solver=SimpleNamespace(_iter_count=1),
                              system_iter=lambda **kwargs: [])
    problem = SimpleNamespace(model=SimpleNamespace(circuit=circuit), derivative_calls=0,
                              get_val=lambda name: np.array([values[name]]))
    evidence = diagnostics(problem)
    assert not evidence.converged
    assert evidence.residual_norm > evidence.residual_tolerance


def test_nonfinite_constitutive_residual_cannot_hide_behind_finite_balance():
    from types import SimpleNamespace
    from examples.interoperability.circuit.model import diagnostics

    values = {"source.I": .05, "circuit.R1.I": .04, "circuit.R2.I": .01,
              "circuit.D1.I": .01, "circuit.n1.V": 4., "circuit.n2.V": np.nan}
    problem = SimpleNamespace(get_val=lambda name: np.array([values[name]]))
    with pytest.raises(ValueError, match="all be finite"):
        diagnostics(problem)


def test_invalid_total_derivative_blocks_optimizer_comparison(tmp_path, monkeypatch):
    pytest.importorskip("openmdao")
    pytest.importorskip("optuna")
    from examples.interoperability.circuit import run
    original = run.direct

    def invalid(*args, **kwargs):
        record = original(*args, **kwargs)
        if kwargs.get("derivatives"):
            record["derivative"] = 1e99
        return record

    monkeypatch.setattr(run, "direct", invalid)
    monkeypatch.setattr(run, "OptunaBackend", lambda *a, **k: pytest.fail("search started"))
    with pytest.raises(ValueError, match="derivative mismatch"):
        run.run(tmp_path / "circuit")
    assert (tmp_path / "circuit/derivatives.json").exists()
    assert not (tmp_path / "circuit/study").exists()
