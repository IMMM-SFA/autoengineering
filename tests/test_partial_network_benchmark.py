"""Evidence reconstruction contracts for the Item 9 benchmark."""

import copy
import importlib.util
import json
import math

import pytest

if importlib.util.find_spec("botorch") is not None:
    from autoengineering.benchmarks.partial_network import __main__ as benchmark_main
    from autoengineering.benchmarks.partial_network.problems import benchmark_problems
    from autoengineering.benchmarks.partial_network.runner import (
        PARTIAL_SETTINGS,
        _backend,
        execute_run,
    )
    from autoengineering.benchmarks.partial_network.summary import (
        _audit_records,
        _lineage_audit,
        _terminal_separation,
        component_summary,
        summarize_records,
        value_cost_payload,
    )
    from autoengineering.optimization import ObservationLedger
    from autoengineering.optimization.partial_network_backend import PartialNetworkBayesBackend
    from autoengineering.optimization.partial_network_baselines import (
        CheapestInformativePartialNetworkBackend,
        RandomPartialNetworkBackend,
    )
else:
    benchmark_main = None


@pytest.mark.skipif(benchmark_main is None, reason="optional Bayesian dependencies")
def test_partial_benchmark_problems_match_frozen_analytic_optima():
    chain, branch = benchmark_problems()
    chain_config = {
        "upstream.choice": "base",
        "upstream.x": math.asin(0.8) / math.pi,
        "terminal.choice": "base",
        "terminal.y": 0.3,
    }
    branch_config = {
        "left.choice": "base",
        "left.x": 0.65,
        "right.choice": "base",
        "right.y": 0.5,
        "terminal.choice": "base",
        "terminal.z": 0.25,
    }

    assert chain.analytic(chain_config)["utility"] == pytest.approx(1.0)
    assert chain.feasible(chain.analytic(chain_config))
    assert branch.analytic(branch_config)["utility"] == pytest.approx(1.0)
    assert branch.feasible(branch.analytic(branch_config))
    assert chain.expected_cost(None) == branch.expected_cost(None) == 1.0


@pytest.mark.skipif(benchmark_main is None, reason="optional Bayesian dependencies")
def test_partial_benchmark_configuration_matches_decision_0010(tmp_path):
    expected_settings = {
        "min_initial": 4,
        "min_component_observations": 3,
        "candidate_pool_size": 16,
        "decision_pool_size": 16,
        "posterior_samples": 16,
        "fantasy_samples": 4,
        "fit_retry_limit": 2,
        "max_component_streak": 2,
        "minimum_value_per_cost": 0.0,
        "cost_quantile": 0.9,
    }
    assert PARTIAL_SETTINGS == expected_settings

    problem = benchmark_problems()[0]
    ledger = ObservationLedger(tmp_path / "observations.jsonl")
    ledger.initialize()
    backend_types = {
        "function_network_partial": PartialNetworkBayesBackend,
        "function_network_partial_random": RandomPartialNetworkBackend,
        "function_network_partial_cheapest_informative": (CheapestInformativePartialNetworkBackend),
    }
    for method, backend_type in backend_types.items():
        backend = _backend(problem, method, 97)
        assert type(backend) is backend_type
        assert backend.identity_dict()["constructor"] == {
            **expected_settings,
            "reserve_system_refresh_budget": True,
            "fantasy_sampler": "common_antithetic_normal",
        }
        if method == "function_network_partial":
            assert backend.identity_dict()["candidate_policy"]["score"] == (
                "finite_pool_common_terminal_utility_v1"
            )
        assert len(backend._candidate_pools(ledger).system) == 16

    records = execute_run(problem, "function_network_partial", 97)
    acquisition = next(item for item in records if item["record_type"] == "acquisition")
    assert acquisition["diagnostics"]["backend"] == "function_network_partial"
    assert acquisition["diagnostics"]["details"]["candidate_pool_size"] == 16
    assert acquisition["diagnostics"]["details"]["decision_pool_size"] == 16


@pytest.mark.skipif(benchmark_main is None, reason="optional Bayesian dependencies")
def test_partial_random_run_reconstructs_lineage_cost_and_terminal_separation():
    problem = benchmark_problems()[0]
    records = execute_run(problem, "function_network_partial_random", 0)
    evaluations = [item for item in records if item["record_type"] == "evaluation"]
    row = next(
        item
        for item in summarize_records(records)
        if item["problem"] == problem.name
        and item["method"] == "function_network_partial_random"
        and item["seed"] == 0
    )

    assert row["completed"] is True
    assert row["post_warm_system_count"] >= 1
    assert row["recommendation_is_observed_system"] is True
    assert row["cost_conservative"] is True
    assert all(item["replay_consistent"] for item in evaluations)
    assert _lineage_audit(records)["passed"] is True
    assert _terminal_separation(records)["passed"] is True
    assert any(item["action"]["scope"] == "component" for item in evaluations)
    assert component_summary(records)
    assert value_cost_payload(records)["decisions"]

    changed = copy.deepcopy(records)
    record = next(item for item in changed if item["record_type"] == "evaluation")
    record["normalized_regret"] = 0.123456
    assert _audit_records(changed)["passed"] is False


@pytest.mark.skipif(benchmark_main is None, reason="optional Bayesian dependencies")
def test_partial_benchmark_source_manifest_and_artifacts_are_stable(tmp_path):
    root = benchmark_main.repository_root()
    first = benchmark_main.source_hash(root)
    second = benchmark_main.source_hash(root)
    assert first == second
    assert benchmark_main.source_file_hashes(root)

    records = execute_run(
        benchmark_problems()[0], "function_network_partial_random", 0
    )
    provenance = {
        "decision_sha256": "a" * 64,
        "source_sha256": first,
        "source_file_sha256": benchmark_main.source_file_hashes(root),
    }
    texts, gate = benchmark_main._artifact_texts(records, provenance)
    for name, value in texts.items():
        (tmp_path / name).write_text(value, encoding="utf-8")
    assert json.loads(texts["gate.json"])["passed"] is False
    assert gate["passed"] is False
