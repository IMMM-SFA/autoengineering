"""Normalized provider usage remains distinct from totals and billed money."""

import csv
import io
import json

import pytest

from autoengineering.agents.hosts.claude import parse_result
from autoengineering.agents.hosts.codex import parse_events
from autoengineering.utility.costs import join_batch_costs
from autoengineering.utility.report import accounting_report, render_markdown
from autoengineering.utility.reporting import report_files
from test_agent_batch import initialized, reservation, observed, finish
from test_agent_claude import encoded, MODEL
from test_utility_controller import prepared

MAPPING = {"first": "1" * 64, "second": "2" * 64}


def saved_usage(tmp_path, usage):
    child = initialized(tmp_path)
    r = reservation()
    child.reserve(r)
    child.observe(observed(child, r, usage=usage))
    return child


def quantities(child):
    return {r.resource: r.quantity for r in join_batch_costs(child, MAPPING)}


def codex_usage():
    raw = b"\n".join(
        json.dumps(event).encode()
        for event in (
            {"type": "item.completed", "item": {"type": "agent_message", "text": "authored"}},
            {
                "type": "turn.completed",
                "usage": {
                    "input_tokens": 10,
                    "cached_input_tokens": 4,
                    "output_tokens": 8,
                    "reasoning_output_tokens": 3,
                },
            },
        )
    )
    return parse_events(raw)[2]


def test_codex_cache_and_reasoning_are_not_dropped_or_added_to_totals(tmp_path):
    child = saved_usage(tmp_path, codex_usage())
    q = quantities(child)
    assert q["provider_input_tokens"] == 10
    assert q["provider_cached_input_tokens"] == 4
    assert q["provider_output_tokens"] == 8
    assert q["provider_reasoning_output_tokens"] == 3
    assert q["provider_total_tokens"] == 18
    # The adapter did not declare these fields. No subtraction or implicit zero.
    assert q["provider_uncached_input_tokens"] is None
    assert q["provider_cache_creation_input_tokens"] is None
    assert q["provider_spend"] is None


def test_claude_uses_normalized_whole_call_breakdown_not_top_level(tmp_path):
    result = parse_result(
        encoded(
            modelUsage={
                MODEL: {
                    "inputTokens": 5,
                    "cacheReadInputTokens": 2,
                    "cacheCreationInputTokens": 3,
                    "outputTokens": 4,
                },
                "claude-fixture-2": {
                    "inputTokens": 7,
                    "cacheReadInputTokens": 11,
                    "cacheCreationInputTokens": 13,
                    "outputTokens": 17,
                },
            }
        )
    )
    assert result.top_level_usage["total_tokens"] == 14
    child = saved_usage(tmp_path, result.usage)
    q = quantities(child)
    assert q["provider_uncached_input_tokens"] == 12
    assert q["provider_cached_input_tokens"] == 13
    assert q["provider_cache_creation_input_tokens"] == 16
    assert q["provider_input_tokens"] == 41
    assert q["provider_output_tokens"] == 21
    assert q["provider_total_tokens"] == 62
    assert q["provider_reasoning_output_tokens"] is None
    assert result.estimated_cost_usd == 0.01 and q["provider_spend"] is None


@pytest.mark.parametrize("mode", ["partial", "crash", "legacy"])
def test_incomplete_and_crash_work_does_not_acquire_zero_components(tmp_path, mode):
    if mode == "partial":
        usage = parse_result(encoded(modelUsage={MODEL: {"inputTokens": 5}})).usage
    elif mode == "crash":
        zero = {
            "inputTokens": 0,
            "cacheReadInputTokens": 0,
            "cacheCreationInputTokens": 0,
            "outputTokens": 0,
        }
        usage = parse_result(
            encoded(subtype="error_during_execution", modelUsage={MODEL: zero})
        ).usage
    else:
        usage = {"input_tokens": 5}
    child = saved_usage(tmp_path, usage)
    q = quantities(child)
    assert q["provider_cached_input_tokens"] is None
    assert q["provider_cache_creation_input_tokens"] is None
    assert q["provider_reasoning_output_tokens"] is None
    assert q["provider_total_tokens"] is None
    assert q["provider_spend"] is None
    if mode == "crash":
        assert all(value is None for key, value in q.items() if key.startswith("provider_"))


def test_pending_host_has_unknown_components_without_new_work(tmp_path, monkeypatch):
    child = initialized(tmp_path)
    child.reserve(reservation())
    before = child.replay()
    monkeypatch.setattr("subprocess.Popen", lambda *_a, **_k: pytest.fail("reader launched"))
    q = quantities(child)
    assert all(value is None for key, value in q.items() if key.startswith("provider_"))
    assert child.replay() == before


def test_suite_accounting_and_csv_preserve_components_and_blank_unknowns(tmp_path, monkeypatch):
    controller, identity, cell, _, _ = prepared(tmp_path)

    def authored_case(child, case):
        r = reservation(at=child.clock())
        child.reserve(r)
        child.observe(observed(child, r, usage=codex_usage()))
        finish(child, id=case)

    controller.dispatch(identity, cell, authored_case)
    before = controller.store.replay()["head"]
    monkeypatch.setattr("subprocess.Popen", lambda *_a, **_k: pytest.fail("reader launched"))
    document = accounting_report(controller.store)
    assert not document["evidence_blockers"]
    assert not document["complete_cost_evidence"]
    assert "Provider token components overlap totals" in render_markdown(document)
    # Exercise the table renderer from real accounting, without claiming a
    # comparative analysis or creating a confirmation barrier for this fixture.
    tables = report_files(
        {
            "suite_digest": controller.store.spec.digest,
            "cells": [{"cell_digest": c.digest} for c in controller.store.spec.cells],
            "analysis": {"contrasts": []},
            "accounting": document,
            "claim_limits": [],
        }
    )
    rows = list(csv.DictReader(io.StringIO(tables["physical-costs.csv"].decode())))
    q = {r["resource"]: r["quantity"] for r in rows}
    assert q["provider_cached_input_tokens"] == "4.0"
    assert q["provider_reasoning_output_tokens"] == "3.0"
    assert q["provider_total_tokens"] == "18.0"
    assert q["provider_uncached_input_tokens"] == q["provider_spend"] == ""
    assert "Do not sum distinct token resources" in tables["summary.md"].decode()
    assert accounting_report(controller.store) == document
    assert controller.store.replay()["head"] == before
