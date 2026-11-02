"""Scripted coordination respects a smaller candidate allowance than its pool."""

from dataclasses import replace
import json

import pytest

from autoengineering.agents.hosts.scripted import supplied_reply
from autoengineering.agents.records import RoleHandoff
from test_agent_contracts import task_assignment, H


@pytest.mark.parametrize(
    "question,action,role",
    [
        ("Recommend freeze or stop for this stage.", "freeze", None),
        ("Recommend investigator or stop for this stage.", "assign", "investigator"),
    ],
)
def test_scripted_orchestrator_obeys_controller_stage_with_untried_candidates(
    question, action, role
):
    task = replace(
        task_assignment(),
        role="orchestrator",
        question=question,
        allowed_operations=("freeze", "stop"),
    )
    first = {"target": "routing", "implementation_id": "first"}
    second = {"target": "routing", "implementation_id": "second"}
    summary = {
        "state": "proposal_open",
        "proposed_interventions": [first],
        "catalogue": [first, second],
    }
    prompt = json.dumps({"approved_evidence": [{"id": H, "content": json.dumps(summary)}]})
    result = supplied_reply(task, prompt, "invocation-one")
    handoff = RoleHandoff.from_json(result.raw_output)
    assert handoff.output.action == action and handoff.output.role == role
