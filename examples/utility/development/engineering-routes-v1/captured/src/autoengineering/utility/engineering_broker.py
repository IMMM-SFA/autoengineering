"""Engineering advice over the existing role scheduler and scientific journals.

Only supplied choices are admitted. Handoffs never create scientific authority.
The inherited role/request machinery retains existing grants, repairs and recovery.
"""

from __future__ import annotations

from contextlib import nullcontext
from dataclasses import replace

from autoengineering.agents.broker import CampaignBroker, WorkflowStopped
from autoengineering.agents.records import (
    CandidateBrief,
    NextStep,
    ReviewFindings,
    SuppliedConfiguration,
)
from autoengineering.campaign.artifacts import put_bytes
from autoengineering.campaign.records import Request
from autoengineering.campaign.serialization import canonical_json, digest
from autoengineering.campaign.store import StoreError
from .engineering_campaign import EngineeringNativeCampaignSpec
from .mechanical import (
    MechanicalClaim,
    MechanicalReply,
    mechanism_identity,
    mechanical_output,
    read_mechanical,
)


def engineering_catalogue(spec):
    items = [
        {
            "target": "engineering",
            "implementation_id": d.id,
            "parameters": dict(d.configuration),
            "mode": "fixed",
            "parameter_role": "fixed",
        }
        for d in spec.designs
    ]
    items.append(
        {
            "target": "engineering",
            "implementation_id": "calibration",
            "parameters": {},
            "mode": "calibrated",
            "parameter_role": "registered_numerical_recipe",
        }
    )
    if isinstance(spec, EngineeringNativeCampaignSpec):
        items.append(
            {
                "target": "engineering",
                "implementation_id": "native",
                "parameters": {},
                "mode": "native",
                "parameter_role": "registered_native_recipe",
            }
        )
    return tuple(items)


def engineering_recipe_identity(spec):
    run = spec.execution.study.run.to_dict()
    run["study"]["seed"] = 0
    native = spec.native.to_dict() if isinstance(spec, EngineeringNativeCampaignSpec) else None
    if native is not None:
        native["execution"]["study"]["run"]["study"]["seed"] = 0
    return digest(
        {
            "profile": "engineering-supplied-queue-v1",
            "baseline": dict(spec.baseline_configuration),
            "catalogue": engineering_catalogue(spec),
            "run": run,
            "native": native,
            "seed_rule": "paired-cell-seed-for-scenario-and-numerical-study",
        }
    )


def engineering_grant_identity(spec):
    """The model pool, domain, scenarios and rules shared by every route."""
    return {
        "candidates": (spec.model.digest,),
        "partition_digest": digest([s.to_dict() for s in spec.execution.scenarios]),
        "search_bounds_digest": digest(
            {
                "space": spec.execution.study.run.search_space.to_dict(),
                "catalogue": engineering_catalogue(spec),
                "baseline": dict(spec.baseline_configuration),
            }
        ),
        "acceptance_digest": spec.execution.study.rules.digest,
    }


def _public_evaluation(value):
    record = value.evaluation

    def checks(items):
        return [
            {
                "name": c.name,
                "version": c.version,
                "required": c.required,
                "scope": c.scope,
                "status": c.status,
                "value": c.value,
                "threshold": c.threshold,
            }
            for c in items
        ]

    return {
        "id": record.id,
        "configuration": dict(record.configuration),
        "status": record.status,
        "metrics": dict(record.metrics),
        "checks": checks(record.checks),
        "kind": "engineering_evaluation",
        "scenarios": [
            {"id": s.scenario_id, "outcomes": dict(s.values), "checks": checks(s.checks)}
            for s in value.scenarios
        ],
    }


def paired_engineering_spec(spec, seed):
    if type(seed) is not int or not 0 <= seed < 2**63:
        raise ValueError("engineering paired seed is outside supported bounds")
    study = spec.execution.study
    run = replace(study.run, study=replace(study.run.study, seed=seed))
    execution = replace(spec.execution, study=replace(study, run=run))
    if isinstance(spec, EngineeringNativeCampaignSpec):
        return replace(spec, execution=execution, native=replace(spec.native, execution=execution))
    return replace(spec, execution=execution)


def _proposal(brief):
    return {
        "id": brief.candidate_id,
        "target": brief.target,
        "implementation_id": brief.implementation_id,
        "hypothesis": brief.hypothesis,
        "sources": list(brief.evidence_ids),
        "expected_tradeoffs": brief.expected_tradeoffs,
        "kind": "engineering_choice_brief",
    }


def recipe_request(controller, operation, payload=None, *, key, resume_scenarios=False):
    """Reuse the original committed envelope instead of inventing a new revision."""
    payload = payload or {}
    identity = (
        "engineering-"
        + digest(
            {
                "campaign": controller.spec.digest,
                "operation": operation,
                "payload": payload,
                "key": key,
            }
        )[:32]
    )
    projection = controller.store.replay()
    previous = projection.responses.get(identity)
    if previous:
        event = next(e for e in projection.events if e.response.request_id == identity)
        original = Request(
            "1.0", controller.spec.name, identity, event.revision - 1, operation, payload
        )
        if event.request_digest != original.digest:
            raise StoreError("registered engineering request differs from original envelope")
        return previous[1]
    return controller.handle(
        Request("1.0", controller.spec.name, identity, projection.revision, operation, payload),
        resume_scenarios=resume_scenarios,
    )


def run_engineering_recipe(controller, kind, *, resume_scenarios=False):
    if kind not in ("baseline", "conventional"):
        raise StoreError("non-agent engineering recipe is unsupported")
    if kind == "conventional" and not isinstance(controller.spec, EngineeringNativeCampaignSpec):
        raise StoreError("conventional engineering requires its registered native driver")
    operations = [("evaluate", {"candidate_id": "baseline", "mode": "fixed"}, "baseline")]
    if kind == "conventional":
        operations += [
            (
                "evaluate",
                {"candidate_id": i["implementation_id"], "mode": i["mode"]},
                i["implementation_id"],
            )
            for i in engineering_catalogue(controller.spec)
        ]
    operations += [("review", {}, "review"), ("freeze", {}, "freeze")]
    for operation, payload, key in operations:
        response = recipe_request(
            controller, operation, payload, key=key, resume_scenarios=resume_scenarios
        )
        if response.status != "ok":
            raise WorkflowStopped("engineering recipe request failed: " + str(response.error))
    return controller.state()


class EngineeringBroker(CampaignBroker):
    """Supplied engineering choices with isolated roles or one advisory persona."""

    def __init__(self, controller, scheduler, *, suite_store=None, plan=None, cell_digest=None):
        self.controller, self.scheduler, self.store = controller, scheduler, scheduler.store
        self.workflow_route = self.store.spec.workflow_route
        if (self.store.spec.campaign_id, self.store.spec.campaign_identity) != (
            controller.spec.name,
            digest(controller.identity),
        ):
            raise StoreError("engineering worker/scientific identity differs")
        self.catalogue = engineering_catalogue(controller.spec)
        if (
            self.store.spec.execution_mode != "supplied"
            or self.store.spec.permitted_interventions
            != tuple(i["implementation_id"] for i in self.catalogue)
        ):
            raise StoreError("engineering worker catalogue differs from frozen scientific choices")
        self.phase, self.proposals = "proposal_open", []
        self._resume_scenarios = False
        self.suite_store, self.plan, self.cell_digest = suite_store, plan, cell_digest
        self.omitted = None
        if suite_store is not None:
            from .role_host import RoleBoundHost

            host = scheduler.host
            if (
                not isinstance(host, RoleBoundHost)
                or host.store.root != suite_store.root
                or host.cell_digest != cell_digest
            ):
                raise StoreError("engineering suite broker needs its assigned role host")
            cell = next(c for c in suite_store.spec.cells if c.digest == cell_digest)
            self.recipe = next(
                row.recipe
                for row in plan.task_routes
                if (row.task_id, row.route_id) == (cell.task_id, cell.route_id)
            )
            expected_route = "single_agent" if self.recipe.kind == "single_agent" else "four_role"
            if self.workflow_route != expected_route:
                raise StoreError("engineering worker route differs from frozen recipe")
            if self.recipe.numerical_recipe_digest != engineering_recipe_identity(controller.spec):
                raise StoreError("engineering numerical recipe differs from frozen route")
            grant = engineering_grant_identity(controller.spec)
            if any(getattr(self.recipe.scientific_grant, k) != v for k, v in grant.items()):
                raise StoreError("engineering role grant differs from campaign")
            if self.recipe.kind.startswith("no_"):
                self.omitted = self.recipe.kind.removeprefix("no_")
                if self.recipe.replacements.get(self.omitted) != mechanism_identity(self.omitted):
                    raise StoreError("engineering ablation mechanism differs")

    def _resolve_action(self, action):
        if action.state == "completed":
            return action
        if action.kind != "request":
            raise StoreError("engineering worker journal contains unsupported staging")
        committed = action.request.request_id in self.controller.store.replay().responses
        guard = self._deadline(action.id)
        if committed:
            response = self.controller.handle(action.request)
        else:
            with guard:
                response = self.controller.handle(
                    action.request, resume_scenarios=self._resume_scenarios
                )
        with self.store.writer():
            result = self.store.commit(replace(action, state="completed", response=response))
        if committed and guard.deadline <= self.scheduler.clock():
            guard.expire()
            guard._check_forwarding()
        return result

    def summary(self):
        state = self.controller.state()
        rules = self.controller.spec.execution.study.rules
        summary = {
            "schema": "engineering-advice-v1",
            "campaign_id": self.controller.spec.name,
            "revision": state["projection"].revision,
            "state": self.phase,
            "scientific_state": state["projection"].state,
            "objective": {
                "metric": rules.primary_metric,
                "direction": rules.direction,
                "minimum_gain": rules.minimum_gain,
                "outcomes": [o.to_dict() for o in rules.outcomes],
                "secondary_limits": dict(rules.secondary_limits),
            },
            "catalogue": list(self.catalogue),
            "proposed_interventions": [
                {"target": p.target, "implementation_id": p.implementation_id}
                for p in self.proposals
            ],
            "evaluations": [_public_evaluation(v) for v in state["evaluations"]],
            "mandatory_checks": [c.to_dict() for c in rules.checks if c.required],
            "native_jobs": [
                {
                    "id": "native-report-" + r.digest[:24],
                    "status": r.status,
                    "inner_model_calls": len(r.result.solves) if r.result else None,
                }
                for r in state["native_reports"]
            ],
            "limits": {
                "independent_confirmation": "not_admitted",
                "training": "not_admitted",
                "execution": "trusted_supplied_only",
            },
        }
        if self.workflow_route == "single_agent":
            calls = [c for c in self.store.replay().invocations.values() if c.state == "completed"]
            history = []
            for call in calls[-4:]:
                item = {"invocation_id": call.id, "handoff": self.scheduler.handoff(call).to_dict()}
                if len(canonical_json([*history, item]).encode()) <= 8192:
                    history.append(item)
            summary["agent_history"] = history
            summary["history_policy"] = {
                "version": "single-agent-history-1.0",
                "max_handoffs": 4,
                "max_bytes": 8192,
                "included_invocation_ids": [item["invocation_id"] for item in history],
                "raw_transcripts_included": False,
            }
        return summary

    def _mechanical(self, role, key, context, validate):
        host = self.scheduler.host
        store = self.suite_store
        with nullcontext() if store._locked else store.writer():
            previous = store.replay()["mechanical_steps"].get((self.cell_digest, role, key))
            if previous:
                claim = read_mechanical(store.root, previous)
            else:
                self._require_time()
                summary = self.summary()
                if context is not None:
                    summary["submitted_handoff"] = context
                    if "native_failure" in context:
                        summary["evaluations"].append(context["native_failure"])
                        summary["mandatory_checks"] = []
                ref = put_bytes(
                    store.root,
                    canonical_json(summary).encode(),
                    name="mechanical-context.json",
                    media_type="application/json",
                    producer="engineering-mechanical",
                )
                output = mechanical_output(role, summary, ref.sha256)
                if validate:
                    validate(MechanicalReply(output))
                claim = MechanicalClaim(host.plan_ref, role, key, ref, output)
                ref = put_bytes(
                    store.root,
                    claim.to_json().encode(),
                    name="mechanical-step.json",
                    media_type="application/json",
                    producer="engineering-mechanical",
                )
                store.append(
                    request_id="mechanical-"
                    + digest({"cell": self.cell_digest, "role": role, "key": key})[:48],
                    operation="mechanical_step",
                    cell_digest=self.cell_digest,
                    attempt_id=host.allocation.attempt_id,
                    child_digest=host.allocation.child_digest,
                    result_digest=ref.sha256,
                )
        reply = MechanicalReply(claim.output)
        if validate:
            validate(reply)
        return reply

    def _role(self, role, key, question, *, context=None, validate=None, **kwargs):
        key = str(key)
        if role == self.omitted:
            return self._mechanical(role, key, context, validate)
        if self.workflow_route == "single_agent":
            expected = {
                "investigator": CandidateBrief,
                "implementer": SuppliedConfiguration,
                "reviewer": ReviewFindings,
            }[role]

            def check(value):
                if isinstance(value.output, NextStep):
                    if role != "investigator" or value.output.action != "freeze":
                        raise ValueError(
                            "single-agent control action differs from engineering phase"
                        )
                elif not isinstance(value.output, expected):
                    raise ValueError("single-agent engineering output type differs")
                elif validate:
                    validate(value)

            return CampaignBroker._role(
                self,
                "single_agent",
                role + ":" + key,
                question,
                context=context,
                validate=check,
                expected_schema="role-handoff-1.2",
                **kwargs,
            )
        return CampaignBroker._role(
            self, role, key, question, context=context, validate=validate, **kwargs
        )

    def _coordinate(self, key, role, *, may_freeze=False):
        if self.workflow_route == "single_agent":
            return False

        def validate(value):
            if not isinstance(value.output, NextStep) or not (
                (value.output.action == "assign" and value.output.role == role)
                or (may_freeze and value.output.action == "freeze")
            ):
                raise ValueError("engineering coordinator proposed a different stage")

        handoff = self._role(
            "orchestrator", key, "Assign the declared engineering stage or stop.", validate=validate
        )
        return handoff.output.action == "freeze"

    def _review_rows(self, implementation):
        state = self.controller.state()
        if implementation == "calibration":
            return [
                _public_evaluation(v)
                for v in state["evaluations"]
                if v.evaluation.id.startswith("eval-")
            ]
        if implementation == "native":
            rows = [
                _public_evaluation(v)
                for v in state["evaluations"]
                if v.evaluation.id.startswith("native-choice-")
            ]
            if rows:
                return rows
            report = state["native_reports"][-1]
            return [
                {
                    "id": "native-report-" + report.digest[:24],
                    "kind": "native_proposal_failure",
                    "status": report.status,
                    "metrics": {},
                    "checks": [],
                }
            ]
        action = self.controller.spec.action(implementation)
        return [_public_evaluation(v) for v in state["evaluations"] if v.evaluation.id == action.id]

    def advance(self, *, resume_scenarios=False):
        if type(resume_scenarios) is not bool:
            raise ValueError("engineering scenario continuation must be explicitly boolean")
        self._resume_scenarios = resume_scenarios
        try:
            return self._advance()
        finally:
            self._resume_scenarios = False

    def _advance(self):
        self.reconcile_actions()
        if self.controller.store.replay().state == "selection_frozen":
            return self.controller.state()
        self.request("evaluate", {"candidate_id": "baseline", "mode": "fixed"}, key="baseline")
        self.proposals = []
        advised_freeze = False
        for slot in range(len(self.catalogue)):
            self.phase = "proposal_open"
            if self._coordinate("investigate:" + str(slot), "investigator", may_freeze=True):
                advised_freeze = True
                break

            def brief_check(value):
                out = value.output
                if (
                    not isinstance(out, CandidateBrief)
                    or out.target != "engineering"
                    or out.eligibility_gaps
                    or out.implementation_id not in {i["implementation_id"] for i in self.catalogue}
                    or out.implementation_id in {p.implementation_id for p in self.proposals}
                    or out.candidate_id in {p.candidate_id for p in self.proposals}
                ):
                    raise ValueError("engineering brief expands or repeats supplied choices")

            brief = self._role(
                "investigator",
                str(slot),
                "Propose one untried registered engineering choice or stop.",
                validate=brief_check,
            )
            if isinstance(brief.output, NextStep):
                advised_freeze = True
                break
            item = next(
                i
                for i in self.catalogue
                if i["implementation_id"] == brief.output.implementation_id
            )
            self.phase = "candidate_pending"
            self._coordinate("implement:" + str(slot), "implementer")

            def configuration_check(value):
                out = value.output
                if (
                    not isinstance(out, SuppliedConfiguration)
                    or out.candidate_id != brief.output.candidate_id
                    or out.implementation_id != item["implementation_id"]
                    or dict(out.parameters) != item["parameters"]
                ):
                    raise ValueError(
                        "engineering implementation overrides frozen configuration/recipe"
                    )

            configured = self._role(
                "implementer",
                str(slot),
                "Return the exact supplied configuration or registered recipe.",
                candidate_id=brief.output.candidate_id,
                context=_proposal(brief.output),
                validate=configuration_check,
            )
            self.request(
                "evaluate",
                {"candidate_id": item["implementation_id"], "mode": item["mode"]},
                key="choice:" + str(slot),
                invocation_id=getattr(configured, "invocation_id", None),
            )
            rows = self._review_rows(item["implementation_id"])
            if not rows:
                raise WorkflowStopped(
                    "engineering choice has no original evaluation/attempt evidence"
                )
            self.phase = "evidence_ready"
            for row in rows:
                self._coordinate("review:" + row["id"], "reviewer")
                context = {"proposal": _proposal(brief.output), "evaluation_id": row["id"]}
                if row["kind"] == "native_proposal_failure":
                    context["native_failure"] = row

                def review_check(value):
                    out = value.output
                    names = {c["name"] for c in row["checks"]}
                    if isinstance(out, ReviewFindings) and any(
                        not set(f.supporting_checks) <= names for f in out.findings
                    ):
                        raise ValueError(
                            "engineering review names checks outside its original evidence"
                        )
                    if (
                        not isinstance(out, ReviewFindings)
                        or out.candidate_id != brief.output.candidate_id
                        or out.evaluation_id != row["id"]
                    ):
                        raise ValueError("engineering advisory review context differs")

                reviewed = self._role(
                    "reviewer",
                    row["id"],
                    "Review this original engineering result, including failed checks.",
                    candidate_id=brief.output.candidate_id,
                    evaluation_id=row["id"],
                    context=context,
                    validate=review_check,
                )
                if (
                    reviewed.output.recommendation != "proceed"
                    or reviewed.output.missing_evidence
                    or any(f.severity == "blocking" for f in reviewed.output.findings)
                ):
                    raise WorkflowStopped("engineering advisory review stopped the workflow")
            self.proposals.append(brief.output)
        self.phase = "proposal_open"
        if self.workflow_route != "single_agent" and not advised_freeze:
            if not self._coordinate("freeze", "investigator", may_freeze=True):
                raise WorkflowStopped("engineering route has no remaining supplied choice")
        elif (
            self.workflow_route == "single_agent"
            and not advised_freeze
            and len(self.proposals) == len(self.catalogue)
        ):
            value = self._role(
                "investigator", "freeze", "The candidate allowance is exhausted. Freeze or stop."
            )
            if not isinstance(value.output, NextStep) or value.output.action != "freeze":
                raise WorkflowStopped("single agent did not freeze exhausted engineering choices")
        self.request("review", key="review")
        self.request("freeze", key="freeze")
        return self.controller.state()

    def stage(self, *args, **kwargs):
        raise StoreError("engineering broker does not stage generated scientific records")

    def prepare_implementation(self, *args, **kwargs):
        raise StoreError("engineering broker supports supplied configurations only")

    def dispose_review(self, *args, **kwargs):
        raise StoreError(
            "engineering advisory stop requires a separate admitted disposition profile"
        )
