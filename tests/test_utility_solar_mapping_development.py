"""Keep equipment calibration out of reserved periods and preserve output limits."""

import numpy as np
import pandas as pd
import pytest

pytest.importorskip("pvlib")

from examples.utility import solar_1278_development as alternative
from examples.utility import solar_mapping_development as original


def test_original_rejects_reserved_dates_before_model_execution(tmp_path):
    filename, columns = original.FILES["electrical"]
    pd.DataFrame({"measured_on": ["2022-01-01"], **{c: [0] for c in columns}}).to_csv(
        tmp_path / filename, index=False
    )
    with pytest.raises(ValueError, match="beyond the fixed cutoff"):
        original.load(tmp_path)


def test_alternative_rejects_dates_outside_development(tmp_path):
    for name in ["1278_development_sample.csv", *[f"1278_day_{d:02d}.csv" for d in range(2, 15)]]:
        pd.DataFrame({"measured_on": ["2013-01-01"]}).to_csv(tmp_path / name, index=False)
    with pytest.raises(ValueError, match="outside development window"):
        alternative.run(tmp_path)


def test_two_inverter_model_has_total_ac_limit_and_zero_at_night():
    poa = np.array([0.0, 1000.0, 5000.0])
    power = alternative.predict(poa, np.full(3, 25.0), np.full(3, 1.0))
    assert np.isfinite(power).all()
    assert power[0] == 0
    assert np.all((power >= 0) & (power <= 150))
