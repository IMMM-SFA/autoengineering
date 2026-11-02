"""Large contiguous reads retain the original range safety and shared allowance."""

import hashlib
import io

import pytest

from examples.utility.wind_point_range import PointRangeLimits, WindPointRangeFile
from examples.utility.wind_range import WindObjectPin, RangeLimits, RangeReadError

ETAG = '"' + "a" * 32 + '"'


def fixture(data, limits=PointRangeLimits()):
    calls = []

    def fetch(pin, lo, hi, timeout):
        calls.append((lo, hi))
        return (
            206,
            {
                "etag": ETAG,
                "content-range": f"bytes {lo}-{hi}/{len(data)}",
                "content-length": str(hi - lo + 1),
            },
            data[lo : hi + 1],
        )

    pin = WindObjectPin("utility-wind-development-object-v1", 2007, len(data), ETAG)
    return WindPointRangeFile(pin, limits, fetch=fetch), calls


def test_one_direct_request_preserves_exact_offsets_and_global_counters():
    data = bytes(i % 251 for i in range(200000))
    limits = PointRangeLimits(block_bytes=4096, requests=2)
    reader, calls = fixture(data, limits)
    assert reader.read(1) == data[:1]
    reader.seek(5000)
    out = bytearray(100000)
    assert reader.readinto(out) == 100000 and out == data[5000:105000]
    assert calls == [(0, 4095), (5000, 104999)]
    assert reader.stats()["reserved_response_bytes"] == 4097 + 100001
    reader.seek(150000)
    with pytest.raises(RangeReadError):
        reader.read(50000)
    assert len(calls) == 2


def test_corrupt_direct_reply_is_consumed_without_cache_or_retry():
    reader, calls = fixture(b"x" * 100000)
    original = reader.fetch

    def lost(*args):
        status, headers, raw = original(*args)
        headers["etag"] = "wrong"
        return status, headers, raw

    reader.fetch = lost
    with pytest.raises(RangeReadError):
        reader.read(100000)
    assert reader.stats()["response_bytes_total"] is None
    with pytest.raises(RangeReadError):
        reader.read(1)
    assert len(calls) == 1


def test_legacy_and_unbounded_profiles_cannot_be_silently_expanded():
    with pytest.raises(ValueError):
        RangeLimits(max_read_bytes=2 * 1024**2)
    with pytest.raises(ValueError):
        PointRangeLimits(max_read_bytes=5 * 1024**2)
    with pytest.raises(ValueError):
        PointRangeLimits(response_bytes=65 * 1024**2)
    reader, calls = fixture(b"x" * 100000)
    with pytest.raises(RangeReadError):
        reader.read()
    assert not calls


def test_optional_hdf5_extracts_only_one_authored_column_with_direct_reads():
    h5py = pytest.importorskip("h5py")
    np = pytest.importorskip("numpy")
    array = (np.arange(1280 * 128, dtype=np.uint32) % 10000).astype(np.uint16).reshape(1280, 128)
    buffer = io.BytesIO()
    with h5py.File(buffer, "w") as file:
        file.create_dataset("wind", data=array, chunks=(640, 128))
    raw = buffer.getvalue()
    reader, calls = fixture(raw)
    with reader:
        with h5py.File(reader, "r") as file:
            point = file["wind"][:, 17]
        np.testing.assert_array_equal(point, array[:, 17])
        assert any(hi - lo + 1 > 65536 for lo, hi in calls)
        assert any(e.get("profile") == "direct-large-read-v1" for e in reader.stats()["events"])
        assert all(
            e["sha256"] == hashlib.sha256(raw[e["lo"] : e["hi"] + 1]).hexdigest()
            for e in reader.stats()["events"]
        )
