"""A consumed or altered acquisition cannot reopen the source transport."""

import pytest

from autoengineering.campaign.serialization import digest
from examples.utility import wind_point_extract as module
from examples.utility.wind_point_range import PointRangeLimits


def control(root):
    limits = PointRangeLimits()
    return {
        "schema": "utility-wind-point-acquisition-v1",
        "sources": module.sources(),
        "scope_digest": digest(str(root)),
        "phase": "development_only",
        "stage_order": list(module.STAGES),
        "point": {"latitude": 41.5, "longitude": -70.5, "height_m": 80},
        "nearest_policy": "spherical_great_circle_lowest_index_tie",
        "scientific_starts_allowed": 0,
        "automatic_retries": 0,
        "stage_limits": limits.to_dict(),
        "total_request_cap": 3 * limits.requests,
        "total_response_byte_cap": 3 * limits.response_bytes,
        "pin": {
            "schema": "utility-wind-development-object-v1",
            "year": 2007,
            "size_bytes": 10000,
            "etag": '"' + "a" * 32 + '"',
        },
    }


@pytest.mark.parametrize(
    "change",
    [
        {"phase": "confirmation"},
        {"sources": {}},
        {"total_request_cap": 1},
        {"automatic_retries": 1},
        {"scientific_starts_allowed": 1},
    ],
)
def test_bad_profiles_refuse_before_any_stage(tmp_path, monkeypatch, change):
    q = control(tmp_path)
    q.update(change)
    module.save(tmp_path, "request.json", q)
    monkeypatch.setattr(module, "stage_file", lambda *a, **kw: pytest.fail("source stage opened"))
    with pytest.raises(ValueError):
        module.execute(tmp_path, expected_digest=digest(q))
    assert not (tmp_path / "execution-intent.json").exists()


def test_consumed_attempt_never_opens_source_again(tmp_path, monkeypatch):
    q = control(tmp_path)
    module.save(tmp_path, "request.json", q)
    (tmp_path / "execution-intent.json").write_text("{}")
    monkeypatch.setattr(module, "stage_file", lambda *a, **kw: pytest.fail("source stage reopened"))
    with pytest.raises(module.StoreError, match="consumed"):
        module.execute(tmp_path, expected_digest=digest(q))
