"""Ecosystem bottleneck & error-propagation triage engine.

Implements Capability 1 (Ecosystem Bottleneck & Error-Propagation Triage) and
Capability 2 (Investment & Emulator ROI Assessment) described in ``VISION.md``.
"""

from __future__ import annotations

import json
import math
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field

import numpy as np

from autoengineering.system.graph import Component, System
from autoengineering.validate.compare import ValidationResult, validate_arrays


@dataclass(frozen=True)
class PerturbationSensitivity:
    """Downstream impact of perturbing a component's output on a terminal metric."""

    component: str
    perturbation: str
    terminal_output: str
    baseline_kge: float
    perturbed_kge: float
    delta_kge: float
    baseline_rmse: float
    perturbed_rmse: float
    delta_rmse: float
    relative_sensitivity: float

    def to_dict(self) -> dict:
        return {
            "component": self.component,
            "perturbation": self.perturbation,
            "terminal_output": self.terminal_output,
            "baseline_kge": round(self.baseline_kge, 6),
            "perturbed_kge": round(self.perturbed_kge, 6),
            "delta_kge": round(self.delta_kge, 6),
            "baseline_rmse": round(self.baseline_rmse, 6),
            "perturbed_rmse": round(self.perturbed_rmse, 6),
            "delta_rmse": round(self.delta_rmse, 6),
            "relative_sensitivity": round(self.relative_sensitivity, 6),
        }


@dataclass(frozen=True)
class EmulatorROI:
    """Break-even and speedup analysis for replacing a component with an AI emulator."""

    upstream_hpc_hours_per_run: float
    emulator_training_cost_hours: float
    emulator_inference_hours_per_run: float
    speedup_factor: float
    breakeven_runs: int | None
    viable: bool
    summary: str

    def to_dict(self) -> dict:
        return {
            "upstream_hpc_hours_per_run": round(self.upstream_hpc_hours_per_run, 4),
            "emulator_training_cost_hours": round(self.emulator_training_cost_hours, 4),
            "emulator_inference_hours_per_run": round(self.emulator_inference_hours_per_run, 6),
            "speedup_factor": round(self.speedup_factor, 2),
            "breakeven_runs": self.breakeven_runs,
            "viable": self.viable,
            "summary": self.summary,
        }


@dataclass
class ComponentTriage:
    """Triage diagnosis and investment recommendation for one system component."""

    component: str
    model_type: str
    local_runtime_seconds: float
    upstream_hpc_hours: float
    compute_share: float
    downstream_sensitivity: float
    skill_shortfall: float
    priority_score: float
    recommendation: str  # "ai_emulator" | "component_swap" | "parameter_calibration" | "retain_baseline"
    rationale: str
    emulator_roi: EmulatorROI
    sensitivities: list[PerturbationSensitivity] = field(default_factory=list)
    validation_results: list[ValidationResult] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "component": self.component,
            "model_type": self.model_type,
            "local_runtime_seconds": round(self.local_runtime_seconds, 6),
            "upstream_hpc_hours": round(self.upstream_hpc_hours, 4),
            "compute_share": round(self.compute_share, 4),
            "downstream_sensitivity": round(self.downstream_sensitivity, 4),
            "skill_shortfall": round(self.skill_shortfall, 4),
            "priority_score": round(self.priority_score, 4),
            "recommendation": self.recommendation,
            "rationale": self.rationale,
            "emulator_roi": self.emulator_roi.to_dict(),
            "sensitivities": [s.to_dict() for s in self.sensitivities],
            "validation_results": [r.to_dict() for r in self.validation_results],
        }


@dataclass
class TriageReport:
    """Whole-system triage report ranking components and recommending interventions."""

    system_name: str
    baseline_metrics: dict[str, dict[str, float]]
    components: list[ComponentTriage]

    def to_dict(self) -> dict:
        return {
            "system_name": self.system_name,
            "baseline_metrics": {
                out: {k: round(v, 6) for k, v in m.items()}
                for out, m in self.baseline_metrics.items()
            },
            "components": [c.to_dict() for c in self.components],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    def to_markdown(self) -> str:
        lines = [
            f"# Ecosystem Triage Report: {self.system_name}",
            "",
        ]
        if self.baseline_metrics:
            lines.append("## Baseline Terminal Performance")
            lines.append("")
            for out_name, m_dict in self.baseline_metrics.items():
                formatted = ", ".join(f"**{k}**={v:.4f}" for k, v in m_dict.items())
                lines.append(f"- `{out_name}`: {formatted}")
            lines.append("")

        lines.extend(
            [
                "## Component Investment Matrix",
                "",
                "| Priority | Component | Model Type | Compute Share | Downstream Sensitivity | Shortfall | Recommendation | Emulator Break-Even |",
                "| --- | --- | --- | --- | --- | --- | --- | --- |",
            ]
        )
        for idx, comp in enumerate(self.components, 1):
            be = (
                f"{comp.emulator_roi.breakeven_runs} runs ({comp.emulator_roi.speedup_factor:.0f}x)"
                if comp.emulator_roi.viable and comp.emulator_roi.breakeven_runs is not None
                else "N/A"
            )
            lines.append(
                f"| {idx} ({comp.priority_score:.2f}) | `{comp.component}` | {comp.model_type} "
                f"| {100.0 * comp.compute_share:.1f}% | {comp.downstream_sensitivity:.3f} "
                f"| {comp.skill_shortfall:.3f} | **{comp.recommendation}** | {be} |"
            )

        lines.append("")
        lines.append("## Detailed Component Diagnostics")
        lines.append("")
        for comp in self.components:
            lines.append(f"### `{comp.component}` -> **{comp.recommendation}**")
            lines.append(f"- **Rationale:** {comp.rationale}")
            lines.append(
                f"- **Compute Profile:** {comp.upstream_hpc_hours:.2f} HPC hrs/run "
                f"({100.0 * comp.compute_share:.1f}% of chain compute), "
                f"local runtime {comp.local_runtime_seconds:.4f}s"
            )
            lines.append(f"- **Emulator ROI:** {comp.emulator_roi.summary}")
            if comp.sensitivities:
                for s in comp.sensitivities:
                    lines.append(
                        f"- **Sensitivity (`{s.perturbation}` -> `{s.terminal_output}`):** "
                        f"dKGE={s.delta_kge:+.4f}, dRMSE={s.delta_rmse:+.4f} "
                        f"(sensitivity={s.relative_sensitivity:.3f})"
                    )
            lines.append("")
        return "\n".join(lines)


def _compute_emulator_roi(comp: Component, compute_share: float) -> EmulatorROI:
    cost_meta = comp.metadata.get("compute_cost", {}) if isinstance(comp.metadata, dict) else {}
    hpc_hours = float(cost_meta.get("hpc_hours_per_run", cost_meta.get("hours_per_run", 0.0)))
    training_hours = float(
        cost_meta.get("emulator_training_hours", max(hpc_hours * 5.0, 10.0) if hpc_hours > 0 else 0.0)
    )
    inference_hours = float(
        cost_meta.get("emulator_inference_hours", max(hpc_hours * 0.001, 0.0001) if hpc_hours > 0 else 0.0)
    )
    if hpc_hours <= 0.0:
        return EmulatorROI(
            upstream_hpc_hours_per_run=0.0,
            emulator_training_cost_hours=0.0,
            emulator_inference_hours_per_run=0.0,
            speedup_factor=1.0,
            breakeven_runs=None,
            viable=False,
            summary="Low compute cost; direct physical execution is already fast.",
        )

    savings_per_run = hpc_hours - inference_hours
    speedup = hpc_hours / max(inference_hours, 1e-9)
    if savings_per_run <= 0:
        return EmulatorROI(
            upstream_hpc_hours_per_run=hpc_hours,
            emulator_training_cost_hours=training_hours,
            emulator_inference_hours_per_run=inference_hours,
            speedup_factor=speedup,
            breakeven_runs=None,
            viable=False,
            summary="Emulator inference does not save compute over direct execution.",
        )

    breakeven = max(1, int(math.ceil(training_hours / savings_per_run)))
    viable = compute_share >= 0.40 and speedup >= 10.0 and hpc_hours >= 1.0
    summary = (
        f"{speedup:.0f}x speedup ({hpc_hours:.1f} -> {inference_hours:.4f} HPC hrs/run); "
        f"breaks even after {breakeven} scenario runs (training cost ~{training_hours:.1f} hrs)."
    )
    return EmulatorROI(
        upstream_hpc_hours_per_run=hpc_hours,
        emulator_training_cost_hours=training_hours,
        emulator_inference_hours_per_run=inference_hours,
        speedup_factor=speedup,
        breakeven_runs=breakeven,
        viable=viable,
        summary=summary,
    )


def _shortfall_from_results(results: list[ValidationResult]) -> float:
    if not results:
        return 0.0
    scores: list[float] = []
    for r in results:
        if r.metric in ("nse", "kge", "correlation"):
            scores.append(max(0.0, min(1.0, (0.85 - r.value) / 0.85)))
        elif r.metric == "relative_bias":
            scores.append(min(1.0, abs(r.value)))
        elif r.metric == "pbias":
            scores.append(min(1.0, abs(r.value) / 100.0))
        elif r.threshold is not None and r.threshold > 0:
            scores.append(max(0.0, min(1.0, (abs(r.value) - r.threshold) / r.threshold)))
    return float(np.mean(scores)) if scores else 0.0


def _choose_recommendation(
    comp: Component,
    compute_share: float,
    sensitivity: float,
    shortfall: float,
    roi: EmulatorROI,
) -> tuple[str, str]:
    meta = comp.metadata if isinstance(comp.metadata, dict) else {}
    structural_deficit = bool(meta.get("structural_deficit", False))
    tunable_params = int(meta.get("tunable_parameters", len(meta.get("parameters", []))))

    if sensitivity < 0.05 and shortfall < 0.15 and not roi.viable:
        return (
            "retain_baseline",
            f"Low downstream sensitivity ({sensitivity:.3f}) and modest shortfall ({shortfall:.3f}); "
            "downstream components damp perturbations, so engineering effort has higher ROI elsewhere.",
        )

    if roi.viable and (shortfall < 0.35 or not structural_deficit):
        return (
            "ai_emulator",
            f"Component consumes {100.0 * compute_share:.1f}% of total chain compute "
            f"({roi.upstream_hpc_hours_per_run:.1f} HPC hrs/run) with {sensitivity:.3f} downstream "
            f"sensitivity. An AI/statistical emulator yields a {roi.speedup_factor:.0f}x speedup "
            f"and breaks even after {roi.breakeven_runs} ensemble runs.",
        )

    if structural_deficit or shortfall >= 0.30 or (sensitivity >= 0.25 and tunable_params == 0):
        return (
            "component_swap",
            f"High downstream sensitivity ({sensitivity:.3f}) combined with structural/regime "
            f"shortfall ({shortfall:.3f}). Swapping the component formulation or input dataset "
            "is recommended over local parameter tuning.",
        )

    if tunable_params > 0 or sensitivity >= 0.10 or shortfall >= 0.15:
        return (
            "parameter_calibration",
            f"Component shows meaningful downstream sensitivity ({sensitivity:.3f}) with "
            f"moderate shortfall ({shortfall:.3f}) and {max(tunable_params, 1)} tunable parameter(s); "
            "sequential parameter optimization (`autoengineering optimize`) is recommended.",
        )

    return (
        "retain_baseline",
        f"Component meets baseline expectations (sensitivity={sensitivity:.3f}, shortfall={shortfall:.3f}).",
    )


def triage_system(
    system: System,
    *,
    validation_results: list[ValidationResult] | None = None,
    observed: Mapping[str, np.ndarray] | np.ndarray | None = None,
    validate_output: str | None = None,
    component_perturber: Callable[[str, float], Mapping[str, np.ndarray]] | None = None,
    perturbation_fraction: float = 0.10,
) -> TriageReport:
    """Run ecosystem bottleneck, sensitivity, and Emulator/Swap ROI triage on ``system``.

    Args:
        system: The connected :class:`System` graph.
        validation_results: Optional pre-computed :class:`ValidationResult` list.
        observed: Optional terminal observation array (or dict of ``{output_key: array}``)
            used when ``component_perturber`` is supplied for empirical sensitivity probing.
        validate_output: Terminal output key when ``observed`` is a single array.
        component_perturber: Optional callable ``(component_name, scale_factor) -> outputs_dict``
            that runs the chain with ``component_name``'s outputs scaled by ``1 + scale_factor``
            (and ``scale_factor=0.0`` for baseline).
        perturbation_fraction: Fractional output perturbation (default ``0.10`` for +10%).

    Returns:
        A :class:`TriageReport` ranking components and recommending an intervention for each.
    """
    validation_results = list(validation_results or [])
    comp_map: dict[str, Component] = {c.name: c for c in system.components}
    by_comp_results: dict[str, list[ValidationResult]] = {name: [] for name in comp_map}
    for r in validation_results:
        if r.component in by_comp_results:
            by_comp_results[r.component].append(r)
        elif "." in r.component:
            prefix = r.component.split(".", 1)[0]
            if prefix in by_comp_results:
                by_comp_results[prefix].append(r)

    # Normalize observed dict if provided
    obs_map: dict[str, np.ndarray] = {}
    if isinstance(observed, Mapping):
        obs_map = {k: np.asarray(v, dtype=float) for k, v in observed.items()}
    elif observed is not None and validate_output is not None:
        obs_map = {validate_output: np.asarray(observed, dtype=float)}

    baseline_metrics: dict[str, dict[str, float]] = {}
    empirical_sensitivities: dict[str, list[PerturbationSensitivity]] = {
        name: [] for name in comp_map
    }
    measured_runtimes: dict[str, float] = {}

    if component_perturber is not None and obs_map:
        t0 = time.perf_counter()
        base_out = component_perturber("__baseline__", 0.0)
        base_elapsed = time.perf_counter() - t0
        for out_key, obs_arr in obs_map.items():
            sim_arr = np.asarray(base_out[out_key], dtype=float)
            res = validate_arrays(
                out_key, obs_arr, sim_arr, metrics=["rmse", "bias", "nse", "kge", "pbias"]
            )
            baseline_metrics[out_key] = {r.metric: r.value for r in res}

        for comp_name in system.topological_order():
            t_start = time.perf_counter()
            pert_out = component_perturber(comp_name, perturbation_fraction)
            measured_runtimes[comp_name] = time.perf_counter() - t_start
            for out_key, obs_arr in obs_map.items():
                if out_key not in pert_out:
                    continue
                sim_pert = np.asarray(pert_out[out_key], dtype=float)
                res_pert = validate_arrays(out_key, obs_arr, sim_pert, metrics=["rmse", "kge"])
                m_pert = {r.metric: r.value for r in res_pert}
                base_kge = baseline_metrics[out_key]["kge"]
                base_rmse = baseline_metrics[out_key]["rmse"]
                d_kge = m_pert["kge"] - base_kge
                d_rmse = m_pert["rmse"] - base_rmse
                rel_sens = (
                    abs(d_rmse)
                    / (max(abs(base_rmse), 1e-9) * max(abs(perturbation_fraction), 1e-6))
                    + abs(d_kge) / max(abs(perturbation_fraction), 1e-6)
                ) / 2.0
                empirical_sensitivities[comp_name].append(
                    PerturbationSensitivity(
                        component=comp_name,
                        perturbation=f"+{100.0 * perturbation_fraction:.0f}% output perturbation",
                        terminal_output=out_key,
                        baseline_kge=base_kge,
                        perturbed_kge=m_pert["kge"],
                        delta_kge=d_kge,
                        baseline_rmse=base_rmse,
                        perturbed_rmse=m_pert["rmse"],
                        delta_rmse=d_rmse,
                        relative_sensitivity=min(1.0, float(rel_sens)),
                    )
                )
    else:
        base_elapsed = 0.0

    # Compute HPC cost shares
    hpc_costs: dict[str, float] = {}
    local_runtimes: dict[str, float] = {}
    for name, comp in comp_map.items():
        meta = comp.metadata if isinstance(comp.metadata, dict) else {}
        cost_meta = (
            meta.get("compute_cost", {}) if isinstance(meta.get("compute_cost"), dict) else {}
        )
        hpc = float(cost_meta.get("hpc_hours_per_run", cost_meta.get("hours_per_run", 0.0)))
        loc_rt = float(
            measured_runtimes.get(
                name, cost_meta.get("local_runtime_seconds", base_elapsed / max(len(comp_map), 1))
            )
        )
        hpc_costs[name] = hpc
        local_runtimes[name] = loc_rt

    total_hpc = sum(hpc_costs.values())
    total_local = sum(local_runtimes.values())

    total_nodes = max(len(comp_map), 1)
    triaged: list[ComponentTriage] = []

    for name, comp in comp_map.items():
        if total_hpc > 0:
            compute_share = hpc_costs[name] / total_hpc
        elif total_local > 0:
            compute_share = local_runtimes[name] / total_local
        else:
            compute_share = 1.0 / total_nodes

        sens_list = empirical_sensitivities[name]
        meta = comp.metadata if isinstance(comp.metadata, dict) else {}
        if sens_list:
            downstream_sens = float(np.mean([s.relative_sensitivity for s in sens_list]))
        elif "downstream_sensitivity" in meta:
            downstream_sens = float(meta["downstream_sensitivity"])
        else:
            # Topological fallback: fraction of downstream components + terminal sink bonus
            desc = system.downstream_of(name)
            downstream_sens = min(1.0, (len(desc) + 1) / total_nodes)

        comp_results = by_comp_results.get(name, [])
        if comp_results:
            shortfall = _shortfall_from_results(comp_results)
        elif "skill_shortfall" in meta:
            shortfall = float(meta["skill_shortfall"])
        else:
            shortfall = 0.25 * downstream_sens

        roi = _compute_emulator_roi(comp, compute_share)
        rec, rationale = _choose_recommendation(
            comp, compute_share, downstream_sens, shortfall, roi
        )
        priority = round(
            0.40 * downstream_sens + 0.35 * shortfall + 0.25 * compute_share,
            4,
        )
        triaged.append(
            ComponentTriage(
                component=name,
                model_type=comp.model_type,
                local_runtime_seconds=local_runtimes[name],
                upstream_hpc_hours=hpc_costs[name],
                compute_share=compute_share,
                downstream_sensitivity=downstream_sens,
                skill_shortfall=shortfall,
                priority_score=priority,
                recommendation=rec,
                rationale=rationale,
                emulator_roi=roi,
                sensitivities=sens_list,
                validation_results=comp_results,
            )
        )

    triaged.sort(key=lambda c: c.priority_score, reverse=True)
    return TriageReport(
        system_name=system.name,
        baseline_metrics=baseline_metrics,
        components=triaged,
    )
