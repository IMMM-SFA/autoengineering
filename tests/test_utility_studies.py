"""Engineering calibration reuses durable optimizer and physical batch evidence."""
from dataclasses import replace

import pytest

from autoengineering.agents.batch import BatchStore
from autoengineering.optimization import (
    OptimizationRunSpec, StudySpec, ObjectiveSpec, BudgetSpec, NoiseSpec, SearchSpace, ContinuousParameter,
)
from autoengineering.campaign.store import StoreError
from autoengineering.campaign.serialization import digest
from autoengineering.utility.studies import EngineeringStudy, EngineeringStudySpec, EngineeringReconciliationRequired
from test_agent_batch import initialized, reservation, observed
from test_utility_outcomes import rules, score
from test_utility_contracts import H


def profile():
    run = OptimizationRunSpec(
        StudySpec("engineering-study", ObjectiveSpec("power", "minimize"), (),
                  BudgetSpec(4, "physical_executions", 2), NoiseSpec(), "system", 17),
        SearchSpace((ContinuousParameter("x", 0., 1.),)), "sobol", {},
        "autoengineering.utility.studies:engineering_evaluator")
    return EngineeringStudySpec(run, rules(), ("scenario-0", "scenario-1"), H)


def setup(tmp_path):
    original = initialized(tmp_path, science=4)
    batch = BatchStore(original.root, expected_digest=original.digest, clock=lambda: 100)
    case = batch.root / "cases/first"
    case.mkdir(mode=0o700, exist_ok=True)
    starts = []

    def perform(action):
        for index in range(2):
            r = reservation(id=f"science-{action.id}-{index}", resource="science", task=None, at=100)
            r = replace(r, invocation_digest=digest({"action": action.to_dict(),
                        "scenario": f"scenario-{index}", "profile": profile().digest}))
            batch.execute(r, lambda _: starts.append(r.id),
                          lambda r, _: observed(batch, r, status="success", size=0,
                                                 intent="not_applicable"))
        value = score(action.id, powers=(10-action.config["x"], 20-action.config["x"]))
        return replace(value, evaluation=replace(value.evaluation, configuration=action.config))

    return batch, starts, perform


def test_study_counts_physical_work_and_resumes_without_new_calls(tmp_path):
    batch, starts, perform = setup(tmp_path)
    bridge = EngineeringStudy(profile(), batch, "first", perform)
    bridge.run(max_new_evaluations=1)
    assert len(starts) == 2
    resumed = EngineeringStudy(profile(), batch, "first", perform)
    resumed.run()
    assert len(starts) == 4
    again = EngineeringStudy(profile(), batch, "first", perform)
    again.run()
    assert len(starts) == 4
    assert len(batch.replay().reservations) == 4


def test_saved_result_reused_after_optimizer_ack_interruption(tmp_path):
    batch, starts, perform = setup(tmp_path)

    def fail(stage):
        if stage == "engineering_result_saved":
            raise RuntimeError("interrupted")

    bridge = EngineeringStudy(profile(), batch, "first", perform, fault=fail)
    with pytest.raises(EngineeringReconciliationRequired):
        bridge.run(max_new_evaluations=1)
    assert len(starts) == 2
    resumed = EngineeringStudy(profile(), batch, "first", perform)
    resumed.run()
    assert len(starts) == 4


def test_missing_physical_profile_cannot_become_success(tmp_path):
    batch, _, _ = setup(tmp_path)
    bridge = EngineeringStudy(profile(), batch, "first", lambda action: score(action.id))
    with pytest.raises(EngineeringReconciliationRequired):
        bridge.run(max_new_evaluations=1)


def test_unsupported_noise_or_insufficient_reserve_reject(tmp_path):
    batch, _, perform = setup(tmp_path)
    p = profile()
    too_large = replace(p, run=replace(p.run, study=replace(p.run.study,
                        budget=BudgetSpec(6, "physical_executions", 3))))
    with pytest.raises(StoreError, match="reserve"):
        EngineeringStudy(too_large, batch, "first", perform)
    assert EngineeringStudySpec.from_json(p.to_json()) == p


def test_uncertain_dispatch_blocks_recovery_without_new_allowance(tmp_path):
    batch, starts, _ = setup(tmp_path)
    bridge = EngineeringStudy(profile(), batch, "first", lambda action: score(action.id))
    with pytest.raises(EngineeringReconciliationRequired):
        bridge.run(max_new_evaluations=1)
    with pytest.raises(EngineeringReconciliationRequired):
        EngineeringStudy(profile(), batch, "first", lambda action: pytest.fail("must not redispatch"))
    assert starts == []


def test_recovery_rejects_modified_saved_cost(tmp_path):
    import json
    batch, starts, perform = setup(tmp_path)

    def fail(stage):
        raise RuntimeError("saved result before acknowledgement")

    bridge = EngineeringStudy(profile(), batch, "first", perform, fault=fail)
    with pytest.raises(EngineeringReconciliationRequired):
        bridge.run(max_new_evaluations=1)
    path = next(bridge.directory.glob("*-result.json"))
    document = json.loads(path.read_text())
    document["result"]["cost"] = 0
    path.write_text(json.dumps(document))
    with pytest.raises(StoreError, match="physical/scientific evidence"):
        EngineeringStudy(profile(), batch, "first", perform)
    assert len(starts) == 2
