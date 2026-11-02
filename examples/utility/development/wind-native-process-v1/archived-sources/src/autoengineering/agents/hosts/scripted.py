"""Deterministic four-role replies for offline integration fixtures.

This is a scripted comparator, not an LLM or evidence of agent utility.
"""

from __future__ import annotations

import json
from itertools import repeat

from autoengineering.agents.hosts.base import HostResult
from autoengineering.agents.hosts.fake import FakeHost
from autoengineering.agents.records import (
    CandidateBrief,
    NextStep,
    ReviewFindings,
    RoleHandoff,
    SuppliedConfiguration,
)


def supplied_reply(task, prompt, invocation_id):
    context = json.loads(prompt[prompt.index('{"approved_evidence"') :])
    evidence_id = context["approved_evidence"][0]["id"]
    summary = json.loads(context["approved_evidence"][0]["content"])
    if task.role == "orchestrator":
        phase = summary["state"]
        if phase == "candidate_pending":
            output = NextStep("assign", "implementer", "Prepare the supplied configuration")
        elif phase == "evidence_ready":
            output = NextStep("assign", "reviewer", "Inspect the approved evidence")
        else:
            tried = {
                (p["target"], p["implementation_id"]) for p in summary["proposed_interventions"]
            }
            remaining = [
                p
                for p in summary["catalogue"]
                if (p["target"], p["implementation_id"]) not in tried
            ]
            output = (
                NextStep("assign", "investigator", "Investigate the supplied pool")
                if remaining
                and not (phase == "proposal_open" and task.question.startswith("Recommend freeze"))
                else NextStep(
                    "freeze",
                    None,
                    "The candidate allowance is exhausted"
                    if remaining
                    else "The supplied pool is exhausted",
                )
            )
        action = output.action
    elif task.role == "investigator":
        tried = {(p["target"], p["implementation_id"]) for p in summary["proposed_interventions"]}
        item = next(
            p for p in summary["catalogue"] if (p["target"], p["implementation_id"]) not in tried
        )
        output = CandidateBrief(
            f"{item['target']}-{item['implementation_id']}",
            item["target"],
            item["implementation_id"],
            "Evaluate the supplied implementation and frozen parameter space",
            "Measure the declared comparison",
            (evidence_id,),
            (),
        )
        action = "propose"
    elif task.role == "implementer":
        proposal = summary["submitted_handoff"]
        item = next(
            p
            for p in summary["catalogue"]
            if (p["target"], p["implementation_id"])
            == (proposal["target"], proposal["implementation_id"])
        )
        output = SuppliedConfiguration(
            proposal["id"], item["implementation_id"], item["parameters"], (evidence_id,)
        )
        action = "configure"
    else:
        submitted = summary["submitted_handoff"]
        output = ReviewFindings(
            submitted["proposal"]["id"],
            submitted["evaluation_id"],
            (evidence_id,),
            (),
            (),
            "proceed",
        )
        action = "review"
    handoff = RoleHandoff(
        "1.0",
        f"handoff-{invocation_id}",
        task.id,
        invocation_id,
        task.role,
        task.campaign_revision,
        "complete",
        output,
        (evidence_id,),
        (),
        action,
    )
    return HostResult("completed", handoff.to_json(), None, {"total_tokens": None}, 0)


def single_supplied_reply(task, prompt, invocation_id):
    from dataclasses import replace
    from autoengineering.agents.records import TaskAssignment

    context = json.loads(prompt[prompt.index('{"approved_evidence"') :])
    summary = json.loads(context["approved_evidence"][0]["content"])
    phase = summary["state"]
    if phase == "proposal_open":
        tried = {(p["target"], p["implementation_id"]) for p in summary["proposed_interventions"]}
        remaining = [
            p for p in summary["catalogue"] if (p["target"], p["implementation_id"]) not in tried
        ]
        if not remaining or task.question.startswith("The candidate allowance is exhausted"):
            evidence = context["approved_evidence"][0]["id"]
            handoff = RoleHandoff(
                "1.2",
                f"handoff-{invocation_id}",
                task.id,
                invocation_id,
                "single_agent",
                task.campaign_revision,
                "complete",
                NextStep("freeze", None, "The supplied pool is exhausted"),
                (evidence,),
                (),
                "freeze",
            )
            return HostResult("completed", handoff.to_json(), None, {"total_tokens": None}, 0)
        role = "investigator"
    else:
        role = {"candidate_pending": "implementer", "evidence_ready": "reviewer"}[phase]
    # Reuse the authored scientific choice, but produce only a single-agent
    # handoff. No four-role tasks or invocations are created by this fixture.
    legacy = TaskAssignment(
        "1.0",
        task.id,
        task.run_id,
        role,
        None,
        task.campaign_revision,
        task.question,
        (),
        "role-handoff-1.0",
        (),
        task.deadline,
        0,
    )
    response = supplied_reply(legacy, prompt, invocation_id)
    handoff = RoleHandoff.from_json(response.raw_output)
    return replace(
        response, raw_output=replace(handoff, schema_version="1.2", role="single_agent").to_json()
    )


def scripted_host(route="four_role"):
    if route not in ("four_role", "single_agent"):
        raise ValueError("unsupported workflow route")
    return FakeHost(repeat(single_supplied_reply if route == "single_agent" else supplied_reply))
