"""Solar parameter constraints reject before optional physics executes."""
import numpy as np
import pytest


def test_invalid_gain_rejected_before_physics(monkeypatch):
    pytest.importorskip("pvlib")
    from examples.interoperability.solar import model
    from examples.interoperability.solar.fixture import BASELINE

    def forbidden(*args, **kwargs):
        raise AssertionError("invalid physical configuration reached pvlib")

    monkeypatch.setattr(model.models, "temperature", forbidden)
    with pytest.raises(ValueError, match="physical parameter"):
        model.physical({}, {**BASELINE, "dc_loss_scale": 1.1})


def test_nighttime_preserves_sandia_standby_behavior():
    pytest.importorskip("pvlib")
    from examples.interoperability.solar.model import physical
    from examples.interoperability.solar.fixture import BASELINE

    forcing = {"poa": np.zeros(6), "ambient": np.full(6, 20.), "wind": np.ones(6),
               "timestamp": np.arange(6, dtype=np.int64) * 300_000_000_000}
    outputs = physical(forcing, BASELINE)
    assert np.isfinite(outputs["prediction"]).all()
    assert (outputs["prediction"] <= 0).all()


def test_datetime_storage_precision_does_not_create_false_gaps(tmp_path):
    pytest.importorskip("pvlib")
    import pandas as pd
    from examples.interoperability.solar.fixture import BASELINE, context

    index = pd.date_range("2018-06-01", periods=6, freq="5min", tz="UTC").as_unit("us")
    data = pd.DataFrame({"score": [False] * 4 + [True] * 2}, index=index)
    ctx = context(data, BASELINE, tmp_path)
    assert ctx.model.outputs[0].time.warmup_mask == (True,) * 4 + (False,) * 2


@pytest.mark.parametrize("change", ["gain", "capacity", "night", "negative_wind"])
def test_scientific_checks_veto_attractive_invalid_power(change):
    from autoengineering.campaign.acceptance import CheckContext, solar_physical

    output = np.array([-.01, 10.])
    forcing = {"poa": np.array([0., 500.]), "wind": np.ones(2)}
    params = {"dc_loss_scale": 1.}
    if change == "gain":
        params["dc_loss_scale"] = 1.1
    elif change == "capacity":
        output[1] = 101.
    elif change == "night":
        output[0] = 1.
    else:
        forcing["wind"][1] = -1.
    status, *_ = solar_physical(CheckContext({"prediction": output}, forcing, params),
                                {"capacity_kw": 100., "standby_floor_kw": -.01})
    assert status == "fail"


def test_gap_restarts_warmup_and_forcing_has_no_labels(tmp_path):
    pytest.importorskip("pvlib")
    import pandas as pd
    from examples.interoperability.solar.fixture import BASELINE, context, forcing
    from examples.open_chains.solar.run_workflow import AIR, POA, WIND

    index = pd.DatetimeIndex(["2018-06-01T00:00Z", "2018-06-01T00:05Z",
                              "2018-06-01T00:20Z", "2018-06-01T00:25Z"])
    data = pd.DataFrame({"score": [False] * 4, POA: [0.] * 4,
                         AIR: [20.] * 4, WIND: [1.] * 4,
                         "comparison_label": [999.] * 4}, index=index)
    ctx = context(data, BASELINE, tmp_path)
    assert ctx.model.outputs[0].time.warmup_mask == (True,) * 4
    assert set(forcing(data)) == {"poa", "ambient", "wind", "timestamp"}


def test_nonfinite_forcing_rejects_before_physics(tmp_path, monkeypatch):
    pytest.importorskip("pvlib")
    import pandas as pd
    from examples.interoperability.solar import model
    from examples.interoperability.solar.fixture import BASELINE, context, forcing
    from examples.open_chains.solar.run_workflow import AIR, POA, WIND

    data = pd.DataFrame({"score": [False] * 5, POA: [np.nan] * 5,
                         AIR: [20.] * 5, WIND: [1.] * 5},
                        index=pd.date_range("2018-06-01", periods=5, freq="5min", tz="UTC"))
    adapter = model.adapter()
    ctx = context(data, BASELINE, tmp_path)
    monkeypatch.setattr(model.models, "temperature", lambda *a, **k: pytest.fail("physics ran"))
    with pytest.raises(ValueError, match="finite"):
        from autoengineering.adapters.python import run_lifecycle
        run_lifecycle(adapter, ctx, forcing(data), ctx.model.inputs, ctx.model.outputs)
