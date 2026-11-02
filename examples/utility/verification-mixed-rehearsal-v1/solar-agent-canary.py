"""Qualify one real solar role-removal cell with a partially untried pool."""

from dataclasses import replace
import json
from pathlib import Path

from autoengineering.utility.mixed_execution import ScriptedMixedCoordinator
from autoengineering.utility.routes import RoutePlan
from autoengineering.utility.store import SuiteStore
from examples.utility.rehearse_mixed import prepare

output, source, plan, prepared = prepare(
    Path("examples/utility/development/solar-agent-canary-v1"),
    Path("/Users/cam/projects/autoengineering/examples/open_chains/solar/data"),
)
names = ("solar", "circuit")
rows = tuple(
    next(
        r
        for r in plan.routes.task_routes
        if r.task_id == name and r.recipe.kind == "no_investigator"
    )
    for name in names
)
tasks = tuple(next(t for t in prepared.spec.tasks if t.task_id == name) for name in names)
routes = RoutePlan("utility-routes-v1", rows, 1, 17, {t.task_id: t.partition_digest for t in tasks})
plan = replace(
    plan, routes=routes, campaigns=tuple(t for t in plan.campaigns if t.task_id in names)
)
route_specs, cells = routes.expand(tasks, prepared.spec.budgets)
spec = replace(
    prepared.spec, tasks=tasks, routes=route_specs, cells=cells, protocol_digest=plan.digest
)
store = SuiteStore.create(output / "agent-canary", spec)
(output / "canary-plan.json").write_text(plan.to_json())
coordinator = ScriptedMixedCoordinator(store, plan, source)
result = coordinator.run(max_new_cells=1)
state = store.replay()
first = next(a for a, status in state["attempts"].values() if status == "finished")
child, bindings = coordinator.runtime._child(first.child_digest)
projection = child.replay()
assert not projection.pending
assert result["finished_cells"] == 1 and result["assigned_cells"] == 2
assert len(prepared.replay()["attempts"]) == 0
summary = {
    "purpose": "bounded exposed agent canary; not a full matrix",
    "result": result,
    "reservations": len(projection.reservations),
    "observations": len(projection.observations),
    "all_stops_verified": all(o.stop_verified for o in projection.observations.values()),
    "confirmation_accesses": len(state["confirmation_accesses"]),
    "frozen": state["frozen"],
    "utility_verdict": "not_attempted",
}
(output / "agent-canary-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps(summary), flush=True)
