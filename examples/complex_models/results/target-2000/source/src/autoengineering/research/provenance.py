"""Evidence-first report + provenance sidecar for an auto-research run.

Combines two ideas credited in the repo ``NOTICE``:

- feynman's *provenance sidecar* — every research output is shipped next to a
  ``<slug>.provenance.md`` recording what was tried, what was accepted or rejected,
  and whether verification passed.
- openresearch-cli's *evidence-first* reporting — lead with the measured evidence
  (the baseline -> best metric table straight from the experiment tree), not with a
  narrative conclusion. Claims come after the numbers that support them.

The report reuses :func:`autoengineering.analyze.report.generate_report` for the
system overview/diagram section so the two report styles stay consistent.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from autoengineering.research.experiment import ExperimentNode, ExperimentTree
from autoengineering.system.graph import System


def _metric_table(baseline: ExperimentNode, best: ExperimentNode) -> list[str]:
    metrics = list(baseline.metrics.keys()) or list(best.metrics.keys())
    lines = [
        "| Metric | Baseline | Best | Δ |",
        "| --- | ---: | ---: | ---: |",
    ]
    for m in metrics:
        b = baseline.metrics.get(m)
        k = best.metrics.get(m)
        delta = ""
        if isinstance(b, (int, float)) and isinstance(k, (int, float)):
            delta = f"{k - b:+.4f}"
        b_s = f"{b:.4f}" if isinstance(b, (int, float)) else str(b)
        k_s = f"{k:.4f}" if isinstance(k, (int, float)) else str(k)
        lines.append(f"| {m} | {b_s} | {k_s} | {delta} |")
    return lines


def write_report(
    tree: ExperimentTree,
    system: System,
    slug: str,
    workdir: str | Path = "outputs",
    *,
    now: str | None = None,
) -> tuple[Path, Path]:
    """Write ``<slug>.report.md`` and ``<slug>.provenance.md``.

    Args:
        tree: The experiment tree from :func:`auto_improve`.
        system: The baseline system (for the overview/diagram section).
        slug: File-name slug.
        workdir: Output directory.
        now: Optional timestamp string (injected for reproducible tests; defaults
            to the current local time).

    Returns:
        ``(report_path, provenance_path)``.
    """
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    stamp = now or datetime.now().strftime("%Y-%m-%d %H:%M")

    baseline = tree.nodes[tree.root_id]
    best = tree.best()
    path = tree.path_to_best()
    kept = [n for n in path if n.status == "kept"]
    reverted = [n for n in tree.nodes.values() if n.status == "reverted"]
    failed = [n for n in tree.nodes.values() if n.status == "failed"]

    # Collect sources from every node on the kept path (deduped, order-preserving).
    sources: list[str] = []
    for n in path:
        for s in n.sources:
            if s not in sources:
                sources.append(s)

    # --- Report (evidence first) ---
    r: list[str] = [f"# Auto-research report: {slug}", "", f"*Generated: {stamp}*", ""]

    r.append("## Evidence\n")
    if best.id == baseline.id:
        r.append("No candidate improved on the baseline. Metrics:\n")
    else:
        r.append(
            f"Best variant **{best.candidate}** improved fitness "
            f"{baseline.score:.4f} -> {best.score:.4f}. Metrics:\n"
        )
    r.extend(_metric_table(baseline, best))
    r.append("")

    r.append("## Experiment tree\n")
    r.append("```")
    r.append(tree.to_markdown())
    r.append("```")
    r.append("")

    r.append("## Changes kept\n")
    if kept:
        for n in kept:
            r.append(f"### `{n.component}` -> {n.candidate}")
            if n.description:
                r.append(n.description)
            if n.notes:
                r.append(f"*Rationale:* {n.notes}")
            r.append(
                "Result: "
                + ", ".join(f"{m}={_fmt(v)}" for m, v in n.metrics.items())
            )
            r.append("")
    else:
        r.append("No swaps improved the baseline; the baseline was retained.\n")

    if reverted:
        r.append("## Changes tried and reverted\n")
        for n in reverted:
            r.append(
                f"- `{n.candidate}` (score {n.score:.4f} did not beat parent)"
            )
        r.append("")

    # System overview reuses the existing report generator's diagram section.
    r.append("## System\n")
    r.append(system.to_mermaid())
    r.append("")

    if sources:
        r.append("## References\n")
        for i, s in enumerate(sources, 1):
            r.append(f"{i}. {s}")
        r.append("")

    report_path = workdir / f"{slug}.report.md"
    report_path.write_text("\n".join(r) + "\n")

    # --- Provenance sidecar (feynman format) ---
    verification = "PASS" if best.id != baseline.id else "PASS WITH NOTES"
    p = [
        f"# Provenance: {slug}",
        "",
        f"- **Date:** {stamp}",
        f"- **Rounds:** {len(tree.nodes) - 1}",
        f"- **Candidates consulted:** {len(tree.nodes) - 1}",
        f"- **Candidates accepted (kept):** {len(kept)}"
        + (f" ({', '.join(n.candidate for n in kept)})" if kept else ""),
        f"- **Candidates rejected (reverted/failed):** "
        f"{len(reverted) + len(failed)}",
        f"- **Sources:** {len(sources)}",
        f"- **Verification:** {verification}",
        f"- **Fitness:** baseline {baseline.score:.4f} -> best {best.score:.4f}",
        "- **Log:** autoresearch.md",
        "- **Structured log:** autoresearch.jsonl",
        "",
    ]
    if failed:
        p.append("### Failed candidates")
        for n in failed:
            p.append(f"- `{n.candidate}`: {n.notes}")
        p.append("")

    provenance_path = workdir / f"{slug}.provenance.md"
    provenance_path.write_text("\n".join(p) + "\n")

    return report_path, provenance_path


def _fmt(v) -> str:
    try:
        return f"{float(v):.4f}"
    except (TypeError, ValueError):
        return str(v)
