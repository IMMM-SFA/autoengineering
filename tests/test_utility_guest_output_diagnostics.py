"""Output diagnostic ownership remains distinct and exact before cleanup."""

from copy import deepcopy

import pytest

from autoengineering.campaign.serialization import digest
from examples.utility import guest_output_diagnostics as module
from test_utility_guest_resources import authored, NONCE, CID


def observed(mode):
    value, _, _ = authored("read_only_root", image_id=module.resources.DERIVATIVE_IMAGE)
    config = module.configuration(mode, NONCE)
    value["HostConfig"] = config.pop("HostConfig")
    value["Config"] = config
    value["Name"] = "/ae-guest-output-" + NONCE
    return value


@pytest.mark.parametrize("mode", module.MODES)
def test_distinct_profile_checks_exact_actual_source_and_preserves_observations(mode):
    value = observed(mode)
    before = deepcopy(value)
    state = module.verify_owned(value, mode, NONCE, CID)
    assert state["Status"] == "exited" and value == before
    assert value["Config"]["Labels"]["org.autoengineering.purpose"] == module.PURPOSE
    assert "-S" in value["Config"]["Entrypoint"]


@pytest.mark.parametrize(
    "change",
    [
        lambda v: v.update(Name="/other-container"),
        lambda v: v["Config"].update(Cmd=["other", NONCE]),
        lambda v: v["Config"]["Labels"].update(
            {"org.autoengineering.purpose": module.resources.PURPOSE}
        ),
        lambda v: v["Config"].update(Entrypoint=["/bin/sh"]),
        lambda v: v["HostConfig"].update(Binds=["/private:/work"]),
        lambda v: v["HostConfig"].update(NetworkMode="host"),
        lambda v: v["HostConfig"].update(Memory=0),
    ],
)
def test_foreign_or_weakened_container_never_receives_cleanup_authority(change):
    value = observed("malformed_stdio")
    change(value)
    with pytest.raises(ValueError):
        module.verify_owned(value, "malformed_stdio", NONCE, CID)


def test_producer_is_fixed_and_has_no_model_or_external_input_selector():
    source = module.worker_source()
    compile(source, "authored-output-worker", "exec")
    assert len(source.encode()) < 65536
    with pytest.raises(ValueError):
        module.configuration("arbitrary-program", NONCE)
    with pytest.raises(ValueError):
        module.configuration("malformed_stdio", "../../unsafe")


def test_consumed_request_refuses_before_runtime_construction(tmp_path, monkeypatch):
    b = {"endpoint": "/unused/socket", "scope": str(tmp_path)}
    q = {
        "schema": "utility-guest-output-diagnostics-v1",
        "sources": module.sources(),
        "reader_sources": module.reader_sources(),
        "bindings_digest": digest(b),
        "limits": module.LIMITS,
        "cases": [{"mode": m, "nonce": str(i) * 32} for i, m in enumerate(module.MODES)],
        "endpoint": {},
    }
    module.fixture.save(tmp_path, "request.json", q)
    module.fixture.save(tmp_path, "bindings.json", b)
    monkeypatch.setattr(module.fixture.build, "_endpoint", lambda x: {})
    monkeypatch.setattr(
        module, "GuestDaemonAPI", lambda *a, **k: pytest.fail("constructed runtime")
    )
    (tmp_path / "execution-intent.json").write_text("{}")
    with pytest.raises(module.StoreError, match="consumed"):
        module.execute(tmp_path, expected_digest=digest(q))
