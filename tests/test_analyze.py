"""Tests for the analysis module."""

from autoengineering.analyze.metrics import rank_opportunities
from autoengineering.analyze.report import generate_report
from autoengineering.system.graph import System
from autoengineering.validate.compare import ValidationResult


def _make_system():
    s = System("test")
    s.add_component("a", model_type="generator")
    s.add_component("b", model_type="transform")
    s.connect("a", "b")
    return s


def _make_results():
    return [
        ValidationResult("a", "rmse", 0.05, threshold=0.1, status="pass"),
        ValidationResult("a", "nse", 0.95, threshold=0.7, status="pass"),
        ValidationResult("b", "rmse", 0.5, threshold=0.1, status="fail"),
        ValidationResult("b", "nse", 0.3, threshold=0.7, status="fail"),
    ]


class TestRankOpportunities:
    def test_ranking_order(self):
        results = _make_results()
        ranked = rank_opportunities(results)
        assert ranked[0]["component"] == "b"
        assert ranked[0]["score"] > ranked[1]["score"]

    def test_failing_metrics_listed(self):
        results = _make_results()
        ranked = rank_opportunities(results)
        b_entry = next(r for r in ranked if r["component"] == "b")
        assert "rmse" in b_entry["failing_metrics"]
        assert "nse" in b_entry["failing_metrics"]

    def test_all_passing(self):
        results = [
            ValidationResult("a", "rmse", 0.01, threshold=0.1, status="pass"),
        ]
        ranked = rank_opportunities(results)
        assert ranked[0]["score"] == 0.0


class TestReport:
    def test_markdown_report(self):
        system = _make_system()
        results = _make_results()
        report = generate_report(system, results, format="markdown")
        assert "# Autoengineering Report" in report
        assert "Improvement Opportunities" in report
        assert "b" in report

    def test_json_report(self):
        system = _make_system()
        results = _make_results()
        report = generate_report(system, results, format="json")
        import json

        data = json.loads(report)
        assert data["system"] == "test"
        assert len(data["validation_results"]) == 4
