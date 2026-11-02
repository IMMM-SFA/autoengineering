"""Host configuration is frozen before activity and survives acknowledgment loss."""

from dataclasses import replace
from types import SimpleNamespace

import pytest

from autoengineering.agents.command import _bind_host_configuration
from autoengineering.agents.host_configuration import HostConfiguration
from autoengineering.agents.records import HostCapabilities, HostConfigurationBinding, HostSelection
from autoengineering.agents.store import WorkerStore
from autoengineering.campaign.store import StoreError
from test_agent_contracts import run_spec, task_assignment
from test_agent_store import reservation


def fixture(tmp_path):
    spec = replace(run_spec(), host=HostSelection("codex", "subscription", "unit", "2.1", "0" * 64))
    store = WorkerStore.create(tmp_path / "worker", spec, clock=lambda: 0)
    config = HostConfiguration(tmp_path, "0" * 64, tmp_path / "unread-lease", "unit")
    capabilities = HostCapabilities(
        "1.0", "codex", "2.1", "unit", "subscription", True, True, "0" * 64, "unit"
    )
    return store, config, SimpleNamespace(capabilities=lambda: capabilities)


@pytest.mark.parametrize("stage", ["before_event_commit", "after_event_commit"])
def test_binding_commit_fault_can_resume_without_work_or_rebinding(tmp_path, stage):
    store, config, host = fixture(tmp_path)

    def fault(point):
        if point == stage:
            raise RuntimeError("authored acknowledgment loss")

    store.fault = fault
    with pytest.raises(RuntimeError, match="acknowledgment"):
        _bind_host_configuration(store, host, config)
    reopened = WorkerStore(store.root)
    _bind_host_configuration(reopened, host, config)
    binding = reopened.replay().host_configuration
    assert binding.configuration_digest == config.digest
    assert len(reopened.replay().events) == 2
    _bind_host_configuration(reopened, host, config)
    assert len(reopened.replay().events) == 2
    with pytest.raises(ValueError, match="changed"):
        _bind_host_configuration(reopened, host, replace(config, lease_id="changed"))
    assert not reopened.replay().invocations


def test_binding_cannot_be_added_after_existing_activity(tmp_path):
    store, config, host = fixture(tmp_path)
    with store.writer():
        store.commit(task_assignment())
    with pytest.raises(ValueError, match="no original"):
        _bind_host_configuration(store, host, config)
    assert store.replay().host_configuration is None


def test_binding_cannot_be_replaced_and_every_invocation_must_match(tmp_path):
    store, config, host = fixture(tmp_path)
    _bind_host_configuration(store, host, config)
    binding = store.replay().host_configuration
    with store.writer():
        with pytest.raises(StoreError, match="before worker activity"):
            store.commit(binding)
        store.commit(task_assignment())
        # Even the first reservation must use the original capabilities.
        value = reservation(store)
        with pytest.raises(StoreError, match="bound host"):
            store.commit(value)
    assert not store.replay().invocations


def test_binding_rejects_a_foreign_qualification_before_first_activity(tmp_path):
    store, config, host = fixture(tmp_path)
    binding = HostConfigurationBinding(
        "1.0",
        store.spec.id,
        config.digest,
        replace(host.capabilities(), boundary_identity="1" * 64),
    )
    with store.writer(), pytest.raises(StoreError, match="run selection"):
        store.commit(binding)
    assert len(store.replay().events) == 1
