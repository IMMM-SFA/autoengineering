"""Export selected development metrics without pooling incompatible task units."""

import csv
import json
from pathlib import Path

from autoengineering.campaign.artifacts import read_bytes
from autoengineering.utility.confirmation import SelectedState, read_manifest
from autoengineering.utility.mixed_execution import ScriptedMixedPlan
from autoengineering.utility.store import SuiteStore

root = Path("examples/utility/development/four-family-v1")
v = Path("examples/utility/verification-four-family-v1")
store = SuiteStore(root / "suite")
reader = json.loads((v / "offline-reader.json").read_text())
manifest = read_manifest(store.root, reader["suite_selection"])
cells = {c.digest: c for c in store.spec.cells}
routes = {r.route_id: r.kind for r in store.spec.routes}
families = {t.task_id: t.family for t in store.spec.tasks}
plan = ScriptedMixedPlan.from_json((root / "execution-plan.json").read_text())
campaigns = {t.task_id: t.campaign for t in plan.campaigns}
rows, flat = [], []
for selected in manifest.cells:
    c = cells[selected.cell_digest]
    bound = SelectedState.from_json(read_bytes(store.root, selected.selected_state).decode())
    camp = campaigns[c.task_id]
    rules = camp.execution.study.rules if c.task_id in ("circuit", "wind") else camp.acceptance
    rows.append(
        {
            "cell": c.digest,
            "task": c.task_id,
            "family": families[c.task_id],
            "route": routes[c.route_id],
            "repetition": c.repetition,
            "paired_seed": c.seed,
            "selected_evaluation_id": bound.evaluation.id,
            "configuration": dict(bound.configuration),
            "metrics": dict(bound.evaluation.metrics),
            "primary_metric": rules.primary_metric,
            "declared_output_units": {p.name: p.units for p in bound.model.outputs},
        }
    )
    flat.extend(
        {
            "cell": c.digest,
            "task": c.task_id,
            "route": routes[c.route_id],
            "metric": k,
            "value": value,
        }
        for k, value in bound.evaluation.metrics.items()
    )
(v / "development-outcomes.json").write_text(
    json.dumps(
        {
            "scope": "one exposed scripted repetition; no independent utility or role-retention conclusion",
            "rows": rows,
            "confirmation": "not_attempted",
            "utility_verdict": "not_attempted",
        },
        indent=2,
    )
    + "\n"
)
with (v / "development-metrics.csv").open("w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=("cell", "task", "route", "metric", "value"))
    w.writeheader()
    w.writerows(flat)
print(json.dumps({"cells": len(rows), "metric_rows": len(flat), "cross_task_aggregation": "none"}))
