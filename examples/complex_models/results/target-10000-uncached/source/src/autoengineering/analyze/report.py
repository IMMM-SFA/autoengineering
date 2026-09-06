"""Report generation for system analysis."""

from __future__ import annotations

import json
from datetime import datetime

from autoengineering.analyze.metrics import rank_opportunities
from autoengineering.system.graph import System
from autoengineering.validate.compare import ValidationResult


def generate_report(
    system: System,
    validation_results: list[ValidationResult],
    format: str = "markdown",
) -> str:
    """Generate a system analysis report.

    Args:
        system: The system being analyzed.
        validation_results: Validation results for all components.
        format: Output format — "markdown" or "json".

    Returns:
        Report as a string.
    """
    if format == "json":
        return _generate_json_report(system, validation_results)
    return _generate_markdown_report(system, validation_results)


def _generate_markdown_report(
    system: System, validation_results: list[ValidationResult]
) -> str:
    lines = []
    lines.append(f"# Autoengineering Report: {system.name}")
    lines.append(f"\n*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n")

    # System overview
    lines.append("## System Overview\n")
    lines.append(f"- **Components**: {len(system.component_names)}")
    lines.append(f"- **Connections**: {len(system.connections)}")
    try:
        order = system.topological_order()
        lines.append(f"- **Execution order**: {' → '.join(order)}")
    except Exception:
        pass
    lines.append("")

    # Diagram
    lines.append("## System Diagram\n")
    lines.append(system.to_mermaid())
    lines.append("")

    # Validation results by component
    lines.append("## Validation Results\n")
    by_component: dict[str, list[ValidationResult]] = {}
    for r in validation_results:
        by_component.setdefault(r.component, []).append(r)

    for comp_name, results in by_component.items():
        lines.append(f"### {comp_name}\n")
        for r in results:
            lines.append(f"- {r.to_markdown()}")
        lines.append("")

    # Improvement opportunities
    ranked = rank_opportunities(validation_results)
    if ranked:
        lines.append("## Improvement Opportunities\n")
        lines.append("Components ranked by improvement potential:\n")
        for i, opp in enumerate(ranked, 1):
            lines.append(
                f"{i}. **{opp['component']}** (score: {opp['score']}) — {opp['summary']}"
            )
        lines.append("")

        # Recommendation
        top = ranked[0]
        if top["score"] > 0:
            lines.append("## Recommendation\n")
            lines.append(
                f"**Priority target**: `{top['component']}` has the highest improvement "
                f"potential (score: {top['score']}). {top['summary']}."
            )
            lines.append("")
            lines.append(
                "Consider reviewing this component's implementation and testing "
                "alternative approaches."
            )

    return "\n".join(lines)


def _generate_json_report(
    system: System, validation_results: list[ValidationResult]
) -> str:
    ranked = rank_opportunities(validation_results)
    report = {
        "system": system.name,
        "generated": datetime.now().isoformat(),
        "components": system.component_names,
        "connections": system.connections,
        "validation_results": [r.to_dict() for r in validation_results],
        "opportunities": ranked,
    }
    return json.dumps(report, indent=2)
