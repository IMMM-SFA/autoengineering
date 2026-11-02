"""A frozen baseline group authorizes one source score and no follower starts."""

from dataclasses import replace

import pytest

from autoengineering.campaign.serialization import digest
from autoengineering.utility.analysis import analyze_confirmation
from autoengineering.utility.costs import join_confirmation_costs
from autoengineering.utility.scoring import ConfirmationGrant, ConfirmationService, PublicScore
from autoengineering.utility.contracts import ResourceCap
from test_utility_analysis import fixture
from test_utility_confirmation import selected_suite
from test_utility_contracts import H, suite


def baseline_suite(tmp_path, *, result=None, configuration_digest=None):
    from autoengineering.utility.contracts import BaselineReuseGroup, BaselineReusePolicy

    def freeze_policy(spec):
        group = BaselineReuseGroup(
            tuple(c.digest for c in spec.cells),
            spec.cells[0].digest,
            spec.tasks[0].candidate_digests[0],
            configuration_digest or digest({}),
            H,
            (0.25, 0.75),
        )
        policy = BaselineReusePolicy("utility-baseline-reuse-v1", spec.protocol_digest, (group,))
        return replace(
            spec, schema="utility-suite-v2", protocol_digest=policy.digest, baseline_reuse=policy
        )

    plan = fixture((2.0,))[1]
    store, manifest, contract = selected_suite(
        tmp_path,
        analysis_plan=plan,
        all_selected=True,
        baseline_routes=True,
        suite_transform=freeze_policy,
    )
    calls = []

    def scorer(*_):
        calls.append(1)
        return result or PublicScore("success", "power", "W", 3.0, True)

    grants = tuple(
        ConfirmationGrant(
            store.spec.digest,
            c.cell_digest,
            store.spec.tasks[0].partition_digest,
            H,
            contract.digest,
            c.model.sha256,
            store.replay()["frozen"],
            (ResourceCap("scientific_starts", "count", 1, "reservation"),),
        )
        for c in manifest.cells
    )
    service = ConfirmationService(store, scorer, scorer_digest=H, outcome_contract=contract)
    return store, plan, grants, service, calls


def test_source_executes_once_followers_share_without_new_charges(tmp_path):
    store, plan, grants, service, calls = baseline_suite(tmp_path)
    receipt = service.confirm(grants[0])
    before = store.replay()
    report = analyze_confirmation(store, plan)
    assert report["scored_cells"] == 2 and report["physical_score_receipts"] == 1
    assert service.confirm(grants[0]) == receipt and calls == [1]
    assert store.replay()["head"] == before["head"]
    costs = join_confirmation_costs(store)
    row = next(c for c in costs if c.resource == "confirmation_reservations")
    assert row.quantity == 1 and row.cell_digests == tuple(c.digest for c in store.spec.cells)
    assert row.allocation == (0.25, 0.75)
    assert len(store.replay()["confirmation_accesses"]) == 1


def test_follower_dispatch_and_direct_reservation_are_both_forbidden(tmp_path):
    store, _, grants, service, calls = baseline_suite(tmp_path)
    target = grants[1]
    before = store.replay()["head"]
    with pytest.raises(ValueError):
        service.confirm(target)
    with store.writer(), pytest.raises(ValueError):
        store.append(
            request_id="bypass-cache",
            operation="reserve",
            cell_digest=target.cell_digest,
            attempt_id="confirmation-" + target.cell_digest[:48],
            child_digest=target.digest,
            phase="confirmation",
            resources=target.resources,
        )
    assert calls == [] and store.replay()["head"] == before


def test_failed_source_does_not_fabricate_follower_scores(tmp_path):
    store, plan, grants, service, calls = baseline_suite(
        tmp_path, result=PublicScore("timeout", "power", "W", None, None)
    )
    service.confirm(grants[0])
    report = analyze_confirmation(store, plan)
    assert report["scored_cells"] == report["physical_score_receipts"] == 1
    assert not report["shared_baselines"] and calls == [1]


def test_protocol_identity_changes_and_legacy_bytes_remain_exact():
    from autoengineering.utility.contracts import UtilitySuiteSpec

    legacy = suite()
    raw = legacy.to_json()
    assert "baseline_reuse" not in raw
    assert UtilitySuiteSpec.from_json(raw).to_json() == raw
    with pytest.raises(ValueError):
        UtilitySuiteSpec.from_dict(legacy.to_dict() | {"baseline_reuse": None})


def test_wrong_frozen_parameters_stop_before_any_confirmation_charge(tmp_path):
    store, _, grants, service, calls = baseline_suite(tmp_path, configuration_digest="3" * 64)
    before = store.replay()["head"]
    with pytest.raises(ValueError, match="parameters"):
        service.confirm(grants[0])
    assert calls == [] and store.replay()["head"] == before


def test_recovery_reuses_original_source_after_publication_interruption(tmp_path):
    from test_utility_confirmation_recovery import SavedScorer

    store, plan, grants, service, _ = baseline_suite(tmp_path)
    scorer = SavedScorer()
    service.scorer = scorer

    def fault(point):
        if point == "confirmation_score_created":
            raise RuntimeError("authored source publication interruption")

    store.fault = fault
    with pytest.raises(RuntimeError):
        service.confirm(grants[0])
    store.fault = lambda _: None
    before = store.replay()
    report = analyze_confirmation(store, plan)
    assert report["scored_cells"] == 0 and not report["shared_baselines"]
    with pytest.raises(ValueError):
        service.confirm(grants[0])
    service.recover(grants[0])
    after = store.replay()
    assert after["used"] == before["used"]
    assert after["confirmation_accesses"] == before["confirmation_accesses"]
    assert analyze_confirmation(store, plan)["scored_cells"] == 2
    assert scorer.calls == scorer.recoveries == 1


def test_report_and_export_allocate_one_cost_and_mark_reused_cell(tmp_path):
    import csv
    import io
    from autoengineering.campaign.artifacts import put_bytes
    from autoengineering.utility.reporting import ReportSpec, comparative_report, report_files

    store, plan, grants, service, _ = baseline_suite(tmp_path)
    service.confirm(grants[0])
    ref = put_bytes(
        store.root,
        plan.to_json().encode(),
        name="analysis.json",
        media_type="application/json",
        producer="authored-fixture",
    )
    report = comparative_report(
        store, ReportSpec("utility-report-inputs-v1", store.spec.digest, ref, None, ())
    )
    assert [r["confirmation_reused"] for r in report["cells"]] == [False, True]
    assert {r["confirmation_status"] for r in report["cells"]} == {"success"}
    files = report_files(report)
    costs = list(csv.DictReader(io.StringIO(files["cost-allocations.csv"].decode())))
    reserved = [r for r in costs if r["resource"] == "confirmation_reservations"]
    assert len(reserved) == 2 and len({r["receipt_id"] for r in reserved}) == 1
    assert sum(float(r["allocated_quantity"]) for r in reserved) == 1.0
    assert [float(r["allocation"]) for r in reserved] == [0.25, 0.75]
    assert "confirmation_reused" in files["cells.csv"].decode().splitlines()[0]


def test_policy_changes_are_new_identity_and_invalid_groups_reject(tmp_path):
    from autoengineering.utility.contracts import BaselineReusePolicy, UtilitySuiteSpec
    from autoengineering.utility.store import SuiteStore

    store, _, _, _, _ = baseline_suite(tmp_path)
    spec = store.spec
    assert UtilitySuiteSpec.from_json(spec.to_json()) == spec
    group = spec.baseline_reuse.groups[0]
    changed = replace(spec.baseline_reuse, groups=(replace(group, allocation=(0.5, 0.5)),))
    with pytest.raises(ValueError):
        replace(spec, baseline_reuse=changed)
    successor = replace(spec, protocol_digest=changed.digest, baseline_reuse=changed)
    assert successor.digest != spec.digest
    with pytest.raises(ValueError):
        SuiteStore(store.root, expected=successor)
    with pytest.raises(ValueError):
        BaselineReusePolicy("utility-baseline-reuse-v1", H, (group, group))
    with pytest.raises(ValueError):
        replace(spec, routes=tuple(replace(r, kind="conventional") for r in spec.routes))


def test_source_cannot_change_the_prefrozen_scorer_identity(tmp_path):
    store, _, grants, service, calls = baseline_suite(tmp_path)
    changed = replace(grants[0], scorer_digest="3" * 64)
    changed_service = ConfirmationService(
        store,
        service.scorer,
        scorer_digest=changed.scorer_digest,
        outcome_contract=service.outcome_contract,
    )
    before = store.replay()["head"]
    with pytest.raises(ValueError, match="scorer"):
        changed_service.confirm(changed)
    assert calls == [] and store.replay()["head"] == before
