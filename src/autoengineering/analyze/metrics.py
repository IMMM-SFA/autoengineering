"""Component-level scoring and opportunity ranking."""

from __future__ import annotations

from autoengineering.validate.compare import ValidationResult


def rank_opportunities(
    validation_results: list[ValidationResult],
) -> list[dict]:
    """Rank components by potential for improvement based on validation results.

    Groups results by component, computes a composite score based on how far
    each metric is from its threshold (or from ideal), and returns a ranked list.

    Returns:
        List of dicts sorted by improvement potential (highest first), each with:
        - component: component name
        - score: composite improvement potential score (0-1, higher = more room)
        - failing_metrics: list of metrics that failed thresholds
        - summary: human-readable summary
    """
    # Group by component
    by_component: dict[str, list[ValidationResult]] = {}
    for r in validation_results:
        by_component.setdefault(r.component, []).append(r)

    ranked = []
    for component, results in by_component.items():
        failing = [r for r in results if r.status == "fail"]
        warnings = [r for r in results if r.status == "warn"]

        # Compute a simple score: fraction of metrics that are failing or warning
        total = len(results)
        if total == 0:
            continue
        fail_score = len(failing) / total
        warn_score = len(warnings) / total * 0.5
        score = min(fail_score + warn_score, 1.0)

        # Also factor in magnitude of RMSE/bias if available
        for r in results:
            if r.metric == "nse" and r.value < 0.5:
                score = max(score, 0.6)
            elif r.metric == "kge" and r.value < 0.5:
                score = max(score, 0.6)

        summary_parts = []
        if failing:
            summary_parts.append(
                f"{len(failing)} failing metric(s): "
                + ", ".join(f"{r.metric}={r.value:.3f}" for r in failing)
            )
        if warnings:
            summary_parts.append(f"{len(warnings)} warning(s)")
        if not summary_parts:
            summary_parts.append("All metrics passing")

        ranked.append(
            {
                "component": component,
                "score": round(score, 3),
                "failing_metrics": [r.metric for r in failing],
                "results": [r.to_dict() for r in results],
                "summary": "; ".join(summary_parts),
            }
        )

    ranked.sort(key=lambda x: x["score"], reverse=True)
    return ranked
