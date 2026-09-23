"""The benchmark parse cache must preserve fail-closed ledger behavior."""

import hashlib

import pytest

from autoengineering.optimization import (
    EvaluationAction,
    EvaluationResult,
    LedgerCorruptionError,
    ObservationLedger,
)
from examples.complex_models.ledger import BenchmarkLedger


def record(name="a", unit="model_call", **kwargs):
    action = EvaluationAction.system(name, {"x": 0.2})
    result = EvaluationResult.success(name, {"rmse": 1.0}, {}, 1.0, unit, **kwargs)
    return action, result


@pytest.fixture
def ledger(tmp_path):
    value = BenchmarkLedger(tmp_path / "observations.jsonl")
    value.append(*record())
    value.entries()
    return value


def test_cached_and_uncached_records_match(ledger):
    for i in range(4):
        ledger.append(*record(str(i)))
        assert ledger.entries() == ObservationLedger(ledger.path).entries()
    assert ledger._cached_parse.cache_info().hits > 0
    assert ledger._cached_parse.cache_info().maxsize == 16384


def test_same_length_changed_bytes_are_reparsed(ledger):
    data = ledger.path.read_bytes()
    changed = data.replace(b'"rmse":1.0', b'"rmse":2.0')
    assert changed != data and len(changed) == len(data)
    ledger.path.write_bytes(changed)
    assert ledger.entries()[0][1].outcomes["rmse"] == 2.0
    assert ledger.entries() == ObservationLedger(ledger.path).entries()


@pytest.mark.parametrize("change", ["truncate", "duplicate", "unit", "json"])
def test_warm_cache_does_not_hide_corruption(ledger, change):
    data = ledger.path.read_bytes()
    if change == "truncate":
        data = data[:-1]
    elif change == "duplicate":
        data += data
    elif change == "unit":
        data += ledger.record_bytes(*record("b", "seconds"))
    else:
        data = data.replace(b'"rmse":1.0', b'"rmse":xxx')
    ledger.path.write_bytes(data)
    with pytest.raises(LedgerCorruptionError):
        ledger.entries()


@pytest.mark.parametrize("delete", [False, True])
def test_warm_cache_rechecks_artifacts(tmp_path, delete):
    artifact = tmp_path / "artifact.txt"
    artifact.write_bytes(b"original")
    ledger = BenchmarkLedger(tmp_path / "observations.jsonl")
    ledger.append(
        *record(
            artifacts={"a": artifact.name},
            artifact_sha256={"a": hashlib.sha256(artifact.read_bytes()).hexdigest()},
        )
    )
    ledger.entries()
    if delete:
        artifact.unlink()
    else:
        artifact.write_bytes(b"modified")
    with pytest.raises(LedgerCorruptionError, match="artifact"):
        ledger.entries()
