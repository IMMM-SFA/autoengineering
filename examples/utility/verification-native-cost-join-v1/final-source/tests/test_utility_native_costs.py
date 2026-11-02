"""Native work joins retain exact original processes and distinct counter scopes."""

import pytest

from autoengineering.utility.costs import reconcile
from autoengineering.utility.native_costs import join_native_costs
from test_utility_engineering_native import setup as circuit
from test_utility_callback_native import setup as callback

MAPPING = {"first": "1" * 64, "second": "2" * 64}


def test_native_join_preserves_outer_process_and_final_snapshot_counts(tmp_path, monkeypatch):
    driver, batch, _ = circuit(tmp_path)
    report = driver.run()
    before = batch.replay()
    monkeypatch.setattr(
        "subprocess.Popen", lambda *_a, **_k: pytest.fail("reader launched a process")
    )
    records = join_native_costs(batch, MAPPING)
    quantities = {r.resource: r.quantity for r in records}
    assert quantities == {
        "native_driver_process_starts": 1,
        "native_inner_model_calls": 4,
        "native_driver_derivative_calls": 1,
        "native_scenario_derivative_calls": 2,
        "native_driver_final_solver_iterations": 2,
        "native_driver_final_component_calls": 5,
        "native_scenario_solver_iterations": 4,
        "native_scenario_component_calls": 10,
    }
    assert all(
        r.source_digest == report.digest and r.cell_digests == (MAPPING["first"],) for r in records
    )
    assert reconcile(records, tuple(r.receipt_id for r in records))["complete"]
    assert join_native_costs(batch, MAPPING) == records
    assert batch.replay() == before


def test_callback_join_keeps_wake_gradient_entries_separate_from_inner_solves(
    tmp_path, monkeypatch
):
    driver, batch, _ = callback(tmp_path)
    driver.run()
    monkeypatch.setattr(
        "subprocess.Popen", lambda *_a, **_k: pytest.fail("reader launched a process")
    )
    records = join_native_costs(batch, MAPPING)
    q = {r.resource: r.quantity for r in records}
    assert q["native_driver_process_starts"] == 1
    assert q["native_callback_entries"] == 2
    assert q["native_wake_callbacks_completed"] == q["native_gradient_callbacks_attempted"] == 1
    assert not any("inner_model" in name or "solver" in name for name in q)


@pytest.mark.parametrize("mode", ["timeout", "error", "overflow"])
def test_failed_callback_preserves_unknown_work_for_each_frozen_kind(tmp_path, mode):
    driver, batch, _ = callback(tmp_path, mode=mode, timeout=0.05 if mode == "timeout" else 6)
    driver.run()
    records = join_native_costs(batch, MAPPING)
    q = {r.resource: r.quantity for r in records}
    assert q["native_driver_process_starts"] == 1
    assert q["native_callback_entries"] is None
    assert all(
        q[f"native_{kind}_callbacks_{status}"] is None
        for kind in ("wake", "gradient")
        for status in ("attempted", "completed", "failed", "unresolved")
    )
    assert not reconcile(records, tuple(r.receipt_id for r in records))["complete"]


@pytest.mark.parametrize(
    "target", ["process/stdout.bin", "process/job.json", "process/completion.json", "job.json"]
)
def test_native_join_rejects_corrupted_original_inputs_and_output(tmp_path, target):
    driver, batch, _ = circuit(tmp_path)
    driver.run()
    (driver.directory / target).write_bytes(b"corrupt")
    with pytest.raises(ValueError):
        join_native_costs(batch, MAPPING)
    assert len(batch.replay().reservations) == 1


@pytest.mark.parametrize("mapping", [{"first": "1" * 64}, {"first": "1" * 64, "second": "1" * 64}])
def test_native_cost_mapping_cannot_drop_or_duplicate_cells(tmp_path, mapping):
    _, batch, _ = circuit(tmp_path)
    with pytest.raises(ValueError, match="mapping"):
        join_native_costs(batch, mapping)


def test_pending_native_permission_does_not_invent_observed_work(tmp_path):
    def fault(stage):
        if stage == "native_reserved":
            raise RuntimeError("authored interruption before native launch")

    driver, batch, _ = circuit(tmp_path, fault=fault)
    with pytest.raises(RuntimeError):
        driver.run()
    assert join_native_costs(batch, MAPPING) == ()
    assert len(batch.replay().pending) == 1


@pytest.mark.parametrize("iterations", [5, 2])
def test_wind_join_uses_original_typed_callback_receipts(tmp_path, monkeypatch, iterations):
    from test_utility_wind_process import setup as wind

    driver, batch, _ = wind(tmp_path, iterations=iterations)
    report = driver.run()
    monkeypatch.setattr(
        "subprocess.Popen", lambda *_a, **_k: pytest.fail("reader launched a process")
    )
    records = join_native_costs(batch, MAPPING)
    q = {r.resource: r.quantity for r in records}
    assert q["wind_native_process_starts"] == 1
    if report.result:
        assert q["wind_native_wake_callbacks_completed"] == 1
        assert q["wind_native_gradient_callbacks_failed"] == 1
    else:
        assert all(v is None for k, v in q.items() if "callbacks" in k)
    assert not any("inner_model" in name or "solver" in name for name in q)


def test_suite_accounting_joins_native_work_offline_and_blocks_corrupted_stdout(
    tmp_path, monkeypatch
):
    from autoengineering.utility.engineering_execution import ScriptedEngineeringCoordinator
    from autoengineering.utility.report import accounting_report
    from test_utility_engineering_execution import setup as suite

    store, plan, source = suite(tmp_path)
    assert ScriptedEngineeringCoordinator(store, plan, source).run()["finished_cells"] == 2
    before = store.replay()["head"]
    monkeypatch.setattr(
        "subprocess.Popen", lambda *_a, **_k: pytest.fail("reader launched a process")
    )
    report = accounting_report(store)
    native = [r for r in report["receipts"] if r["resource"].startswith("native_")]
    assert len(native) == 8 and not report["evidence_blockers"]
    assert (
        sum(r["quantity"] for r in native if r["resource"] == "native_driver_process_starts") == 1
    )
    assert not report["complete_cost_evidence"]
    assert accounting_report(store) == report and store.replay()["head"] == before
    outputs = list(store.root.glob("children/*/cases/*/native-drivers/*/process/stdout.bin"))
    assert len(outputs) == 1
    outputs[0].write_bytes(b"corrupt original native output")
    corrupted = accounting_report(store)
    assert corrupted["evidence_blockers"]
    assert not any(r["resource"].startswith("native_") for r in corrupted["receipts"])
    assert store.replay()["head"] == before
