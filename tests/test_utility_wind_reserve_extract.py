"""Reserve preparation uses a separate pin and does not broaden development access."""

import io
import json

import numpy as np
import pytest

from examples.utility.wind_annual_scoring import _axis
from examples.utility.wind_range import WindObjectPin
from examples.utility.wind_reserve_extract import ReserveObjectPin, extract, reserve_axis


def pin(year=2014):
    return ReserveObjectPin("utility-wind-reserve-object-v1", year, 1000, '"' + "a" * 32 + '"')


def test_reserve_version_and_unchanged_development_restriction():
    assert "/v1.1.0/" in pin().url
    assert "/v1.0.0/" in pin(2012).url
    with pytest.raises(ValueError):
        WindObjectPin("utility-wind-development-object-v1", 2012, 1000, pin().etag)
    with pytest.raises(ValueError):
        pin(2011)


def test_reserve_axis_rejects_missing_hours_and_wrong_clock():
    axis = _axis(2012)
    assert len(reserve_axis(axis, 2012, "UTC")) == 8784
    with pytest.raises(ValueError):
        reserve_axis(axis[:-1], 2012, "UTC")
    with pytest.raises(ValueError):
        reserve_axis(axis, 2012, "local")


@pytest.mark.parametrize("missing", [False, True])
def test_local_hdf_extraction_consumes_scope_and_keeps_payload_private(tmp_path, missing):
    h5py = pytest.importorskip("h5py")
    buffer = io.BytesIO()
    axis = _axis(2014)
    with h5py.File(buffer, "w") as h:
        h.create_dataset("coordinates", data=[[41.5, -70.5], [42.0, -71.0]])
        h.create_dataset(
            "meta",
            data=np.array(
                [(41.5, -70.5), (42.0, -71.0)], dtype=[("latitude", "f8"), ("longitude", "f8")]
            ),
        )
        times = h.create_dataset("time_index", data=np.array(axis, dtype="S20"))
        times.attrs["time_zone"] = "UTC"
        for name, unit, number in [
            ("windspeed_80m", "m s-1", 800),
            ("winddirection_80m", "degree", 18000),
        ]:
            values = np.full((8760, 2), number, dtype="uint16")
            if missing:
                values[0, 0] = 65535
            d = h.create_dataset(name, data=values)
            d.attrs["units"], d.attrs["scale_factor"], d.attrs["fill_value"] = unit, 100, 65535
    raw = buffer.getvalue()

    class Reader(io.BytesIO):
        def stats(self):
            return {"fixture_bytes": len(raw)}

    def factory(*args, **kwargs):
        return Reader(raw)

    root = tmp_path / "private"
    root.mkdir(mode=0o700)
    if missing:
        with pytest.raises(ValueError, match="incomplete"):
            extract(pin(), root, reader_factory=factory)
        assert not (root / "point.npz").exists()
        assert json.loads((root / "failure.json").read_text())["automatic_retry"] is False
    else:
        result = extract(pin(), root, reader_factory=factory)
        assert result["hours"] == 8760
        assert "speed_m_s" not in result and "direction_deg" not in result
        assert (root / "point.npz").stat().st_mode & 0o777 == 0o600
        with np.load(root / "point.npz", allow_pickle=False) as payload:
            assert np.all(payload["speed_m_s"] == 8)
    with pytest.raises(ValueError, match="consumed"):
        extract(pin(), root, reader_factory=factory)
