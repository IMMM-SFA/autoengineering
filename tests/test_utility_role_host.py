"""Durable role caps refuse dispatch before the physical host boundary."""
from dataclasses import replace

import pytest

from autoengineering.agents.batch import BatchCase
from autoengineering.agents.hosts.base import HostResult
from autoengineering.agents.hosts.fake import FakeHost
from autoengineering.campaign.store import StoreError
from autoengineering.utility.controller import UtilityController, CaseBinding
from autoengineering.utility.role_host import RoleBoundHost
from autoengineering.utility.routes import RoutePlan, TaskRoute, role_removals
from autoengineering.utility.store import SuiteStore
from test_agent_batch import specification
from test_agent_contracts import task_assignment
from test_utility_contracts import suite, H
from test_utility_routes import full


def setup(tmp_path, *, omitted=None):
    recipe = full()
    recipe = replace(recipe, host=replace(recipe.host, model="scripted", version="scripted-1.0"))
    if omitted:
        recipe = next(r for r in role_removals(recipe, {r: H for r in (
            "investigator", "implementer", "reviewer")}) if r.kind == "no_" + omitted)
    conventional = replace(recipe, kind="conventional", roles=(), host=None, replacements={})
    plan = RoutePlan("utility-routes-v1", (
        TaskRoute("task", "conventional", conventional), TaskRoute("task", "multi", recipe)),
        1, 17, {"task": H})
    original = suite()
    routes, cells = plan.expand(original.tasks, original.budgets)
    spec = replace(original, routes=routes, cells=cells)
    store = SuiteStore.create(tmp_path / "suite", spec)
    route = next(r for r in routes if r.route_id == "multi")
    cell = next(c for c in cells if c.route_id == "multi")
    child_spec = specification()
    child_spec = replace(child_spec, host_configuration_digest=H,
        cases=(BatchCase("agent", "roles", route.configuration_digest, 20, 0),),
        limits=replace(child_spec.limits, max_invocations=20))
    child = UtilityController(store).prepare_batch(child_spec, (CaseBinding(cell.digest, "agent"),))
    child.start_case("agent", route.configuration_digest)
    allocation, _ = store.replay()["attempts"]["child-" + cell.digest[:48]]
    with store.writer():
        store.append(request_id="start", operation="start", cell_digest=cell.digest,
                     attempt_id=allocation.attempt_id, child_digest=allocation.child_digest)
    host = FakeHost([HostResult("completed", "fixture-output", None, {}, 0.) for _ in range(10)])
    wrapper = RoleBoundHost(store, child, cell.digest, plan, host,
                            templates={r.role: r.prompt_digest for r in recipe.roles})
    return store, child, plan, cell, recipe, host, wrapper


def invoke(wrapper, invocation_id, task=None):
    return wrapper.invoke(task or task_assignment(), "PRIVATE-PROMPT-CANARY",
                          invocation_id=invocation_id, timeout_seconds=1., max_output_bytes=1000)


def test_role_cap_survives_restart_and_never_redispatches_identity(tmp_path):
    store, child, plan, cell, recipe, host, wrapper = setup(tmp_path)
    for index in range(4):
        invoke(wrapper, f"call-{index}")
    assert len(host.calls) == 4
    with pytest.raises(StoreError, match="allowance"):
        invoke(wrapper, "call-over-budget")
    with pytest.raises(StoreError, match="already reserved"):
        invoke(wrapper, "call-0")
    resumed = RoleBoundHost(SuiteStore(store.root), child, cell.digest, plan, host,
                            templates={r.role: r.prompt_digest for r in recipe.roles})
    with pytest.raises(StoreError, match="allowance"):
        invoke(resumed, "after-resume")
    assert len(host.calls) == 4
    assert store.replay()["role_counts"][(cell.digest, "investigator")] == 4
    for path in (store.root / "events").glob("*.json"):
        assert "PRIVATE-PROMPT-CANARY" not in path.read_text()


def test_omitted_role_refuses_before_host_without_reallocation(tmp_path):
    store, _, _, _, recipe, host, wrapper = setup(tmp_path, omitted="investigator")
    with pytest.raises(StoreError, match="omitted"):
        invoke(wrapper, "omitted-role")
    assert host.calls == []
    assert store.replay()["role_counts"] == {}
    assert recipe.unused_role_allowance == 8


def test_delegate_failure_retains_role_charge(tmp_path):
    store, _, _, cell, _, _, wrapper = setup(tmp_path)
    wrapper.delegate = FakeHost([RuntimeError("host interrupted")])
    with pytest.raises(RuntimeError):
        invoke(wrapper, "interrupted")
    assert store.replay()["role_counts"][(cell.digest, "investigator")] == 1
    with pytest.raises(StoreError, match="already reserved"):
        invoke(wrapper, "interrupted")


def test_batch_scoped_host_version_does_not_change_frozen_profile(tmp_path):
    store, child, plan, cell, recipe, host, _ = setup(tmp_path)

    class ScopedHost(FakeHost):
        def capabilities(self):
            return replace(super().capabilities(), executable_version=
                f"scripted-1.0:batch:{child.digest}:agent")

    wrapped = RoleBoundHost(store, child, cell.digest, plan, ScopedHost([]),
                            templates={r.role: r.prompt_digest for r in recipe.roles})
    assert wrapped.capabilities().executable_version.endswith(":agent")
    with pytest.raises(StoreError, match="templates"):
        RoleBoundHost(store, child, cell.digest, plan, host, templates={})
