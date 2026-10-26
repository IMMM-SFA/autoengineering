"""Failure injection for the Part 1 sketch. Numerical fixtures use no real data."""

from __future__ import annotations

import json

import numpy as np
import pytest

from examples.agentic_architecture_pilot import control, science


@pytest.fixture
def fixture_evaluator(monkeypatch):
    calls = []
    monkeypatch.setattr(
        control,
        "identity",
        lambda: {"source": "a" * 64, "examples/leaf_river/models/routing_calibrated.py": "b" * 64},
    )

    def evaluate(directory, hashes):
        calls.append(directory)
        return dict(decision="retain_triangular", scope="fixture", total_executions=38)

    monkeypatch.setattr(control, "evaluate_choices", evaluate)
    return calls


def submitted(directory):
    for message in list(control.scripted_messages())[:2]:
        control.request(directory, message)


def evaluation():
    return dict(id="evaluate", tool="evaluate", payload={})


def test_transitions_and_duplicate_result_do_not_evaluate_twice(tmp_path, fixture_evaluator):
    with pytest.raises(control.ProtocolError, match="illegal workflow"):
        control.request(tmp_path, evaluation())
    first = control.replay(tmp_path)
    assert control.request(tmp_path, evaluation()) == first
    assert len(fixture_evaluator) == 1
    assert (
        control.request(tmp_path, dict(id="s", tool="state", payload={}))["next_tool"] == "complete"
    )


@pytest.mark.parametrize(
    "message",
    [
        None,
        {},
        dict(id="../x", tool="submit", payload={}),
        dict(id="x", tool=[], payload={}),
        dict(id="x", tool="submit", payload={"candidate": "own-code"}),
        dict(id="x", tool="evaluate", payload={"acceptance": "bypass"}),
    ],
)
def test_malformed_and_untrusted_requests_rejected(tmp_path, fixture_evaluator, message):
    with pytest.raises(control.ProtocolError):
        control.request(tmp_path, message)
    assert not fixture_evaluator


def test_result_before_ack_recovers_without_extra_cost(tmp_path, fixture_evaluator):
    submitted(tmp_path)
    with pytest.raises(RuntimeError, match="result-before-ack"):
        control.request(tmp_path, evaluation(), fault="after_evaluation")
    assert control.request(tmp_path, evaluation())["decision"] == "retain_triangular"
    assert len(fixture_evaluator) == 1
    state = json.loads((tmp_path / "state.json").read_text())
    assert state["reserved_executions"] == 40 and state["step"] == 3


def test_uncertain_execution_keeps_reservation(tmp_path, fixture_evaluator):
    submitted(tmp_path)
    with pytest.raises(RuntimeError, match="uncertain execution"):
        control.request(tmp_path, evaluation(), fault="before_evaluation")
    with pytest.raises(control.ProtocolError, match="uncertain execution"):
        control.request(tmp_path, evaluation())
    assert not fixture_evaluator
    assert json.loads((tmp_path / "state.json").read_text())["reserved_executions"] == 40


def test_worker_disappearance_resumes_from_admitted_candidate(tmp_path, fixture_evaluator):
    submitted(tmp_path)
    assert (
        control.request(tmp_path, dict(id="s", tool="state", payload={}))["next_tool"] == "evaluate"
    )
    control.replay(tmp_path)
    assert len(fixture_evaluator) == 1


def test_changed_identity_refused(tmp_path, fixture_evaluator, monkeypatch):
    submitted(tmp_path)
    monkeypatch.setattr(control, "identity", lambda: {"source": "c" * 64})
    with pytest.raises(control.ProtocolError, match="identity changed"):
        control.request(tmp_path, evaluation())
    assert not fixture_evaluator


def test_cancellation_and_conflicting_request_id(tmp_path, fixture_evaluator):
    control.request(tmp_path, dict(id="x", tool="cancel", payload={}))
    with pytest.raises(control.ProtocolError, match="cancelled"):
        control.request(tmp_path, dict(id="d", tool="diagnose", payload={}))
    with pytest.raises(control.ProtocolError, match="identity reused"):
        control.request(tmp_path, dict(id="x", tool="diagnose", payload={}))
    assert not fixture_evaluator


@pytest.mark.parametrize(
    "field,value,message",
    [
        ("reserved_executions", 1, "execution budget"),
        ("tool_calls", 12, "request budget"),
        ("started", 0, "time budget"),
    ],
)
def test_budget_exhaustion(tmp_path, fixture_evaluator, field, value, message):
    submitted(tmp_path)
    path = tmp_path / "state.json"
    state = json.loads(path.read_text())
    state[field] = value
    science.write_json(path, state)
    with pytest.raises(control.ProtocolError, match=message):
        control.request(tmp_path, evaluation())
    assert not fixture_evaluator


def test_concurrent_writer_refused(tmp_path, fixture_evaluator):
    with control.writer(tmp_path):
        with pytest.raises(control.ProtocolError, match="another writer"):
            control.request(tmp_path, dict(id="d", tool="diagnose", payload={}))


def test_unsupported_conclusion_is_rejected(tmp_path, fixture_evaluator):
    submitted(tmp_path)
    control.request(tmp_path, evaluation())
    with pytest.raises(control.ProtocolError, match="unsupported conclusion"):
        control.request(
            tmp_path, dict(id="review", tool="review", payload={"decision": "retain_gamma"})
        )


@pytest.mark.parametrize("output", [np.zeros(5), np.full(6, np.nan), np.full(6, -1), np.zeros(6)])
def test_bad_or_attractive_nonphysical_arrays_fail(output):
    arrays = dict(runoff=np.ones(6), recharge=np.ones(6))
    assert not all(science.checks(output, "triangular", {}, arrays).values())


def test_metrics_reconstructed_independently_match_package():
    from autoengineering.validate.compare import rmse, nse, kge, bias

    pred = np.array([1.0, 3.0, 2.0, 5.0])
    obs = np.array([2.0, 2.0, 3.0, 4.0])
    for name, fn in dict(rmse=rmse, nse=nse, kge=kge, bias=bias).items():
        assert science.metrics(pred, obs)[name] == pytest.approx(fn(obs, pred))


def test_default_then_sobol_is_durable_and_budgeted(tmp_path, monkeypatch):
    from autoengineering.optimization import (
        BudgetSpec,
        ContinuousParameter,
        EvaluationResult,
        NoiseSpec,
        ObjectiveSpec,
        ObservationLedger,
        OptimizationStudy,
        SearchSpace,
        StudySpec,
    )

    monkeypatch.setattr(science, "task", lambda: {"families": {"fixture": {"default": {"x": 0.5}}}})
    space = SearchSpace((ContinuousParameter("x", 0.0, 1.0),))
    spec = StudySpec(
        "test-fixture",
        ObjectiveSpec("score", "minimize"),
        (),
        BudgetSpec(max_cost=4, cost_unit="attempt", max_evaluations=4),
        NoiseSpec(),
        "system",
        17,
    )
    calls = []

    def evaluator(action):
        calls.append(action.id)
        return EvaluationResult.success(
            action.id, {"score": float(action.config["x"])}, {}, 1.0, "attempt"
        )

    def controller():
        return OptimizationStudy(
            spec,
            space,
            science.DefaultThenSobol(spec, space),
            ObservationLedger(tmp_path / "ledger.jsonl"),
            evaluator,
            tmp_path,
        )

    controller().run(max_new_evaluations=2)
    controller().run()
    ledger = ObservationLedger(tmp_path / "ledger.jsonl")
    assert len(calls) == len(ledger.entries()) == 4
    assert dict(ledger.entries()[0][0].config) == {"x": 0.5}
    controller().run()
    assert len(calls) == 4
