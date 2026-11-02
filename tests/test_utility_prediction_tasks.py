"""Prediction task profiles preserve observed-data semantics and physical vetoes."""
import importlib.util

import numpy as np
import pytest


def test_hydrology_oracle_parity_and_conservation(tmp_path):
    from autoengineering.adapters.python import run_lifecycle
    from examples.local_models.kernels import hydro_model
    from examples.utility.hydrology import BASELINE, adapter, context, development_data, forcing, physical_checks
    data = development_data()
    assert all(data.date < "2020-01-01")
    inputs = forcing(data)
    assert "flow_mm" not in inputs
    for family in ("hamon", "hargreaves"):
        parameters = BASELINE | {"pet": family}
        ctx = context(data, parameters, tmp_path)
        result = run_lifecycle(adapter(), ctx, inputs, ctx.model.inputs, ctx.model.outputs)
        direct = hydro_model(data, parameters)
        for name in ("prediction", "soil", "aet", "pet"):
            np.testing.assert_allclose(result.outputs[name], direct[name], rtol=1e-12, atol=1e-12)
        assert all(c.status == "pass" for c in physical_checks(result.outputs, inputs, parameters))
        broken = dict(result.outputs) | {"prediction": result.outputs["prediction"] + 1}
        assert physical_checks(broken, inputs, parameters)[-1].status == "fail"


def test_unqualified_learned_hydrology_starts_no_training():
    from examples.utility.hydrology import learned_candidate_admission
    assert learned_candidate_admission()["status"] == "unsupported_capability"
    assert learned_candidate_admission()["training_started"] is False


@pytest.mark.skipif(importlib.util.find_spec("pvlib") is None, reason="optional pvlib required")
def test_solar_profile_parity_on_authored_forcing(tmp_path):
    import pandas as pd
    from autoengineering.adapters.python import run_lifecycle
    from examples.interoperability.solar.fixture import BASELINE, forcing
    from examples.interoperability.solar.model import physical
    from examples.open_chains.solar.run_workflow import POA, AIR, WIND
    from examples.utility.solar import adapter, context, physical_checks, primary_loss
    data = pd.DataFrame({POA: [0.] * 6, AIR: [20.] * 6, WIND: [1.] * 6,
                         "score": [False] * 6},
                        index=pd.date_range("2018-06-01", periods=6, freq="5min", tz="UTC"))
    ctx = context(data, BASELINE, tmp_path)
    inputs = forcing(data)
    result = run_lifecycle(adapter(), ctx, inputs, ctx.model.inputs, ctx.model.outputs)
    oracle = physical(inputs, BASELINE)
    np.testing.assert_allclose(result.outputs["prediction"], oracle["prediction"], atol=1e-8)
    assert all(c.status == "pass" for c in physical_checks(result.outputs, inputs, BASELINE))
    assert primary_loss(data, result.outputs)["status"] == "insufficient_data"
