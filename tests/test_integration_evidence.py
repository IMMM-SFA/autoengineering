"""Evidence readers must remain bounded, pinned and read-only."""
import hashlib

import pytest

from autoengineering.integrations.evidence import archive, reconstruct, verify


def test_archive_verify_readonly_and_corruption(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "result.json").write_text('{"value": 1}')
    target = tmp_path / "archive"
    pin = archive(source, target, ["result.json"], kind="diagnostic",
                  limitations=("synthetic evidence only",))
    before = {str(p.relative_to(target)): p.read_bytes() for p in target.rglob("*") if p.is_file()}
    assert "synthetic evidence only" in reconstruct(target, pin)
    assert {str(p.relative_to(target)): p.read_bytes() for p in target.rglob("*") if p.is_file()} == before
    (target / "result.json").write_text('{"value": 2}')
    with pytest.raises(ValueError, match="digest"):
        verify(target, pin)


def test_missing_and_wrong_index_pin_fail(tmp_path):
    (tmp_path / "result.json").write_text('{}')
    target = tmp_path / "archive"
    pin = archive(tmp_path, target, ["result.json"], kind="diagnostic")
    with pytest.raises(ValueError, match="trusted pin"):
        verify(target, "b" * 64)
    (target / "result.json").unlink()
    with pytest.raises(ValueError, match="regular"):
        verify(target, pin)


def test_symlink_or_traversal_never_enters_archive(tmp_path):
    (tmp_path / "result").write_text('data')
    (tmp_path / "link").symlink_to(tmp_path / "result")
    for path in ("link", "../result"):
        with pytest.raises(ValueError):
            archive(tmp_path, tmp_path / "archive", [path], kind="diagnostic")
    assert not (tmp_path / "archive").exists()


def test_duplicate_index_key_rejected_even_with_matching_pin(tmp_path):
    raw = b'{"schema_version":1,"schema_version":1}'
    (tmp_path / "index.json").write_bytes(raw)
    with pytest.raises(ValueError, match="duplicate"):
        verify(tmp_path, hashlib.sha256(raw).hexdigest())


@pytest.mark.parametrize("failure", [None, "parity", "balance"])
def test_bmi_report_rechecks_arrays_and_balance(tmp_path, failure):
    import json
    import numpy as np

    source = tmp_path / "source"
    source.mkdir()
    protocol = {"forcing": [1., 0.], "dt_days": 1., "conservation_atol_mm": 1e-14,
                "rate_semantics": "interval_mean_end", "storage_semantics": "instantaneous_end"}
    (source / "manifest.json").write_text(json.dumps({"protocol": protocol}))
    flow = np.array([.5, .25])
    storage = np.array([.5, .25])
    direct_flow = flow.copy()
    if failure == "parity":
        direct_flow[0] += .01
    if failure == "balance":
        storage[0] += .1
    np.savez(source / "outputs.npz", flow=flow, reservoir_storage=storage,
             direct_flow=direct_flow, direct_storage=storage)
    target = tmp_path / "archive"
    pin = archive(source, target, ["manifest.json", "outputs.npz"], kind="bmi")
    if failure is None:
        assert "parity: exact" in reconstruct(target, pin)
    else:
        with pytest.raises(ValueError, match="parity|conservation"):
            reconstruct(target, pin)
