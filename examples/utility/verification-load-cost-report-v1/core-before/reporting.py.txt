"""Offline comparative tables reconstructed from pinned public evidence.

No model, scorer or provider is invoked. Exports preserve assigned denominators,
blank unknown costs, separate units and the exact suite journal head.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
import hashlib
import io
from pathlib import Path
from typing import Literal

from autoengineering.campaign.artifacts import confined_file, read_bytes
from autoengineering.campaign.records import ArtifactRef
from autoengineering.campaign.serialization import Record, canonical_json, unique_json
from autoengineering.campaign.store import StoreError, durable_write
from .analysis import EffortAnalysisPlan, read_analysis_plan, analyze_confirmation
from .baselines import SharedBaseline
from .confirmation import read_manifest
from .contracts import sha256
from .report import accounting_report
from .scoring import ConfirmationGrant, _read, read_receipt
from .uncertainty import DependencePlan


@dataclass(frozen=True)
class ReportSpec(Record):
    schema: Literal["utility-report-inputs-v1"]
    suite_digest: str
    analysis: ArtifactRef
    dependence: ArtifactRef | None
    dependence_evidence: tuple[ArtifactRef, ...]
    shared_baselines: tuple[SharedBaseline, ...] = ()

    @classmethod
    def from_dict(cls, data):
        if cls is ReportSpec and isinstance(data, dict) and data.get("schema") == "utility-report-inputs-v2":
            return EffortReportSpec.from_dict(data)
        return super().from_dict(data)

    def _validate(self):
        sha256(self.suite_digest)
        if self.dependence_evidence and self.dependence is None:
            raise ValueError("dependence receipts require a pinned dependence plan")
        if len({ref.sha256 for ref in self.dependence_evidence}) != len(self.dependence_evidence):
            raise ValueError("duplicate dependence artifact")


@dataclass(frozen=True)
class EffortReportSpec(ReportSpec):
    schema: Literal["utility-report-inputs-v2"]
    effort: ArtifactRef = field(kw_only=True)


def comparative_report(store, request: ReportSpec):
    """Read only public, committed confirmation; a missing barrier is an error."""
    if request.suite_digest != store.spec.digest:
        raise StoreError("report inputs belong to another suite")
    before = store.replay()
    if before["frozen"] is None:
        raise StoreError("comparative report requires the complete selection barrier")
    raw = read_bytes(store.root, request.analysis).decode()
    plan = read_analysis_plan(raw)
    dependence = (DependencePlan.from_json(read_bytes(store.root, request.dependence).decode())
                  if request.dependence else None)
    analysis = analyze_confirmation(store, plan, dependence=dependence,
        dependence_references=request.dependence_evidence, shared_baselines=request.shared_baselines)
    accounting = accounting_report(store)
    effort = None
    if isinstance(request, EffortReportSpec):
        if not isinstance(plan, EffortAnalysisPlan):
            raise ValueError("human-effort inputs require a preregistered effort analysis")
        from .effort import EffortInputs, read_effort, analyze_effort
        inputs = EffortInputs.from_json(read_bytes(store.root, request.effort).decode())
        effort = read_effort(store.spec, store.root, inputs, policy_digest=plan.effort_policy_digest)
        analysis = analyze_effort(store.spec, plan, analysis, effort)
        if accounting["evidence_blockers"]:
            for row in analysis["contrasts"]:
                row["efficiency_verdict"] = "inconclusive"
    if effort is not None:
        accounting["human_effort"] = effort
    selected = {item.cell_digest: item for item in read_manifest(store.root, before["frozen"]).cells}
    scored = {}
    for attempt, identity in before["confirmation_scores"].items():
        grant = _read(store.root, before["confirmation_accesses"][attempt],
                      "confirmation-grant.json", ConfirmationGrant)
        scored[grant.cell_digest] = (identity, read_receipt(store.root, identity).score)
    for allocation in (SharedBaseline.from_dict(a) for a in analysis["shared_baselines"]):
        original = next(value for value in scored.values() if value[0] == allocation.score_digest)
        for cell in allocation.cell_digests:
            scored[cell] = original
    rows = []
    for cell in store.spec.cells:
        selection = selected[cell.digest]
        identity, score = scored.get(cell.digest, (None, None))
        attempts = [(a, status) for a, status in before["attempts"].values()
                    if a.cell_digest == cell.digest and a.phase == "confirmation"]
        status = score.status if score else ("reconciliation_required" if attempts else
                  "not_attempted" if selection.status == "selected" else selection.status)
        rows.append({"cell_digest": cell.digest, "task_id": cell.task_id, "route_id": cell.route_id,
            "regime": cell.regime, "repetition": cell.repetition, "seed": cell.seed,
            "scenario_digest": cell.scenario_digest, "selection_status": selection.status,
            "confirmation_status": status, "score_digest": identity,
            "outcome": score.outcome if score else None, "units": score.units if score else None,
            "value": score.value if score else None, "feasible": score.feasible if score else None,
            "model_digest": selection.model.sha256 if selection.model else None,
            "selected_state_digest": selection.selected_state.sha256 if selection.selected_state else None})
        if store.spec.baseline_reuse is not None:
            rows[-1]["confirmation_reused"] = score is not None and not attempts
    if store.replay()["head"] != before["head"]:
        raise StoreError("suite changed during report reconstruction")
    return {"schema": "utility-comparative-report-v1", "suite_digest": store.spec.digest,
            "source_head": before["head"], "report_spec_digest": request.digest,
            "report_inputs": request.to_dict(), "cells": rows, "analysis": analysis,
            "accounting": accounting, "complete_cost_evidence": accounting["complete_cost_evidence"],
            "claim_limits": ["Public aggregates do not qualify the private scorer boundary",
                             "Unknown quantities remain blank in tables",
                             "No suite-wide score combines different outcome units",
                             "Efficiency and role retention require further evidence"]}


def _csv(rows, columns):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=columns, lineterminator="\n", extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode()


def report_files(document):
    """Derive every exported table from one reconstructed report document."""
    cells = document["cells"]
    pairs, contrasts, failures, roles, costs = [], [], [], [], []
    for contrast in document["analysis"]["contrasts"]:
        base = {name: contrast[name] for name in ("task_id", "regime", "route_id", "comparator_id", "outcome", "units")}
        for pair in contrast["pairs"]:
            pairs.append(base | pair)
        interval = contrast["interval"]
        contrasts.append(base | {name: contrast[name] for name in (
            "assigned_pairs", "valid_pairs", "missing_pairs", "mean_gain", "verdict",
            "repetition_verdict", "dependence_complete", "efficiency_verdict", "scientific_claim_scope")}
            | {"efficiency_basis": contrast.get("efficiency_basis")}
            | {"interval_lower": interval[0] if interval else None, "interval_upper": interval[1] if interval else None})
        for route, summary in contrast["route_counts"].items():
            for status, count in sorted(summary["statuses"].items()):
                failures.append(base | {"counted_route": route, "status": status, "count": count,
                    "assigned": summary["assigned"], "successful_feasible": summary["successful_feasible"],
                    "target_reached": summary["target_reached"], "target_censored": summary["target_censored"],
                    "target_unknown": summary["target_unknown"]})
    by_cell = {row["cell_digest"]: row for row in cells}
    for record in document["accounting"]["receipts"]:
        for cell, fraction in zip(record["cell_digests"], record["allocation"]):
            if cell not in by_cell:
                raise StoreError("cost allocation references an unassigned cell")
            costs.append({name: record[name] for name in (
                "receipt_id", "source_digest", "category", "resource", "units", "quantity")}
                | {"cell_digest": cell, "allocation": fraction,
                   "allocated_quantity": record["quantity"]*fraction if record["quantity"] is not None else None})
    for role in document["accounting"]["role_permissions_reserved"]:
        row = by_cell[role["cell_digest"]]
        roles.append(role | {"task_id": row["task_id"], "route_id": row["route_id"],
                             "regime": row["regime"], "repetition": row["repetition"]})
    dependence = []
    for contrast in document["analysis"]["contrasts"]:
        for item in contrast["dependence_evidence"]:
            if item is not None:
                interval = item["interval"]
                dependence.append(item | {"interval_lower": interval[0] if interval else None,
                                          "interval_upper": interval[1] if interval else None})
    prefix = ["task_id", "regime", "route_id", "comparator_id", "outcome", "units"]
    files = {"report.json": (canonical_json(document)+"\n").encode(),
        "summary.md": render_comparative_markdown(document).encode(),
        "cells.csv": _csv(cells, ["cell_digest", "task_id", "route_id", "regime", "repetition", "seed",
            "scenario_digest", "selection_status", "confirmation_status", "score_digest", "outcome", "units",
            "value", "feasible", "model_digest", "selected_state_digest"]
            + (["confirmation_reused"] if any("confirmation_reused" in row for row in cells) else [])),
        "paired-effects.csv": _csv(pairs, prefix+["repetition", "scenario_digest", "route_value", "comparator_value", "gain"]),
        "contrasts.csv": _csv(contrasts, prefix+["assigned_pairs", "valid_pairs", "missing_pairs", "mean_gain",
            "interval_lower", "interval_upper", "verdict", "repetition_verdict", "dependence_complete",
            "efficiency_verdict", "efficiency_basis", "scientific_claim_scope"]),
        "failure-counts.csv": _csv(failures, prefix+["counted_route", "status", "count", "assigned", "successful_feasible",
            "target_reached", "target_censored", "target_unknown"]),
        "physical-costs.csv": _csv(document["accounting"]["receipts"],
            ["receipt_id", "source_digest", "category", "resource", "units", "quantity"]),
        "cost-allocations.csv": _csv(costs, ["receipt_id", "source_digest", "category", "resource", "units", "quantity",
            "cell_digest", "allocation", "allocated_quantity"]),
        "role-permissions.csv": _csv(roles, ["cell_digest", "task_id", "route_id", "regime", "repetition", "role", "calls"]),
        "dependence.csv": _csv(dependence, ["route_cell_digest", "comparator_cell_digest", "route_score_digest",
            "comparator_score_digest", "policy_digest", "gain", "interval_lower", "interval_upper", "status"])}
    if "human_effort" in document["accounting"]:
        effort = document["accounting"]["human_effort"]
        files["human-effort-cells.csv"] = _csv([{"cell_digest": cell} | value for cell, value in sorted(effort["cells"].items())],
            ["cell_digest", "complete", "first_use_seconds", "amortized_seconds", "timer_seconds", "self_reported_seconds", "unknown_logs"])
        files["human-effort-allocations.csv"] = _csv(effort["allocations"], ["log_id", "log_digest", "source_digest", "scope_id",
            "phase", "kind", "activity", "method", "actor_digest", "cell_digest", "allocation", "physical_seconds", "first_use_seconds", "amortized_seconds"])
        files["human-effort-pairs.csv"] = _csv([{
            "task_id": row["task_id"], "regime": row["regime"], "route_id": row["route_id"], "comparator_id": row["comparator_id"],
            "basis": row["effort"]["basis"]} | pair for row in document["analysis"]["contrasts"] for pair in row["effort"]["pairs"]],
            ["task_id", "regime", "route_id", "comparator_id", "basis", "repetition", "scenario_digest", "route_seconds", "comparator_seconds", "seconds_saved"])
    return files


def render_comparative_markdown(document):
    lines = ["# Utility comparison", "", f"Suite: `{document['suite_digest']}`", "",
             f"Assigned cells: {len(document['cells'])}", "",
             "| Task | Regime | Route | Comparator | Outcome | Units | Valid / assigned pairs | Verdict |",
             "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for row in document["analysis"]["contrasts"]:
        lines.append(f"| {row['task_id']} | {row['regime']} | {row['route_id']} | {row['comparator_id']} | "
                     f"{row['outcome']} | {row['units']} | {row['valid_pairs']} / {row['assigned_pairs']} | {row['verdict']} |")
    lines.extend(["", "Cost evidence is incomplete. Blank table cells denote unknown or unavailable quantities.",
                  "Physical cost allocations retain the original receipt quantity and exclusive shares.",
                  "Role permissions are reservations, not measured host starts.", ""])
    lines.extend(["Provider token components overlap totals. Do not sum distinct token resources.",
                  "Container lifecycle durations overlap callback durations. Do not add them.",
                  "Missing token fields and billed provider spend remain unknown.", ""])
    if "human_effort" in document["accounting"]:
        effort = document["accounting"]["human_effort"]
        lines.extend(["Human effort uses declared logged scopes (person-seconds).",
                      f"Declared scope coverage complete: {effort['declared_scopes_complete']}.",
                      f"Amortization horizon: {effort['amortization_horizon']}.",
                      "This does not establish complete computational or monetary cost.", ""])
        for row in document["analysis"]["contrasts"]:
            lines.append(f"Logged human effort, {row['task_id']} / {row['regime']} / "
                         f"{row['route_id']} versus {row['comparator_id']}: {row['efficiency_verdict']}.")
            comparison = row["effort"]
            lines.append(f"Mean saving: {comparison['mean_seconds_saved']} person-s; "
                         f"interval: {comparison['interval']}; "
                         f"logged pairs: {comparison['valid_pairs']} / {comparison['assigned_pairs']}; "
                         f"basis: {comparison['basis']}.")
        lines.append("")
    lines.extend(document["claim_limits"])
    return "\n".join(lines)+"\n"


def export_report(store, request, destination):
    """Write a new export, with its integrity manifest committed last."""
    document = comparative_report(store, request)
    files = report_files(document)
    root = Path(destination).absolute()
    if root.exists() or any(part.is_symlink() for part in (root, *root.parents)):
        raise StoreError("report export requires an absent path without symlinks")
    root.mkdir(mode=0o700, parents=True)
    manifest = {"schema": "utility-report-export-v1", "suite_digest": store.spec.digest,
                "source_head": document["source_head"], "report_spec_digest": request.digest,
                "files": {name: {"sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}
                          for name, raw in sorted(files.items())}}
    for name, raw in files.items():
        durable_write(root / name, raw)
    durable_write(root / "manifest.json", (canonical_json(manifest)+"\n").encode())
    return manifest


def verify_export(store, request, destination, *, rerender_figures=False):
    """Reconstruct report numbers; figure pixels require explicit rerendering."""
    root = Path(destination).absolute()
    manifest = unique_json(confined_file(root, "manifest.json").read_text())
    if isinstance(manifest, dict) and manifest.get("schema") == "utility-figure-export-v1":
        from .figures import verify_figures
        return verify_figures(store, request, root, rerender=rerender_figures)
    if rerender_figures:
        raise ValueError("pixel verification requires a figure export")
    document = comparative_report(store, request)
    files = report_files(document)
    expected = {"schema": "utility-report-export-v1", "suite_digest": store.spec.digest,
                "source_head": document["source_head"], "report_spec_digest": request.digest,
                "files": {name: {"sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}
                          for name, raw in sorted(files.items())}}
    if manifest != expected or {p.name for p in root.iterdir()} != {*files, "manifest.json"}:
        raise StoreError("export manifest differs from authoritative reconstruction")
    for name, raw in files.items():
        if confined_file(root, name).read_bytes() != raw:
            raise StoreError("exported table differs from authoritative reconstruction")
    return {"status": "verified_reconstruction", "suite_digest": store.spec.digest,
            "source_head": document["source_head"], "files": len(files)}
