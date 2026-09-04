"""Recovery contracts for durable optimization studies."""

from dataclasses import replace
import json
import os
import subprocess
import sys

import pytest

from autoengineering.optimization import (
    BudgetSpec,
    CategoricalParameter,
    BackendDiagnostics,
    EvaluationAction,
    EvaluationResult,
    EvaluationScope,
    NoiseSpec,
    ObjectiveSpec,
    ObservationLedger,
    SearchSpace,
    SobolBackend,
    StudyRecoveryError,
    StudySpec,
)
from autoengineering.optimization.controller import OptimizationStudy
from autoengineering.optimization.provenance import canonical_json


@pytest.fixture
def spec():
    return StudySpec(
        name="recovery",
        objective=ObjectiveSpec(outcome="score", direction="maximize"),
        constraints=(),
        budget=BudgetSpec(max_cost=4.0, cost_unit="run", initial_cost_estimate=1.0),
        noise=NoiseSpec(),
        backend="system",
        seed=17,
    )


@pytest.fixture
def space():
    return SearchSpace(parameters=(CategoricalParameter("model", ("a", "b", "c", "d")),))


def _evaluator(action):
    return EvaluationResult.success(
        action.id,
        {"score": float(ord(action.config["model"]) - ord("a"))},
        {},
        1.0,
        "run",
    )


def _partial_evaluator(action):
    return EvaluationResult.success(
        action.id, {"model.value": 1.0}, {}, 0.25, "run"
    )


def _study(
    directory,
    spec,
    space,
    *,
    backend=None,
    ledger=None,
    wall_clock=lambda: "2026-09-04T12:00:00Z",
    input_hashes=None,
    target_value=None,
):
    backend = SobolBackend(spec, space) if backend is None else backend
    ledger = ObservationLedger(directory / "observations.jsonl") if ledger is None else ledger
    return OptimizationStudy(
        spec,
        space,
        backend,
        ledger,
        _evaluator,
        directory,
        wall_clock=wall_clock,
        target_value=target_value,
        input_artifact_hashes={"system.yaml": "a" * 64} if input_hashes is None else input_hashes,
    )


def _abandon(study):
    lock = study._pending_lock
    if lock is not None:
        lock.__exit__(None, None, None)
        study._pending_lock = None


def _snapshot(directory):
    snapshot = {}
    for path in sorted(directory.iterdir()):
        if path.name.endswith(".lock") or path.name == ".study.lock":
            continue
        if path.is_symlink():
            snapshot[path.name] = ("symlink", os.readlink(path))
        elif path.is_file():
            snapshot[path.name] = ("file", path.read_bytes())
    return snapshot


class _ConfiguredSobol(SobolBackend):
    name = "configured-sobol"

    def __init__(self, spec, space, *, stride):
        super().__init__(spec, space)
        self.stride = stride
        self.mutable_marker = "fresh"

    def identity_dict(self):
        return {
            "schema_version": "1.0",
            "name": self.name,
            "constructor": {"stride": self.stride},
        }

    def state_dict(self):
        return {**super().state_dict(), "mutable_marker": self.mutable_marker}


class _SnapshotReadingSobol(SobolBackend):
    name = "snapshot-reading-sobol"

    def suggest(self, ledger, n=1):
        entries, contents = ledger.snapshot()
        assert contents == b"".join(ledger.record_bytes(*entry) for entry in entries)
        return super().suggest(ledger, n=n)


class _PartialComponentBackend:
    name = "function_network_partial_test"

    def __init__(self, spec, space):
        self.spec = spec
        self.space = space

    def suggest(self, ledger, n=1):
        entries = ledger.entries()
        return (
            EvaluationAction.component(
                f"eval-{len(entries):06d}",
                "model",
                {"model.choice": "base"},
                suggested_by=self.name,
            ),
        )

    def recommend(self, ledger):
        from autoengineering.optimization import Recommendation

        return Recommendation(None, {}, {}, False, "component results are not terminal")

    def diagnostics(self, ledger):
        return BackendDiagnostics(
            self.name,
            "test_backend",
            details={"ledger_entries": len(ledger.entries())},
        )

    def identity_dict(self):
        return {"schema_version": "1.0", "name": self.name, "constructor": {}}

    def state_dict(self):
        return {"schema_version": "1.0", "name": self.name}

    def validate_entries(self, entries):
        for index, (action, _) in enumerate(entries):
            if action.scope is not EvaluationScope.COMPONENT or action.id != f"eval-{index:06d}":
                raise ValueError("invalid mixed-scope test ledger")

    def validate_action(self, action, entries):
        if (
            action.scope is not EvaluationScope.COMPONENT
            or action.component != "model"
            or action.config != {"model.choice": "base"}
            or action.id != f"eval-{len(entries):06d}"
        ):
            raise ValueError("invalid component action")

    def estimated_action_cost(self, action, entries):
        return 0.25

    def minimum_action_cost(self, entries):
        return 0.25


class _AlteredEncodingSpace(SearchSpace):
    @property
    def encoded_dimension(self):
        return super().encoded_dimension + 1


def test_backend_identity_is_stable_and_separate_from_mutable_state(spec, space):
    backend = _ConfiguredSobol(spec, space, stride=3)
    identity = backend.identity_dict()

    backend.mutable_marker = "fitted"

    assert backend.identity_dict() == identity
    assert backend.state_dict()["mutable_marker"] == "fitted"
    assert identity["constructor"] == {"stride": 3}


def test_recovery_replay_supports_the_public_read_only_ledger_surface(tmp_path, spec, space):
    backend = _SnapshotReadingSobol(spec, space)
    first = _study(tmp_path, spec, space, backend=backend)
    action = first.ask()[0]
    _abandon(first)

    resumed = _study(
        tmp_path,
        spec,
        space,
        backend=_SnapshotReadingSobol(spec, space),
    )

    assert resumed.ledger.entries()[0][0] == action


def test_controller_rejects_a_backend_bound_to_different_inputs(tmp_path, spec, space):
    other_space = SearchSpace((CategoricalParameter("model", ("x", "y")),))

    with pytest.raises(ValueError, match="backend spec and search space"):
        _study(tmp_path, spec, space, backend=SobolBackend(spec, other_space))

    assert _snapshot(tmp_path) == {}


def test_new_study_writes_manifest_last_and_records_complete_identity(tmp_path, spec, space):
    study = _study(tmp_path, spec, space)
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    identity = manifest["run_identity"]

    assert identity["study"] == spec.to_dict()
    assert identity["search_space"]["encoded_dimension"] == space.encoded_dimension
    assert identity["backend"]["name"] == "sobol"
    assert identity["ledger"]["path"] == "observations.jsonl"
    assert identity["ledger"]["committed_sha256"]
    assert identity["input_artifact_hashes"] == {"system.yaml": "a" * 64}
    assert identity["seed"] == spec.seed
    assert identity["start_timestamp"] == study.start_timestamp
    assert manifest["run_identity_sha256"]
    assert (tmp_path / "observations.jsonl").is_file()


@pytest.mark.parametrize(
    "mismatch",
    ("study", "seed", "space", "encoding", "backend", "config", "ledger", "input"),
)
def test_incompatible_resume_fails_without_changing_existing_state(tmp_path, spec, space, mismatch):
    _study(tmp_path, spec, space)
    before = _snapshot(tmp_path)
    resumed_spec = spec
    resumed_space = space
    backend = SobolBackend(spec, space)
    ledger = ObservationLedger(tmp_path / "observations.jsonl")
    input_hashes = {"system.yaml": "a" * 64}
    if mismatch == "study":
        resumed_spec = replace(spec, name="other")
    elif mismatch == "seed":
        resumed_spec = replace(spec, seed=18)
    elif mismatch == "space":
        resumed_space = SearchSpace((CategoricalParameter("model", ("a", "b")),))
    elif mismatch == "encoding":
        resumed_space = _AlteredEncodingSpace(space.parameters)
    elif mismatch == "backend":
        backend = _ConfiguredSobol(spec, space, stride=3)
    elif mismatch == "config":
        initial = _ConfiguredSobol(spec, space, stride=3)
        alternate_directory = tmp_path / "configured"
        _study(alternate_directory, spec, space, backend=initial)
        before = _snapshot(alternate_directory)
        tmp_path = alternate_directory
        ledger = ObservationLedger(tmp_path / "observations.jsonl")
        backend = _ConfiguredSobol(spec, space, stride=4)
    elif mismatch == "ledger":
        ledger = ObservationLedger(tmp_path / "alternate.jsonl")
    elif mismatch == "input":
        input_hashes = {"system.yaml": "b" * 64}
    if mismatch in {"study", "seed", "space", "encoding"}:
        backend = SobolBackend(resumed_spec, resumed_space)

    with pytest.raises(StudyRecoveryError):
        _study(
            tmp_path,
            resumed_spec,
            resumed_space,
            backend=backend,
            ledger=ledger,
            input_hashes=input_hashes,
        )

    assert _snapshot(tmp_path) == before


def test_ledger_must_be_a_real_file_bound_to_the_study_directory(tmp_path, spec, space):
    workdir = tmp_path / "study"
    outside = ObservationLedger(tmp_path / "outside.jsonl")

    with pytest.raises(StudyRecoveryError, match="ledger path"):
        _study(workdir, spec, space, ledger=outside)
    assert not workdir.exists()

    workdir.mkdir(exist_ok=True)
    target = tmp_path / "target.jsonl"
    target.touch()
    (workdir / "observations.jsonl").symlink_to(target)
    with pytest.raises(StudyRecoveryError, match="symlink"):
        _study(workdir, spec, space)


@pytest.mark.parametrize(
    "reserved_name",
    (
        "manifest.json",
        "backend-state.json",
        "recommendation.json",
        "optimization-report.md",
        "pending-actions.json",
        "pending-control.json",
        "pending-bootstrap.json",
        ".study.lock",
        ".study",
    ),
)
def test_ledger_cannot_use_a_reserved_control_filename(tmp_path, spec, space, reserved_name):
    ledger = ObservationLedger(tmp_path / reserved_name)

    with pytest.raises(StudyRecoveryError, match="reserved"):
        _study(tmp_path, spec, space, ledger=ledger)

    assert _snapshot(tmp_path) == {}


def test_nonempty_ledger_without_a_manifest_is_not_adopted(tmp_path, spec, space):
    ledger = ObservationLedger(tmp_path / "observations.jsonl")
    action = EvaluationAction.system("eval-000000", {"model": "a"})
    ledger.append(action, _evaluator(action))
    before = _snapshot(tmp_path)

    with pytest.raises(StudyRecoveryError, match="manifest"):
        _study(tmp_path, spec, space, ledger=ledger)

    assert _snapshot(tmp_path) == before


@pytest.mark.parametrize(
    ("artifact", "mutation"),
    (
        ("manifest.json", "missing"),
        ("observations.jsonl", "missing"),
        ("backend-state.json", "missing"),
        ("recommendation.json", "symlink"),
        ("manifest.json", "malformed"),
        ("backend-state.json", "schema"),
    ),
)
def test_missing_symlinked_malformed_or_incompatible_control_artifacts_fail_closed(
    tmp_path, spec, space, artifact, mutation
):
    _study(tmp_path, spec, space)
    path = tmp_path / artifact
    if mutation == "missing":
        path.unlink()
    elif mutation == "symlink":
        path.unlink()
        target = tmp_path / "target.json"
        target.write_text("{}\n", encoding="utf-8")
        path.symlink_to(target)
    elif mutation == "malformed":
        path.write_text("{", encoding="utf-8")
    else:
        payload = json.loads(path.read_text())
        payload["schema_version"] = "0.0"
        path.write_text(canonical_json(payload) + "\n", encoding="utf-8")
    before = _snapshot(tmp_path)

    with pytest.raises(StudyRecoveryError):
        _study(tmp_path, spec, space)

    assert _snapshot(tmp_path) == before


def test_manifest_rejects_an_unknown_terminal_reason_without_changes(tmp_path, spec, space):
    _study(tmp_path, spec, space)
    manifest_path = tmp_path / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["stop_reason"] = "unknown_reason"
    manifest["end_timestamp"] = "2026-09-04T12:10:00Z"
    manifest_path.write_text(canonical_json(manifest) + "\n", encoding="utf-8")
    before = _snapshot(tmp_path)

    with pytest.raises(StudyRecoveryError, match="stop reason"):
        _study(tmp_path, spec, space)

    assert _snapshot(tmp_path) == before


@pytest.mark.parametrize(
    "failure_name",
    ("backend-state.json", "recommendation.json", "optimization-report.md", "manifest.json"),
)
def test_initial_artifact_commit_recovers_from_its_bootstrap_transition(
    tmp_path, spec, space, monkeypatch, failure_name
):
    from autoengineering.optimization import provenance

    original_json_write = provenance.atomic_write_json
    original_text_write = provenance.atomic_write_text

    def interrupted_json_write(directory, name, value):
        if name == failure_name:
            raise OSError("simulated bootstrap interruption")
        return original_json_write(directory, name, value)

    def interrupted_text_write(directory, name, value):
        if name == failure_name:
            raise OSError("simulated bootstrap interruption")
        return original_text_write(directory, name, value)

    monkeypatch.setattr(provenance, "atomic_write_json", interrupted_json_write)
    monkeypatch.setattr(provenance, "atomic_write_text", interrupted_text_write)
    with pytest.raises(OSError, match="bootstrap interruption"):
        _study(tmp_path, spec, space)
    monkeypatch.setattr(provenance, "atomic_write_json", original_json_write)
    monkeypatch.setattr(provenance, "atomic_write_text", original_text_write)

    assert (tmp_path / "pending-bootstrap.json").is_file()
    resumed = _study(tmp_path, spec, space)

    assert resumed.ledger.entries() == ()
    assert (tmp_path / "manifest.json").is_file()
    assert not (tmp_path / "pending-bootstrap.json").exists()


def test_bootstrap_residue_after_manifest_commit_is_removed_once(
    tmp_path, spec, space, monkeypatch
):
    import autoengineering.optimization.controller as controller

    original_remove = controller.remove_artifact

    def fail_bootstrap_remove(directory, name):
        if name == "pending-bootstrap.json":
            raise OSError("simulated bootstrap cleanup interruption")
        return original_remove(directory, name)

    monkeypatch.setattr(controller, "remove_artifact", fail_bootstrap_remove)
    with pytest.raises(OSError, match="bootstrap cleanup interruption"):
        _study(tmp_path, spec, space)
    monkeypatch.setattr(controller, "remove_artifact", original_remove)
    before_manifest = (tmp_path / "manifest.json").read_bytes()

    resumed = _study(tmp_path, spec, space)

    assert resumed.ledger.entries() == ()
    assert (tmp_path / "manifest.json").read_bytes() == before_manifest
    assert not (tmp_path / "pending-bootstrap.json").exists()


def test_ledger_change_without_matching_pending_record_fails_closed(tmp_path, spec, space):
    _study(tmp_path, spec, space)
    ledger = ObservationLedger(tmp_path / "observations.jsonl")
    action = EvaluationAction.system("eval-000000", {"model": "a"})
    ledger.append(action, _evaluator(action))
    before = _snapshot(tmp_path)

    with pytest.raises(StudyRecoveryError, match="ledger"):
        _study(tmp_path, spec, space, ledger=ledger)

    assert _snapshot(tmp_path) == before


def test_resume_before_evaluation_records_one_failure_and_preserves_identity(tmp_path, spec, space):
    first = _study(tmp_path, spec, space)
    original_manifest = json.loads((tmp_path / "manifest.json").read_text())
    action = first.ask()[0]
    _abandon(first)

    resumed = _study(tmp_path, spec, space)
    after_first_resume = (tmp_path / "observations.jsonl").read_bytes()
    second_resume = _study(tmp_path, spec, space)

    entries = resumed.ledger.entries()
    assert len(entries) == 1
    assert entries[0][0] == action
    assert entries[0][1].status.value == "infrastructure_failure"
    assert second_resume.ledger.path.read_bytes() == after_first_resume
    current = json.loads((tmp_path / "manifest.json").read_text())
    assert (
        current["run_identity"]["start_timestamp"]
        == original_manifest["run_identity"]["start_timestamp"]
    )


def test_pending_record_binds_the_committed_identity_and_original_start(tmp_path, spec, space):
    study = _study(tmp_path, spec, space)
    manifest = json.loads((tmp_path / "manifest.json").read_text())

    study.ask()
    pending = json.loads((tmp_path / "pending-actions.json").read_text())
    _abandon(study)

    assert pending["run_identity_sha256"] == manifest["run_identity_sha256"]
    assert (
        pending["committed_ledger_sha256"] == manifest["run_identity"]["ledger"]["committed_sha256"]
    )
    assert pending["original_start_timestamp"] == manifest["run_identity"]["start_timestamp"]


def test_resume_commits_a_persisted_result_once(tmp_path, spec, space):
    first = _study(tmp_path, spec, space)
    action = first.ask()[0]
    pending_path = tmp_path / "pending-actions.json"
    pending = json.loads(pending_path.read_text())
    pending["result"] = _evaluator(action).to_dict()
    pending_path.write_text(canonical_json(pending) + "\n", encoding="utf-8")
    _abandon(first)

    resumed = _study(tmp_path, spec, space)

    assert resumed.ledger.entries() == ((action, _evaluator(action)),)
    assert not pending_path.exists()


def test_resume_accepts_only_the_exact_pending_ledger_extension(tmp_path, spec, space):
    first = _study(tmp_path, spec, space)
    action = first.ask()[0]
    result = _evaluator(action)
    pending_path = tmp_path / "pending-actions.json"
    pending = json.loads(pending_path.read_text())
    pending["result"] = result.to_dict()
    pending_path.write_text(canonical_json(pending) + "\n", encoding="utf-8")
    first.ledger.append(action, result)
    _abandon(first)

    resumed = _study(tmp_path, spec, space)
    ledger_bytes = resumed.ledger.path.read_bytes()
    _study(tmp_path, spec, space)

    assert resumed.ledger.entries() == ((action, result),)
    assert resumed.ledger.path.read_bytes() == ledger_bytes
    assert not pending_path.exists()


@pytest.mark.parametrize("boundary", ("before_evaluation", "after_result", "after_ledger"))
def test_partial_component_action_recovers_once_at_each_pending_boundary(tmp_path, boundary):
    spec = StudySpec(
        name="partial-recovery",
        objective=ObjectiveSpec("score", "maximize"),
        constraints=(),
        budget=BudgetSpec(1.0, "run"),
        noise=NoiseSpec(),
        backend="function_network_partial",
        seed=17,
    )
    space = SearchSpace((CategoricalParameter("model.choice", ("base",)),))
    backend = _PartialComponentBackend(spec, space)
    ledger = ObservationLedger(tmp_path / "observations.jsonl")
    first = OptimizationStudy(spec, space, backend, ledger, _partial_evaluator, tmp_path)
    action = first.ask()[0]
    result = _partial_evaluator(action)
    pending_path = tmp_path / "pending-actions.json"
    if boundary in {"after_result", "after_ledger"}:
        pending = json.loads(pending_path.read_text())
        pending["result"] = result.to_dict()
        pending_path.write_text(canonical_json(pending) + "\n", encoding="utf-8")
    if boundary == "after_ledger":
        ledger.append(action, result)
    _abandon(first)

    resumed = OptimizationStudy(
        spec,
        space,
        _PartialComponentBackend(spec, space),
        ledger,
        _partial_evaluator,
        tmp_path,
    )

    entries = resumed.ledger.entries()
    assert len(entries) == 1
    assert entries[0][0] == action
    expected_status = "infrastructure_failure" if boundary == "before_evaluation" else "success"
    assert entries[0][1].status.value == expected_status
    assert not pending_path.exists()


def test_partial_component_action_recovers_before_manifest_replacement(
    tmp_path, monkeypatch
):
    from autoengineering.optimization import provenance

    spec = StudySpec(
        name="partial-recovery-write",
        objective=ObjectiveSpec("score", "maximize"),
        constraints=(),
        budget=BudgetSpec(1.0, "run"),
        noise=NoiseSpec(),
        backend="function_network_partial",
        seed=17,
    )
    space = SearchSpace((CategoricalParameter("model.choice", ("base",)),))
    ledger = ObservationLedger(tmp_path / "observations.jsonl")
    first = OptimizationStudy(
        spec, space, _PartialComponentBackend(spec, space), ledger, _partial_evaluator, tmp_path
    )
    action = first.ask()[0]
    original = provenance.atomic_write_json

    def interrupt(directory, name, value):
        if name == "recommendation.json":
            raise OSError("simulated partial manifest interruption")
        return original(directory, name, value)

    monkeypatch.setattr(provenance, "atomic_write_json", interrupt)
    with pytest.raises(OSError, match="partial manifest interruption"):
        first.tell(action, _partial_evaluator(action))
    _abandon(first)
    monkeypatch.setattr(provenance, "atomic_write_json", original)

    resumed = OptimizationStudy(
        spec,
        space,
        _PartialComponentBackend(spec, space),
        ledger,
        _partial_evaluator,
        tmp_path,
    )
    assert len(resumed.ledger.entries()) == 1
    assert not (tmp_path / "pending-actions.json").exists()


def test_nonexact_pending_ledger_extension_fails_without_changes(tmp_path, spec, space):
    first = _study(tmp_path, spec, space)
    action = first.ask()[0]
    pending_path = tmp_path / "pending-actions.json"
    pending = json.loads(pending_path.read_text())
    pending["result"] = _evaluator(action).to_dict()
    pending_path.write_text(canonical_json(pending) + "\n", encoding="utf-8")
    other = EvaluationAction.system("eval-000001", {"model": "b"})
    first.ledger.append(other, _evaluator(other))
    _abandon(first)
    before = _snapshot(tmp_path)

    with pytest.raises(StudyRecoveryError, match="exact transition"):
        _study(tmp_path, spec, space)

    assert _snapshot(tmp_path) == before


def test_pending_start_timestamp_mismatch_fails_without_repair(tmp_path, spec, space):
    first = _study(tmp_path, spec, space)
    first.ask()
    pending_path = tmp_path / "pending-actions.json"
    pending = json.loads(pending_path.read_text())
    pending["original_start_timestamp"] = "2000-01-01T00:00:00Z"
    pending_path.write_text(canonical_json(pending) + "\n", encoding="utf-8")
    _abandon(first)
    before = _snapshot(tmp_path)

    with pytest.raises(StudyRecoveryError, match="start timestamp"):
        _study(tmp_path, spec, space)

    assert _snapshot(tmp_path) == before


@pytest.mark.parametrize("mutation", ("invalid_config", "valid_rogue_action"))
def test_pending_action_is_replayed_and_validated_before_recovery_mutates_state(
    tmp_path, spec, space, mutation
):
    first = _study(tmp_path, spec, space)
    action = first.ask()[0]
    pending_path = tmp_path / "pending-actions.json"
    pending = json.loads(pending_path.read_text())
    if mutation == "invalid_config":
        pending["action"]["config"] = {"model": "outside-space"}
    else:
        replacement = next(
            value for value in ("a", "b", "c", "d") if value != action.config["model"]
        )
        pending["action"]["config"] = {"model": replacement}
    pending_path.write_text(canonical_json(pending) + "\n", encoding="utf-8")
    _abandon(first)
    before = _snapshot(tmp_path)

    with pytest.raises(StudyRecoveryError, match="pending action"):
        _study(tmp_path, spec, space)

    assert _snapshot(tmp_path) == before


@pytest.mark.parametrize(
    "failure_name",
    ("recommendation.json", "optimization-report.md", "manifest.json"),
)
def test_crash_during_replaceable_writes_is_repaired_from_pending_transition(
    tmp_path, spec, space, monkeypatch, failure_name
):
    from autoengineering.optimization import provenance

    first = _study(tmp_path, spec, space)
    action = first.ask()[0]
    original_json_write = provenance.atomic_write_json
    original_text_write = provenance.atomic_write_text

    def interrupted_json_write(directory, name, value):
        if name == failure_name:
            raise OSError("simulated artifact interruption")
        return original_json_write(directory, name, value)

    def interrupted_text_write(directory, name, value):
        if name == failure_name:
            raise OSError("simulated artifact interruption")
        return original_text_write(directory, name, value)

    monkeypatch.setattr(provenance, "atomic_write_json", interrupted_json_write)
    monkeypatch.setattr(provenance, "atomic_write_text", interrupted_text_write)
    with pytest.raises(OSError, match="artifact interruption"):
        first.tell(action, _evaluator(action))
    _abandon(first)
    monkeypatch.setattr(provenance, "atomic_write_json", original_json_write)
    monkeypatch.setattr(provenance, "atomic_write_text", original_text_write)

    resumed = _study(tmp_path, spec, space)

    assert len(resumed.ledger.entries()) == 1
    assert not (tmp_path / "pending-actions.json").exists()
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    assert manifest["evaluation_count"] == 1


def test_pending_residue_after_manifest_commit_is_removed_once(tmp_path, spec, space, monkeypatch):
    import autoengineering.optimization.controller as controller

    first = _study(tmp_path, spec, space)
    action = first.ask()[0]
    original_remove = controller.remove_artifact

    def fail_pending_remove(directory, name):
        if name == "pending-actions.json":
            raise OSError("simulated cleanup interruption")
        return original_remove(directory, name)

    monkeypatch.setattr(controller, "remove_artifact", fail_pending_remove)
    with pytest.raises(OSError, match="cleanup interruption"):
        first.tell(action, _evaluator(action))
    _abandon(first)
    monkeypatch.setattr(controller, "remove_artifact", original_remove)

    before_ledger = (tmp_path / "observations.jsonl").read_bytes()
    resumed = _study(tmp_path, spec, space)

    assert len(resumed.ledger.entries()) == 1
    assert resumed.ledger.path.read_bytes() == before_ledger
    assert not (tmp_path / "pending-actions.json").exists()


def test_clean_resume_preserves_ledger_identity_recommendation_and_artifact_bytes(
    tmp_path, spec, space
):
    first = _study(tmp_path, spec, space)
    first.run(max_new_evaluations=2)
    before = _snapshot(tmp_path)
    recommendation = first.recommend()

    resumed = _study(
        tmp_path,
        spec,
        space,
        wall_clock=lambda: "2030-01-01T00:00:00Z",
    )

    assert _snapshot(tmp_path) == before
    assert resumed.recommend() == recommendation
    assert resumed.start_timestamp == first.start_timestamp


def test_clean_resume_in_a_fresh_process_preserves_canonical_artifact_bytes(tmp_path, spec, space):
    first = _study(tmp_path, spec, space)
    first.run(max_new_evaluations=2)
    before = _snapshot(tmp_path)
    program = "\n".join(
        (
            "from pathlib import Path",
            "from autoengineering.optimization import BudgetSpec, CategoricalParameter, NoiseSpec, ObjectiveSpec, ObservationLedger, SearchSpace, SobolBackend, StudySpec",
            "from autoengineering.optimization.controller import OptimizationStudy",
            f"directory = Path({str(tmp_path)!r})",
            "spec = StudySpec('recovery', ObjectiveSpec('score', 'maximize'), (), BudgetSpec(4.0, 'run', initial_cost_estimate=1.0), NoiseSpec(), 'system', 17)",
            "space = SearchSpace((CategoricalParameter('model', ('a', 'b', 'c', 'd')),))",
            "ledger = ObservationLedger(directory / 'observations.jsonl')",
            "backend = SobolBackend(spec, space)",
            "def evaluator(action):",
            "    raise AssertionError('clean resume must not evaluate')",
            "study = OptimizationStudy(spec, space, backend, ledger, evaluator, directory, wall_clock=lambda: '2030-01-01T00:00:00Z', input_artifact_hashes={'system.yaml': 'a' * 64})",
            "print(study.recommend().action_id)",
        )
    )

    completed = subprocess.run(
        [sys.executable, "-c", program],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert _snapshot(tmp_path) == before


def test_terminal_end_timestamp_is_preserved_on_resume(tmp_path, spec, space):
    terminal_spec = replace(spec, budget=replace(spec.budget, max_evaluations=1))
    clock_values = iter(("2026-09-04T12:00:00Z", "2026-09-04T12:10:00Z"))
    first = _study(tmp_path, terminal_spec, space, wall_clock=lambda: next(clock_values))
    first.run()
    before = _snapshot(tmp_path)
    end_timestamp = json.loads((tmp_path / "manifest.json").read_text())["end_timestamp"]

    resumed = _study(
        tmp_path,
        terminal_spec,
        space,
        wall_clock=lambda: "2030-01-01T00:00:00Z",
    )

    assert resumed.stop_reason == "max_evaluations"
    assert json.loads((tmp_path / "manifest.json").read_text())["end_timestamp"] == end_timestamp
    assert _snapshot(tmp_path) == before


def test_terminal_target_state_is_sticky_when_resumed_without_target_configuration(
    tmp_path, spec, space
):
    first = _study(tmp_path, spec, space, target_value=0.0)
    first.run()
    before = _snapshot(tmp_path)
    evaluation_count = len(first.ledger.entries())

    resumed = _study(tmp_path, spec, space)
    recommendation = resumed.run(max_new_evaluations=1)

    assert resumed.stop_reason == "target_attained"
    assert len(resumed.ledger.entries()) == evaluation_count
    assert recommendation == first.recommend()
    assert _snapshot(tmp_path) == before


def test_terminal_metadata_commit_recovers_after_manifest_write_interruption(
    tmp_path, spec, space, monkeypatch
):
    from autoengineering.optimization import provenance

    terminal_spec = replace(spec, budget=replace(spec.budget, max_evaluations=1))
    first = _study(tmp_path, terminal_spec, space)
    original_json_write = provenance.atomic_write_json

    def interrupted_terminal_manifest(directory, name, value):
        if name == "manifest.json" and value["stop_reason"] is not None:
            raise OSError("simulated terminal manifest interruption")
        return original_json_write(directory, name, value)

    monkeypatch.setattr(provenance, "atomic_write_json", interrupted_terminal_manifest)
    with pytest.raises(OSError, match="terminal manifest interruption"):
        first.run()
    monkeypatch.setattr(provenance, "atomic_write_json", original_json_write)

    assert (tmp_path / "pending-control.json").is_file()
    resumed = _study(tmp_path, terminal_spec, space)

    manifest = json.loads((tmp_path / "manifest.json").read_text())
    assert resumed.stop_reason == "max_evaluations"
    assert manifest["stop_reason"] == "max_evaluations"
    assert manifest["end_timestamp"] is not None
    assert manifest["evaluation_count"] == 1
    assert not (tmp_path / "pending-control.json").exists()


def test_terminal_control_residue_after_manifest_commit_is_removed_once(
    tmp_path, spec, space, monkeypatch
):
    import autoengineering.optimization.controller as controller

    terminal_spec = replace(spec, budget=replace(spec.budget, max_evaluations=1))
    first = _study(tmp_path, terminal_spec, space)
    original_remove = controller.remove_artifact

    def fail_control_remove(directory, name):
        if name == "pending-control.json":
            raise OSError("simulated control cleanup interruption")
        return original_remove(directory, name)

    monkeypatch.setattr(controller, "remove_artifact", fail_control_remove)
    with pytest.raises(OSError, match="control cleanup interruption"):
        first.run()
    monkeypatch.setattr(controller, "remove_artifact", original_remove)
    before_manifest = (tmp_path / "manifest.json").read_bytes()

    resumed = _study(tmp_path, terminal_spec, space)

    assert resumed.stop_reason == "max_evaluations"
    assert (tmp_path / "manifest.json").read_bytes() == before_manifest
    assert not (tmp_path / "pending-control.json").exists()


def test_pending_terminal_reason_must_replay_from_committed_state(tmp_path, spec, space):
    study = _study(tmp_path, spec, space)
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    identity = manifest["run_identity"]
    pending = {
        "schema_version": "2.0",
        "run_identity_sha256": manifest["run_identity_sha256"],
        "committed_ledger_sha256": identity["ledger"]["committed_sha256"],
        "original_start_timestamp": identity["start_timestamp"],
        "stop_reason": "max_cost",
        "end_timestamp": "2026-09-04T12:10:00Z",
    }
    (tmp_path / "pending-control.json").write_text(canonical_json(pending) + "\n", encoding="utf-8")
    before = _snapshot(tmp_path)

    with pytest.raises(StudyRecoveryError, match="control reason"):
        _study(tmp_path, spec, space)

    assert study.ledger.entries() == ()
    assert _snapshot(tmp_path) == before
