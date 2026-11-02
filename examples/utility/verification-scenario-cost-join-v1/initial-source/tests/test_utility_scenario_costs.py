"""Original scenario process evidence joins without new model work."""

import pytest

from autoengineering.optimization.records import EvaluationAction
from autoengineering.utility.engineering_process import SupervisedEngineeringExecutor
from autoengineering.utility.scenario_costs import join_scenario_costs
from test_utility_engineering_process import setup

MAPPING = {"first": "1" * 64, "second": "2" * 64}


def run(tmp_path, *, x=0.5, timeout=5.0, fault=lambda _: None):
    batch, spec, source = setup(tmp_path, timeout=timeout, one_scenario=True)
    executor = SupervisedEngineeringExecutor(spec, batch, "first", source, fault=fault)
    executor(EvaluationAction("cost-action", {"x": x}, "system", None, seed=17))
    return batch, executor


def test_scenario_costs_read_original_counters_without_source_or_processes(tmp_path, monkeypatch):
    batch, executor = run(tmp_path)
    before = batch.replay()
    # The reader must need only the saved job and process, not the evaluator tree.
    import shutil

    shutil.rmtree(tmp_path / "captured")
    monkeypatch.setattr("subprocess.Popen", lambda *_a, **_k: pytest.fail("reader launched"))
    records = join_scenario_costs(batch, MAPPING)
    quantities = {r.resource: r.quantity for r in records}
    assert quantities == {
        "scenario_process_starts": 1,
        "scenario_lifecycle_duration": 0.01,
        "scenario_solves": 1,
        "scenario_solver_iterations": None,
        "scenario_component_calls": None,
        "scenario_derivative_calls": None,
    }
    assert all(r.cell_digests == (MAPPING["first"],) for r in records)
    assert join_scenario_costs(batch, MAPPING) == records
    assert batch.replay() == before
    assert executor.directory.exists()


@pytest.mark.parametrize("x,timeout", [(0.0, 0.1), (1.0, 5.0)])
def test_failed_scenario_has_known_start_and_unknown_inner_work(tmp_path, x, timeout):
    batch, _ = run(tmp_path, x=x, timeout=timeout)
    records = join_scenario_costs(batch, MAPPING)
    assert next(r.quantity for r in records if r.resource == "scenario_process_starts") == 1
    assert all(r.quantity is None for r in records if r.resource != "scenario_process_starts")


@pytest.mark.parametrize(
    "name",
    [
        "scenario.json",
        "process/stdout.bin",
        "process/job.json",
        "process/completion.json",
    ],
)
def test_scenario_costs_reject_changed_original_bytes(tmp_path, name):
    batch, executor = run(tmp_path)
    root = next(p for p in executor.directory.iterdir() if p.is_dir())
    (root / name).write_bytes(b"changed")
    with pytest.raises(ValueError):
        join_scenario_costs(batch, MAPPING)
    assert len(batch.replay().reservations) == 1


def test_scenario_costs_reject_changed_execution_binding(tmp_path):
    batch, executor = run(tmp_path)
    (executor.directory / "execution.json").write_bytes(b"{}")
    with pytest.raises(ValueError):
        join_scenario_costs(batch, MAPPING)


def test_pending_scenario_does_not_invent_starts(tmp_path):
    batch, spec, source = setup(tmp_path, one_scenario=True)

    def fault(stage):
        if stage == "engineering_scenario_reserved":
            raise RuntimeError("authored interruption before launch")

    executor = SupervisedEngineeringExecutor(spec, batch, "first", source, fault=fault)
    with pytest.raises(RuntimeError):
        executor(EvaluationAction("pending-action", {"x": 0.5}, "system", None, seed=17))
    assert join_scenario_costs(batch, MAPPING) == ()
    assert len(batch.replay().pending) == 1


@pytest.mark.parametrize(
    "mapping",
    [
        {"first": "1" * 64},
        {"first": "1" * 64, "second": "1" * 64},
    ],
)
def test_scenario_cost_mapping_rejects_missing_or_duplicate_cell(tmp_path, mapping):
    batch, _, _ = setup(tmp_path, one_scenario=True)
    with pytest.raises(ValueError, match="mapping"):
        join_scenario_costs(batch, mapping)
