"""The bounded auto-research loop: hypothesize -> swap -> run -> measure -> decide.

This is the package-native form of feynman's ``/autoresearch`` loop (see the repo
``NOTICE``), specialized to the autoengineering workflow. Where feynman runs an
arbitrary benchmark command, ``auto_improve`` runs the model chain and scores it
with the package's own ``validate_arrays`` / ``rank_opportunities``.

The loop is deliberately deterministic and LLM-free. The *creative* step — deciding
which candidate models to try — happens upstream in deep research and arrives as a
list of :class:`~autoengineering.research.candidates.Candidate` specs. The loop's
job is to test them honestly and keep an auditable record:

    for each candidate:
        swap it onto the current best system   (baseline stays immutable)
        run the chain to get simulated arrays   (execution)
        validate against observed               (validate_arrays)
        score the whole system                  (rank_opportunities)
        record a child node in the tree         (experiment tree)
        keep it if it improved, else revert     (decide)

It is *bounded*: it stops at ``max_iterations`` or when a satisficing ``target`` is
met, matching feynman's bounded-loop discipline. Artifacts (``autoresearch.md``,
``autoresearch.jsonl``, a ``CHANGELOG.md`` entry) use feynman's names for continuity.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

import numpy as np

from autoengineering.execute.swap import swap_component
from autoengineering.research.candidates import Candidate
from autoengineering.research.experiment import ExperimentNode, ExperimentTree
from autoengineering.system.graph import System
from autoengineering.validate.compare import ValidationResult, validate_arrays

# run_chain(system) -> {output_name: array}
RunChain = Callable[[System], dict[str, np.ndarray]]


def _fitness(results: list[ValidationResult]) -> float:
    """Higher-is-better fitness used for the keep/revert decision.

    The keep/revert decision must track the actual goodness of fit directly.
    ``rank_opportunities`` answers a different question (cross-component
    improvement *potential*) and is deliberately flat wherever fit is already
    adequate — its skill shortfall contributes 0 for any NSE/KGE >= 0.5 — so it
    cannot discriminate two good variants. Reading skill straight from the metrics
    keeps the loop sensitive across the whole range:

    - if any of NSE/KGE/correlation is present, use their mean (higher is better);
    - else fall back to negative RMSE (so smaller error scores higher).
    """
    by_metric = {r.metric: r.value for r in results}
    skills = [by_metric[m] for m in ("nse", "kge", "correlation") if m in by_metric]
    if skills:
        return round(sum(skills) / len(skills), 6)
    if "rmse" in by_metric:
        return round(-abs(by_metric["rmse"]), 6)
    return 0.0


def _metric_dict(results: list[ValidationResult]) -> dict:
    return {r.metric: r.value for r in results}


def _target_met(results: list[ValidationResult], target: dict[str, float]) -> bool:
    """True when every target metric passes (direction-aware, matching validate)."""
    by_metric = {r.metric: r.value for r in results}
    for metric, want in target.items():
        if metric not in by_metric:
            return False
        value = by_metric[metric]
        if metric in ("nse", "kge", "correlation"):
            if value < want:
                return False
        else:
            if abs(value) > want:
                return False
    return True


def auto_improve(
    system: System,
    run_chain: RunChain,
    observed: np.ndarray,
    *,
    validate_output: str,
    candidates: list[Candidate] | None = None,
    metrics: list[str] | None = None,
    thresholds: dict[str, float] | None = None,
    target: dict[str, float] | None = None,
    max_iterations: int = 20,
    workdir: str | Path = "outputs",
    slug: str = "auto-improve",
) -> ExperimentTree:
    """Run the bounded auto-research improvement loop.

    Args:
        system: Baseline system (never mutated; stays the immutable tree root).
        run_chain: Callable that executes a system and returns named output arrays.
            Build one with :func:`autoengineering.research.runner.build_feedforward_runner`
            or hand-write it (as the examples do).
        observed: Observed/baseline array to validate the terminal output against.
        validate_output: Key into ``run_chain``'s output dict to score (e.g.
            ``"routing.streamflow"`` or ``"streamflow"``).
        candidates: Replacement specs from deep research. Each is tried once, in
            order, swapped onto the current best system. If ``None`` or empty, only
            the baseline is evaluated.
        metrics: Metrics passed to ``validate_arrays`` (defaults to all).
        thresholds: Pass/fail thresholds passed to ``validate_arrays``.
        target: Optional satisficing stop, e.g. ``{"nse": 0.5}``. When met, the
            loop stops early.
        max_iterations: Upper bound on candidates evaluated (bounded loop).
        workdir: Directory for ``autoresearch.md`` / ``autoresearch.jsonl`` / CHANGELOG.
        slug: Short label used in artifact headers.

    Returns:
        The :class:`ExperimentTree`, root = baseline, children = evaluated candidates.
    """
    metrics = metrics or ["rmse", "bias", "nse", "kge"]
    thresholds = thresholds or {}
    candidates = list(candidates or [])
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)

    # --- Baseline (immutable root) ---
    base_out = run_chain(system)
    base_sim = _resolve_output(base_out, validate_output)
    base_results = validate_arrays(
        validate_output, observed, base_sim, metrics=metrics, thresholds=thresholds
    )
    tree = ExperimentTree(
        ExperimentNode(
            id="baseline",
            parent_id=None,
            component="",
            candidate="baseline",
            description=f"Baseline system '{system.name}'",
            results=base_results,
            score=_fitness(base_results),
            status="baseline",
            metrics=_metric_dict(base_results),
        )
    )
    # Map tree node id -> the System that produced it, so we can swap onto the best.
    systems: dict[str, System] = {"baseline": system}

    log: list[str] = [
        f"# Auto-research: {slug}",
        "",
        f"Baseline `{validate_output}`: "
        + ", ".join(f"{r.metric}={r.value:.4f}" for r in base_results),
        "",
    ]

    if target and _target_met(base_results, target):
        log.append("Baseline already meets target; no candidates evaluated.")
    else:
        n = min(len(candidates), max_iterations)
        for i, cand in enumerate(candidates[:n], 1):
            parent = tree.best()  # grow down from the current winner
            parent_system = systems[parent.id]
            node_id = tree.new_id()

            try:
                trial_system = swap_component(
                    parent_system, cand.name, cand.to_component()
                )
                trial_out = run_chain(trial_system)
                trial_sim = _resolve_output(trial_out, validate_output)
                trial_results = validate_arrays(
                    validate_output,
                    observed,
                    trial_sim,
                    metrics=metrics,
                    thresholds=thresholds,
                )
            except Exception as exc:  # a bad candidate must not kill the loop
                tree.add_child(
                    parent.id,
                    ExperimentNode(
                        id=node_id,
                        component=cand.name,
                        candidate=cand.name,
                        description=cand.description,
                        status="failed",
                        sources=list(cand.sources),
                        notes=f"{type(exc).__name__}: {exc}",
                    ),
                )
                log.append(
                    f"## Iter {i}: {cand.name} — FAILED ({type(exc).__name__}: {exc})"
                )
                log.append("")
                continue

            score = _fitness(trial_results)
            improved = score > parent.score
            status = "kept" if improved else "reverted"
            node = ExperimentNode(
                id=node_id,
                component=cand.name,
                candidate=cand.name,
                description=cand.description,
                results=trial_results,
                score=score,
                status=status,
                metrics=_metric_dict(trial_results),
                sources=list(cand.sources),
                notes=cand.rationale,
            )
            tree.add_child(parent.id, node)
            systems[node_id] = trial_system

            log.append(
                f"## Iter {i}: swap `{cand.name}` (from `{parent.candidate}`)"
            )
            log.append(
                "Result: "
                + ", ".join(f"{r.metric}={r.value:.4f}" for r in trial_results)
            )
            log.append(
                f"Fitness {score:.4f} vs parent {parent.score:.4f} -> "
                f"**{status.upper()}**"
            )
            if cand.rationale:
                log.append(f"Rationale: {cand.rationale}")
            log.append("")

            if target and _target_met(trial_results, target):
                log.append(f"Target {target} met at iteration {i}; stopping early.")
                log.append("")
                break

    # --- Persist artifacts (feynman-compatible names) ---
    best = tree.best()
    log.append("---")
    log.append(
        f"Best: `{best.candidate}` (score {best.score:.4f}) — "
        + ", ".join(f"{k}={_metric_fmt(v)}" for k, v in best.metrics.items())
    )
    (workdir / "autoresearch.md").write_text("\n".join(log) + "\n")
    tree.to_jsonl(workdir / "autoresearch.jsonl")
    _append_changelog(workdir, slug, tree, validate_output)

    return tree


def _resolve_output(out: dict[str, np.ndarray], key: str) -> np.ndarray:
    if key in out:
        return np.asarray(out[key])
    # Allow a bare port name when run_chain keyed by "<component>.<port>".
    for k, v in out.items():
        if k.split(".", 1)[-1] == key:
            return np.asarray(v)
    raise KeyError(
        f"run_chain output has no key '{key}'. Available: {sorted(out)[:12]}"
    )


def _metric_fmt(v) -> str:
    try:
        return f"{float(v):.4f}"
    except (TypeError, ValueError):
        return str(v)


def _append_changelog(
    workdir: Path, slug: str, tree: ExperimentTree, output: str
) -> None:
    baseline = tree.nodes[tree.root_id]
    best = tree.best()
    kept = [n for n in tree.nodes.values() if n.status == "kept"]
    changelog = workdir / "CHANGELOG.md"
    entry = [
        f"## auto-research: {slug}",
        "",
        f"- Output scored: `{output}`",
        f"- Iterations: {len(tree.nodes) - 1}",
        f"- Kept swaps: {len(kept)} "
        + (f"({', '.join(n.candidate for n in kept)})" if kept else ""),
        f"- Baseline fitness: {baseline.score:.4f} -> best: {best.score:.4f}",
        "",
    ]
    existing = changelog.read_text() if changelog.exists() else ""
    changelog.write_text("\n".join(entry) + "\n" + existing)
