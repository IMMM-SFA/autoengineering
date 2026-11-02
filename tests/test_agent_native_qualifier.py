"""Offline qualifier probes and bounded synthetic-secret artifact scanning."""

from pathlib import Path

import pytest

from examples.agent_campaign import qualify_native as qualifier
from examples.agent_campaign.check_brokered_scheduler_fixture import exercise as scheduler_fixture
from autoengineering.agents.hosts.codex_brokered import inspect_brokered_codex
from test_agent_brokered_codex import program


def test_slow_body_reaches_read_deadline_without_dispatch(tmp_path):
    result = qualifier.read_bound(tmp_path / "read")
    assert result["read_deadline_enforced"]
    assert result["upstream_calls"] == 0 and result["dispatch_absent"]
    assert all(
        result["stop"][name]
        for name in ("listener_closed", "handler_stopped", "upstream_callback_stopped")
    )


def test_oversized_schema_is_rejected_before_wrap_launch_or_dispatch(tmp_path):
    inventory = inspect_brokered_codex(program(tmp_path))
    assert qualifier.input_bound(tmp_path / "input", inventory) == {
        "oversized_schema_rejected": True,
        "native_starts": 0,
        "transport_absent": True,
    }


@pytest.mark.parametrize("marker", [None, qualifier.TOKEN, qualifier.REFRESH_TOKEN])
def test_streamed_secret_scan_covers_chunk_boundary_and_large_public_files(tmp_path, marker):
    home = tmp_path / "home"
    home.mkdir()
    raw = b"x" * 65530
    raw += marker.encode() if marker else b"public-only"
    (home / "large.bin").write_bytes(raw + b"x" * 2000000)
    assert qualifier.client_credentials_absent(tmp_path) is (marker is None)


def test_secret_scan_rejects_escaping_symlink(tmp_path):
    (tmp_path / "home").mkdir()
    (tmp_path / "private").write_bytes(b"not for client")
    (tmp_path / "home/escape").symlink_to(tmp_path / "private")
    with pytest.raises(ValueError):
        qualifier.client_credentials_absent(tmp_path)


def test_secret_scan_has_aggregate_bound(tmp_path):
    (tmp_path / "transport").mkdir()
    path = Path(tmp_path / "transport/large")
    with path.open("wb") as stream:
        stream.truncate(16777217)
    with pytest.raises(ValueError, match="bound"):
        qualifier.client_credentials_absent(tmp_path)


@pytest.mark.parametrize("field", ["qualification_root", "qualification_digest"])
def test_scheduler_fixture_requires_profile_root_and_pin_together(tmp_path, field):
    tmp_path.chmod(0o700)
    output = tmp_path / "run"
    with pytest.raises(ValueError, match="together"):
        scheduler_fixture(output, **{field: tmp_path if field.endswith("root") else "0" * 64})
    assert not output.exists()
