"""Range access is conditional, bounded, read-only and consumed after uncertainty."""

from dataclasses import replace
import io

import pytest

from examples.utility.wind_range import WindObjectPin, RangeLimits, WindRangeFile, RangeReadError

ETAG = '"' + "a" * 32 + '-2"'


def source(size=10000, **kw):
    data = bytes(i % 251 for i in range(size))
    calls = []

    def fetch(pin, lo, hi, timeout):
        calls.append((lo, hi, timeout))
        return (
            206,
            {
                "content-range": f"bytes {lo}-{hi}/{size}",
                "content-length": str(hi - lo + 1),
                "etag": ETAG,
            },
            data[lo : hi + 1],
        )

    pin = WindObjectPin("utility-wind-development-object-v1", 2007, size, ETAG)
    return WindRangeFile(pin, RangeLimits(block_bytes=4096), fetch=fetch, **kw), data, calls


def test_seek_cross_block_cache_readinto_and_eof_are_exact():
    reader, data, calls = source()
    assert reader.read(8) == data[:8]
    reader.seek(4090)
    assert reader.read(20) == data[4090:4110]
    assert len(calls) == 2
    reader.seek(0)
    out = bytearray(20)
    assert reader.readinto(out) == 20 and out == data[:20]
    reader.seek(-10, io.SEEK_END)
    assert reader.read(100) == data[-10:]
    assert reader.read(1) == b"" and len(calls) == 3
    assert reader.stats()["cached_blocks"] == 3
    reader.close()
    with pytest.raises(RangeReadError):
        reader.read(1)


@pytest.mark.parametrize("year", [2006, 2012, 2013, 2014, 2025])
def test_reserve_years_and_other_versions_have_no_transport(year):
    with pytest.raises(ValueError):
        WindObjectPin("utility-wind-development-object-v1", year, 100, ETAG)


@pytest.mark.parametrize(
    "kind", ["etag", "full_object", "range", "length", "encoding", "short", "overlong"]
)
def test_unverified_response_poisoned_without_retry(kind):
    reader, _, calls = source()
    original = reader.fetch

    def corrupt(*a):
        status, headers, raw = original(*a)
        if kind == "etag":
            headers["etag"] = '"' + "b" * 32 + '"'
        elif kind == "full_object":
            status = 200
        elif kind == "range":
            headers["content-range"] = "bytes 1-2/3"
        elif kind == "length":
            headers["content-length"] = "2"
        elif kind == "encoding":
            headers["content-encoding"] = "gzip"
        elif kind == "short":
            raw = raw[:-1]
        elif kind == "overlong":
            raw += b"x"
        return status, headers, raw

    reader.fetch = corrupt
    with pytest.raises(RangeReadError):
        reader.read(1)
    before = reader.stats()
    assert before["requests"] == 1 and before["reserved_response_bytes"] == 4097
    with pytest.raises(RangeReadError):
        reader.read(1)
    assert reader.stats() == before and len(calls) == 1


def test_network_failure_retains_reservation_and_cannot_retry():
    reader, _, _ = source()

    def lost(*a):
        raise TimeoutError("response was lost")

    reader.fetch = lost
    with pytest.raises(RangeReadError):
        reader.read(1)
    assert reader.stats()["requests"] == 1 and reader.stats()["received_response_bytes"] == 0
    assert reader.stats()["failed"]
    assert reader.stats()["response_bytes_total"] is None


def test_budget_reservation_precedes_fetch_and_never_renews():
    reader, _, calls = source()
    reader.limits = replace(reader.limits, requests=1)
    reader.read(1)
    reader.seek(5000)
    with pytest.raises(RangeReadError):
        reader.read(1)
    assert len(calls) == 1 and reader.stats()["requests"] == 1
    second, _, calls = source()
    second.limits = replace(second.limits, response_bytes=4096)
    with pytest.raises(RangeReadError):
        second.read(1)
    assert not calls


def test_bulk_read_seek_and_write_refuse_without_network():
    reader, _, calls = source()
    for value in (-1, 2**30, True):
        with pytest.raises(RangeReadError):
            reader.read(value)
    with pytest.raises(RangeReadError):
        reader.seek(-1)
    with pytest.raises(io.UnsupportedOperation):
        reader.write(b"x")
    assert not calls


def test_time_is_checked_even_on_cache_hits():
    now = [0.0]
    reader, _, calls = source(clock=lambda: now[0])
    reader.read(1)
    now[0] = 100
    with pytest.raises(RangeReadError):
        reader.seek(0)
    assert len(calls) == 1 and reader.stats()["failed"]


def test_record_intent_precedes_transport_and_raw_hash_is_bound():
    events = []
    reader, _, calls = source(record=lambda event, raw: events.append((event, raw)))
    original = reader.fetch

    def fetch(*args):
        assert events[-1][0]["status"] == "intended" and events[-1][1] is None
        return original(*args)

    reader.fetch = fetch
    reader.read(1)
    assert events[-1][0]["status"] == "complete" and len(events[-1][1]) == 4096
    stats = reader.stats()
    stats["events"][0]["status"] = "changed"
    assert reader.stats()["events"][0]["status"] == "complete"


def test_optional_h5py_reads_authored_metadata_through_bounded_file_object():
    h5py = pytest.importorskip("h5py")
    buffer = io.BytesIO()
    with h5py.File(buffer, "w") as file:
        item = file.create_dataset("windspeed_80m", shape=(24, 5), dtype="uint16", chunks=(12, 5))
        item.attrs["units"] = "m/s"
        item.attrs["scale_factor"] = 100
    raw = buffer.getvalue()
    calls = []
    pin = WindObjectPin("utility-wind-development-object-v1", 2007, len(raw), ETAG)

    def fetch(pin, lo, hi, timeout):
        calls.append((lo, hi))
        return (
            206,
            {
                "content-range": f"bytes {lo}-{hi}/{len(raw)}",
                "content-length": str(hi - lo + 1),
                "etag": ETAG,
            },
            raw[lo : hi + 1],
        )

    with WindRangeFile(pin, fetch=fetch) as reader:
        with h5py.File(reader, "r") as file:
            item = file["windspeed_80m"]
            assert item.shape == (24, 5) and item.chunks == (12, 5)
            assert item.attrs["units"] == "m/s" and item.attrs["scale_factor"] == 100
        assert reader.stats()["requests"] == len(calls) > 0
        assert not reader.stats()["failed"]
