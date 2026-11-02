"""Mechanical substitutions exercise real campaign transitions with scripted hosts."""
from dataclasses import replace

import pytest

from autoengineering.agents.batch import BatchCase, PhysicalReservation, PhysicalObservation
from autoengineering.agents.scheduler import SerialScheduler, template_digests
from autoengineering.agents.batch_science import BatchCampaignController
from autoengineering.utility.controller import UtilityController, CaseBinding
from autoengineering.utility.mechanical import AblationBroker, mechanism_identity
from autoengineering.utility.role_host import RoleBoundHost
from autoengineering.utility.routes import ScientificGrant, TaskRoute, RoutePlan, role_removals
from autoengineering.utility.store import SuiteStore
from autoengineering.campaign.serialization import digest
from test_agent_broker import create
from test_agent_batch import specification
from test_utility_contracts import suite, H
from test_utility_routes import full


@pytest.mark.parametrize("omitted", ["investigator", "implementer", "reviewer"])
def test_real_supplied_campaign_omits_one_host_role_and_keeps_scientific_acceptance(tmp_path, omitted):
    planning = tmp_path / "planning"
    planning.mkdir(mode=0o700)
    baseline, _ = create(planning)
    campaign = baseline.controller.spec
    candidates = tuple(dict.fromkeys((campaign.baseline.model.digest,
                                      *(s.model.digest for s in baseline.catalogue.values()))))
    partition = digest([data.to_dict() for data in campaign.data])
    bounds = digest([item.to_dict() for item in campaign.interventions])
    grant = ScientificGrant(candidates, partition, bounds, campaign.acceptance.digest, H, H, None)
    recipe = replace(full(), scientific_grant=grant,
        host=replace(full().host, model="scripted", version="scripted-1.0"),
        roles=tuple(replace(role, prompt_digest=template_digests()[role.role]) for role in full().roles))
    replacements = {role: mechanism_identity(role) for role in ("investigator", "implementer", "reviewer")}
    ablation = next(r for r in role_removals(recipe, replacements) if r.kind == "no_" + omitted)
    spec = suite()
    task = replace(spec.tasks[0], candidate_digests=candidates, partition_digest=partition)
    plan = RoutePlan("utility-routes-v1", (TaskRoute("task", "ablation", ablation),), 1, 17, {"task": H})
    routes, cells = plan.expand((task,), spec.budgets)
    spec = replace(spec, tasks=(task,), routes=routes, cells=cells)
    store = SuiteStore.create(tmp_path / "suite", spec)
    runtime = UtilityController(store)
    child_spec = specification()
    child_spec = replace(child_spec, host_configuration_digest=H, scientific_starts=2,
        limits=replace(child_spec.limits, max_invocations=20, max_tasks=16,
                       worker_seconds=30, transcript_bytes=1048576),
        cases=(BatchCase("agent", "comparison", routes[0].configuration_digest, 20, 2),))
    child = runtime.prepare_batch(child_spec, (CaseBinding(cells[0].digest, "agent"),))
    observed_roles = []

    def execute(batch, case_id):
        root = batch.root / "cases" / case_id
        root.mkdir(mode=0o700, exist_ok=True)
        original, _ = create(root)
        controller = BatchCampaignController(original.controller.store, original.controller.spec,
                                             batch=batch, case_id=case_id)
        fake = original.scheduler.host

        class BatchDelegate:
            def capabilities(self):
                return fake.capabilities()

            def invoke(self, task, prompt, *, invocation_id, timeout_seconds, max_output_bytes):
                observed_roles.append(task.role)
                reservation = PhysicalReservation("host-"+digest(invocation_id)[:32], case_id, "host",
                    digest(task.to_dict()), task.id, batch.clock(), timeout_seconds,
                    len(prompt.encode()), max_output_bytes, 0)

                def observe(r, value):
                    evidence = batch.evidence({"fixture_host": "scripted", "invocation_id": invocation_id,
                                               "role": task.role, "status": value.status})
                    return PhysicalObservation(r.id, value.status, True,
                        len(prompt.encode())+len(value.raw_output.encode()), value.usage, None,
                        "absent", value.elapsed_seconds, (evidence,))

                return batch.execute(reservation, lambda _: fake.invoke(task, prompt,
                    invocation_id=invocation_id, timeout_seconds=timeout_seconds,
                    max_output_bytes=max_output_bytes), observe)

            def cancel(self, invocation_id):
                return fake.cancel(invocation_id)

        host = RoleBoundHost(store, batch, cells[0].digest, plan, BatchDelegate(),
                             templates={r.role: r.prompt_digest for r in ablation.roles})
        scheduler = SerialScheduler(original.store, host)
        broker = AblationBroker(controller, scheduler, suite_store=store, plan=plan, cell_digest=cells[0].digest)
        assert broker.advance().state == "completed"
        scientific = controller.state()
        assert scientific.outcome == "accepted_candidate"
        assert scientific.decisions[-1].selected_configuration == {"multiplier": 1.5}
        assert len(scientific.budget.attempts) == 2
        assert omitted not in {task.role for task in broker.store.replay().tasks.values()}
        assert any(action.invocation_id is None for action in broker.store.replay().actions.values())
        count = len(observed_roles)
        broker.advance()
        assert len(observed_roles) == count
        batch.finish_case(case_id, "passed", (batch.evidence({"outcome": scientific.outcome,
                          "mechanical_role": omitted, "attempts": 2}),))

    runtime.dispatch(child.root.name, cells[0].digest, execute)
    assert omitted not in observed_roles
    assert len(store.replay()["mechanical_steps"]) == 1
    assert len([r for r in child.replay().reservations.values() if r.resource == "science"]) == 2
    assert store.replay()["attempts"]["child-" + cells[0].digest[:48]][1] == "finished"
    assert runtime.verify_result("child-"+cells[0].digest[:48])["case_result"]["status"] == "passed"


def test_mechanical_review_preserves_failed_checks_and_stops_for_missing_evidence():
    from autoengineering.utility.mechanical import mechanical_output
    summary = {"submitted_handoff": {"proposal": {"id": "candidate"}, "evaluation_id": "evaluation"},
        "mandatory_checks": [{"name": "physical", "version": "1"}],
        "evaluations": [{"id": "evaluation", "checks": [{"name": "physical", "version": "1", "status": "fail"}]}]}
    result = mechanical_output("reviewer", summary, H)
    assert result.recommendation == "proceed"  # Controller still vetoes failed physical evidence.
    assert summary["evaluations"][0]["checks"][0]["status"] == "fail"
    summary["evaluations"][0]["checks"] = []
    result = mechanical_output("reviewer", summary, H)
    assert result.recommendation == "stop" and result.missing_evidence == ("physical",)
    with pytest.raises(ValueError, match="unsupported"):
        mechanical_output("unknown", summary, H)
