"""Behavioral contracts for durable optimization observations."""

import hashlib
import json
import math

import pytest

from autoengineering.optimization import (
    EvaluationAction,
    EvaluationResult,
    EvaluationScope,
    EvaluationStatus,
    LedgerCorruptionError,
    ObservationLedger,
)


def test_ledger_round_trip_is_byte_stable(tmp_path):
    """Changing replay into a rewrite must fail this test."""
    path = tmp_path / "observations.jsonl"
    ledger = ObservationLedger(path)
    action = EvaluationAction.system("eval-000001", {"x": 0.25}, seed=17)
    result = EvaluationResult.success(
        action_id=action.id,
        outcomes={"score": 1.5},
        standard_errors={"score": 0.1},
        cost=2.0,
        cost_unit="cpu_hour",
    )

    ledger.append(action, result)

    first = path.read_bytes()
    assert ObservationLedger(path).entries() == ((action, result),)
    assert path.read_bytes() == first


def test_duplicate_action_id_is_rejected(tmp_path):
    """Removing duplicate detection must fail this test."""
    ledger = ObservationLedger(tmp_path / "observations.jsonl")
    action = EvaluationAction.system("eval-000001", {"x": 0.25}, seed=17)
    ledger.append(action, EvaluationResult.infrastructure_failure(action.id, "queue"))

    with pytest.raises(ValueError, match="duplicate action id"):
        ledger.append(action, EvaluationResult.infrastructure_failure(action.id, "queue"))


def test_constraint_training_keeps_scientific_infeasibility_not_operational_failures(tmp_path):
    """Treating operational failures as constraint observations must fail this test."""
    ledger = ObservationLedger(tmp_path / "observations.jsonl")
    actions = tuple(
        EvaluationAction.system(f"eval-{index:06d}", {"x": index}, seed=index)
        for index in range(1, 5)
    )
    ledger.append(
        actions[0],
        EvaluationResult.success(actions[0].id, {"score": 1.5}, {"score": 0.1}, 2.0, "cpu_hour"),
    )
    ledger.append(actions[1], EvaluationResult.scientific_infeasible(actions[1].id, "validation"))
    ledger.append(actions[2], EvaluationResult.model_failure(actions[2].id, "import"))
    ledger.append(actions[3], EvaluationResult.infrastructure_failure(actions[3].id, "queue"))

    constraint_statuses = tuple(result.status for _, result in ledger.constraint_training_entries())
    assert constraint_statuses == (
        EvaluationStatus.SUCCESS,
        EvaluationStatus.SCIENTIFIC_INFEASIBLE,
    )
    assert tuple(result.status for _, result in ledger.objective_training_entries()) == (
        EvaluationStatus.SUCCESS,
    )


def test_ledger_rejects_a_different_cost_unit_after_the_first_observation(tmp_path):
    """Dropping study-wide cost-unit consistency must fail this test."""
    ledger = ObservationLedger(tmp_path / "observations.jsonl")
    first = EvaluationAction.system("eval-000001", {"x": 0.25}, seed=1)
    second = EvaluationAction.system("eval-000002", {"x": 0.5}, seed=2)
    ledger.append(first, EvaluationResult.success(first.id, {"score": 1.0}, {}, 1.0, "cpu_hour"))

    with pytest.raises(ValueError, match="cost_unit"):
        ledger.append(
            second,
            EvaluationResult.timeout(second.id, "deadline", cost=1.0, cost_unit="wall_second"),
        )


def test_records_freeze_input_mappings_and_support_system_and_component_factories():
    """Retaining mutable input mappings or losing component scope must fail this test."""
    config = {"choice": "linear", "count": 2, "rate": 0.25, "enabled": True}
    action = EvaluationAction.system("eval-000001", config, seed=7)
    component = EvaluationAction.component(
        "eval-000002",
        "routing",
        {"method": "muskingum"},
        parent_artifact_ids=("upstream-output",),
        replicates=2,
        seed=8,
        suggested_by="random",
    )
    outcomes = {"score": 1.5}
    hashes = {"report": "a" * 64}
    result = EvaluationResult.success(
        action.id,
        outcomes,
        {"score": 0.1},
        2.0,
        "cpu_hour",
        artifacts={"report": "report.txt"},
        artifact_sha256=hashes,
    )
    config["rate"] = 0.75
    outcomes["score"] = 9.0
    hashes["report"] = "b" * 64

    assert action.config == {"choice": "linear", "count": 2, "rate": 0.25, "enabled": True}
    assert component.scope is EvaluationScope.COMPONENT
    assert component.component == "routing"
    assert component.parent_artifact_ids == ("upstream-output",)
    assert result.outcomes == {"score": 1.5}
    assert result.artifact_sha256 == {"report": "a" * 64}
    with pytest.raises(TypeError):
        action.config["rate"] = 1.0
    with pytest.raises(TypeError):
        result.artifacts["report"] = "other.txt"


@pytest.mark.parametrize(
    ("factory", "status"),
    [
        (EvaluationResult.scientific_infeasible, EvaluationStatus.SCIENTIFIC_INFEASIBLE),
        (EvaluationResult.model_failure, EvaluationStatus.MODEL_FAILURE),
        (EvaluationResult.timeout, EvaluationStatus.TIMEOUT),
        (EvaluationResult.infrastructure_failure, EvaluationStatus.INFRASTRUCTURE_FAILURE),
    ],
)
def test_failure_factories_classify_operational_and_scientific_outcomes(factory, status):
    """Returning the wrong durable status from any factory must fail this test."""
    result = factory("eval-000001", "reason", cost=0.5, cost_unit="cpu_hour")

    assert result.status is status
    assert result.outcomes == {}
    assert result.standard_errors == {}
    assert result.cost == 0.5


def test_records_reject_nonfinite_and_invalid_measurements():
    """Permitting invalid scientific measurements must fail this test."""
    with pytest.raises(ValueError, match="finite"):
        EvaluationAction.system("eval-000001", {"x": math.nan})
    with pytest.raises(ValueError, match="successful results must include outcomes"):
        EvaluationResult.success("eval-000001", {}, {}, 1.0, "cpu_hour")
    with pytest.raises(ValueError, match="standard_errors keys"):
        EvaluationResult.success("eval-000001", {"score": 1.0}, {"other": 0.1}, 1.0, "cpu_hour")
    with pytest.raises(ValueError, match="non-negative"):
        EvaluationResult.success("eval-000001", {"score": 1.0}, {}, -1.0, "cpu_hour")
    with pytest.raises(ValueError, match="finite"):
        EvaluationResult.success("eval-000001", {"score": math.inf}, {}, 1.0, "cpu_hour")


def test_append_verifies_artifact_hash_before_writing(tmp_path):
    """Accepting a missing or mismatched artifact must fail this test."""
    path = tmp_path / "observations.jsonl"
    artifact = tmp_path / "report.txt"
    artifact.write_text("scientific output", encoding="utf-8")
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    action = EvaluationAction.system("eval-000001", {"x": 0.25})
    result = EvaluationResult.success(
        action.id,
        {"score": 1.0},
        {},
        1.0,
        "cpu_hour",
        artifacts={"report": "report.txt"},
        artifact_sha256={"report": digest},
    )

    ObservationLedger(path).append(action, result)
    assert ObservationLedger(path).entries() == ((action, result),)

    changed = artifact.with_name("changed.txt")
    changed.write_text("different output", encoding="utf-8")
    failed = EvaluationAction.system("eval-000002", {"x": 0.5})
    mismatched = EvaluationResult.success(
        failed.id,
        {"score": 2.0},
        {},
        1.0,
        "cpu_hour",
        artifacts={"changed": "changed.txt"},
        artifact_sha256={"changed": digest},
    )
    with pytest.raises(ValueError, match="SHA-256"):
        ObservationLedger(path).append(failed, mismatched)


def test_ledger_rejects_id_mismatch_and_reports_corrupt_line_numbers(tmp_path):
    """Dropping pair validation or line context must fail this test."""
    path = tmp_path / "observations.jsonl"
    ledger = ObservationLedger(path)
    action = EvaluationAction.system("eval-000001", {"x": 0.25})
    with pytest.raises(ValueError, match="IDs must match"):
        ledger.append(
            action,
            EvaluationResult.success("eval-000002", {"score": 1.0}, {}, 1.0, "cpu_hour"),
        )

    path.write_bytes(b'{"action":')
    with pytest.raises(LedgerCorruptionError, match="line 1: truncated final line"):
        ledger.entries()

    path.write_bytes(b"{}\n")
    with pytest.raises(LedgerCorruptionError, match="line 1"):
        ledger.entries()


def test_multiple_appends_preserve_prior_bytes_and_round_trip_scalar_types(tmp_path):
    """Rewriting earlier lines or coercing scalar configuration types must fail this test."""
    path = tmp_path / "observations.jsonl"
    ledger = ObservationLedger(path)
    first = EvaluationAction.system(
        "eval-000001", {"name": "α", "count": 3, "rate": 0.25, "enabled": False}, seed=1
    )
    second = EvaluationAction.system(
        "eval-000002", {"name": "β", "count": 4, "rate": 0.5, "enabled": True}, seed=2
    )
    ledger.append(first, EvaluationResult.success(first.id, {"score": 1.0}, {}, 1.0, "cpu_hour"))
    first_bytes = path.read_bytes()
    ledger.append(second, EvaluationResult.success(second.id, {"score": 2.0}, {}, 2.0, "cpu_hour"))

    assert path.read_bytes().startswith(first_bytes)
    assert ObservationLedger(path).entries() == (
        (first, EvaluationResult.success(first.id, {"score": 1.0}, {}, 1.0, "cpu_hour")),
        (second, EvaluationResult.success(second.id, {"score": 2.0}, {}, 2.0, "cpu_hour")),
    )
    encoded = json.loads(first_bytes.decode("utf-8"))
    assert encoded["action"]["config"] == {"count": 3, "enabled": False, "name": "α", "rate": 0.25}


def test_empty_and_missing_ledgers_have_no_entries(tmp_path):
    """Treating absent or empty ledgers as corrupt must fail this test."""
    missing = ObservationLedger(tmp_path / "missing.jsonl")
    empty_path = tmp_path / "empty.jsonl"
    empty_path.touch()

    assert missing.entries() == ()
    assert ObservationLedger(empty_path).entries() == ()


def test_replay_rejects_persisted_positive_cost_unit_inconsistency(tmp_path):
    """Accepting mixed units in a persisted study ledger must fail this test."""
    path = tmp_path / "observations.jsonl"
    first = EvaluationAction.system("eval-000001", {"x": 0.25})
    second = EvaluationAction.system("eval-000002", {"x": 0.5})
    records = (
        (first, EvaluationResult.success(first.id, {"score": 1.0}, {}, 1.0, "cpu_hour")),
        (second, EvaluationResult.success(second.id, {"score": 2.0}, {}, 1.0, "wall_second")),
    )
    path.write_text(
        "".join(
            json.dumps(
                {"action": action.to_dict(), "result": result.to_dict()},
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n"
            for action, result in records
        ),
        encoding="utf-8",
    )

    with pytest.raises(LedgerCorruptionError, match="line 2.*cost_unit"):
        ObservationLedger(path).entries()
