import numpy as np
import pandas as pd
import pytest

from examples.utility.solar_1278_inputs import normalize, evaluate
from examples.utility.consolidated_sources import scope


def frame():
    return pd.DataFrame(
        {
            "measured_on": pd.date_range("2013-01-01", periods=300, freq="15min"),
            "poa_irradiance__3056": 500.0,
            "ambient_temp_f__3058": 68.0,
            "wind_speed_mph__3060": 2.0,
            "ac_power__3081": 50000.0,
        }
    )


def test_solar_units_and_fixed_missingness():
    data = frame()
    data.loc[0, "ambient_temp_f__3058"] = np.nan
    result = normalize(data, "2013-01-01", "2014-01-01")
    assert result["mask"].sum() == 299
    assert result["ambient_c"][1] == 20
    assert result["wind_m_s"][1] == 0.89408
    assert result["labels_kw"][1] == 50
    assert evaluate(result, 0.7)["rows"] == 299


@pytest.mark.parametrize("change", ["date", "order", "too_few"])
def test_solar_rejects_wrong_partition_or_support(change):
    data = frame()
    if change == "date":
        data.loc[0, "measured_on"] = pd.Timestamp("2012-01-01")
    elif change == "order":
        data = data.iloc[::-1]
    else:
        data = data.iloc[:100]
    with pytest.raises(ValueError):
        normalize(data, "2013-01-01", "2014-01-01")


def test_preparation_refuses_consumed_scope(tmp_path):
    root = tmp_path / "staging"
    scope(root, "solar")
    with pytest.raises(FileExistsError):
        scope(root, "solar")
