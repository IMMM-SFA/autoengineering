"""Existing batch journals remain authoritative across parent interruptions."""
from dataclasses import replace

import pytest

from autoengineering.campaign.serialization import digest
from autoengineering.campaign.store import StoreError
from autoengineering.utility.controller import CaseBinding, UtilityController
from autoengineering.utility.store import SuiteStore
from test_agent_batch import specification, reservation, observed, finish
from test_utility_contracts import suite


def prepared(tmp_path, fault=None):
    spec = suite()
    store = SuiteStore.create(tmp_path / "suite", spec, fault=fault)
    controller = UtilityController(store)
    original = specification()
    batch_spec = replace(original, cases=tuple(
        replace(case, configuration_digest=spec.routes[0].configuration_digest)
        for case in original.cases))
    bindings = tuple(CaseBinding(c.digest, name) for c, name in zip(
        spec.cells, ("first", "second")))
    child = controller.prepare_batch(batch_spec, bindings)
    identity = child.root.name
    return controller, identity, spec.cells[0].digest, batch_spec, bindings


def run_case(child, case_id):
    assert case_id == "first"
    r = reservation(at=child.clock())
    child.execute(r, lambda _: "authored fixture", lambda r, _: observed(child, r))
    finish(child)


def test_dispatch_and_replay_never_repeat_runner(tmp_path):
    c, identity, cell, spec, bindings = prepared(tmp_path)
    result = c.dispatch(identity, cell, run_case)
    calls = []
    assert c.dispatch(identity, cell, lambda *_: calls.append(1)) == result
    assert calls == []
    resumed = UtilityController(SuiteStore(c.store.root))
    assert resumed.verify_result("child-" + cell[:48]) == result
    before = resumed.store.replay()["used"]
    resumed.prepare_batch(spec, bindings)
    assert resumed.store.replay()["used"] == before


def test_child_commit_before_parent_ack_is_reconciled(tmp_path):
    c, identity, cell, _, _ = prepared(tmp_path)

    def interrupted(child, case_id):
        run_case(child, case_id)
        raise RuntimeError("owner loss after child commit")

    with pytest.raises(RuntimeError):
        c.dispatch(identity, cell, interrupted)
    with pytest.raises(StoreError, match="uncertain"):
        c.dispatch(identity, cell, lambda *_: pytest.fail("must not run"))
    result = c.reconcile(identity, cell)
    assert result["case_result"]["status"] == "passed"
    assert c.reconcile(identity, cell) == result


def test_unknown_child_start_retains_charges(tmp_path):
    c, identity, cell, _, _ = prepared(tmp_path)
    with pytest.raises(RuntimeError):
        c.dispatch(identity, cell, lambda *_: (_ for _ in ()).throw(RuntimeError("crash")))
    before = c.store.replay()["used"]
    with pytest.raises(StoreError, match="fully reconciled"):
        c.reconcile(identity, cell)
    assert c.store.replay()["used"] == before


def test_tampered_child_evidence_rejected_offline(tmp_path):
    c, identity, cell, _, _ = prepared(tmp_path)
    c.dispatch(identity, cell, run_case)
    child, _ = c._child(identity)
    ref = child.replay().finished["first"].evidence[0]
    (child.root / ref.path).write_text("tampered")
    with pytest.raises(ValueError):
        c.verify_result("child-" + cell[:48])


def test_mapping_pin(tmp_path):
    c, identity, _, _, _ = prepared(tmp_path)
    assert len(identity) == 64
    mapping = c.store.root / "children" / f"{identity}.json"
    import json
    document = json.loads(mapping.read_text())
    assert digest(document) == identity
    document["bindings"].reverse()
    mapping.write_text(json.dumps(document))
    with pytest.raises(StoreError, match="identity"):
        c._child(identity)


def test_forty_cells_dispatch_across_real_child_batches(tmp_path):
    from autoengineering.agents.batch import BatchCase
    spec = suite(20)
    budget = spec.budgets[0]
    spec = replace(spec, budgets=(replace(budget, caps=tuple(
        replace(cap, limit=10000) if cap.name == "active_time" else cap
        for cap in budget.caps)),))
    store = SuiteStore.create(tmp_path / "suite", spec)
    controller = UtilityController(store)
    starts = []

    def authored_science(child, case_id):
        r = reservation(id="science-" + case_id, case=case_id, resource="science",
                        at=child.clock())
        child.execute(r, lambda _: starts.append(case_id),
                      lambda r, _: observed(child, r, status="success", size=0,
                                            intent="not_applicable"))
        finish(child, id=case_id)

    for index, cells in enumerate(spec.child_batches()):
        names = [f"case-{index}-{j}" for j in range(len(cells))]
        cases = tuple(BatchCase(name, "comparison", spec.routes[0].configuration_digest, 0, 1)
                      for name in names)
        batch_spec = replace(specification(), id=f"batch-{index}", cases=cases,
                             scientific_starts=len(cases))
        bindings = tuple(CaseBinding(cell.digest, name) for cell, name in zip(cells, names))
        child = controller.prepare_batch(batch_spec, bindings)
        for cell in cells:
            controller.dispatch(child.root.name, cell.digest, authored_science)
    assert len(starts) == 40
    assert store.replay()["used"][("fixed_evaluations", "scientific_starts")] == 40
    resumed = UtilityController(SuiteStore(store.root))
    for cell in spec.cells:
        assert resumed.verify_result("child-" + cell.digest[:48])["case_result"]["status"] == "passed"
    assert len(starts) == 40


@pytest.mark.parametrize("boundary", ["after_child_mapping", "after_parent_reservations",
                                      "after_child_manifest_pin"])
def test_preparation_interruption_replays_allowances(tmp_path, boundary):
    c, _, _, spec, bindings = prepared(tmp_path)
    # Use a fresh suite so each injected point is the first preparation.
    store = SuiteStore.create(tmp_path / "fresh", c.store.spec)

    def fail(stage):
        if stage == boundary:
            raise RuntimeError("preparation interrupted")

    store.fault = fail
    with pytest.raises(RuntimeError):
        UtilityController(store).prepare_batch(spec, bindings)
    resumed = UtilityController(SuiteStore(store.root))
    resumed.prepare_batch(spec, bindings)
    assert len(resumed.store.replay()["attempts"]) == 2
    assert resumed.store.replay()["used"][("fixed_evaluations", "host_invocations")] == 4


def test_unpinned_child_creation_cannot_reset_clock(tmp_path):
    c, _, _, spec, bindings = prepared(tmp_path)
    store = SuiteStore.create(tmp_path / "fresh", c.store.spec)

    def fail(stage):
        if stage == "after_child_creation":
            raise RuntimeError("interrupted")

    store.fault = fail
    with pytest.raises(RuntimeError):
        UtilityController(store).prepare_batch(spec, bindings)
    with pytest.raises(StoreError, match="before manifest pin"):
        UtilityController(SuiteStore(store.root)).prepare_batch(spec, bindings)


def test_offline_accounting_retains_denominator_and_unknowns(tmp_path):
    from autoengineering.utility.report import accounting_report
    c, identity, cell, _, _ = prepared(tmp_path)
    c.dispatch(identity, cell, run_case)
    report = accounting_report(c.store)
    assert report["assigned_cells"] == 2
    assert sorted(report["cells"].values()) == ["finished", "reserved"]
    assert not report["complete_cost_evidence"]
    assert report["physical_receipt_costs"]["unknown"]
    assert report["utility_verdict"] == "not_attempted"
