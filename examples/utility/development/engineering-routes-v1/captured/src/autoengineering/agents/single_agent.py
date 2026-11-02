"""One supplied-only persona over the same trusted scientific transitions.

This route has advisory self-review, not an independent reviewer. Host calls,
private grants, repairs, scientific requests and recovery use the shared runtime.
"""

from __future__ import annotations

from dataclasses import replace

from autoengineering.campaign.artifacts import read_bytes
from autoengineering.campaign.serialization import canonical_json
from autoengineering.campaign.store import StoreError

from .broker import CampaignBroker
from .permissions import SINGLE_POLICY_DIGEST
from .records import CandidateBrief, NextStep, ReviewFindings, SINGLE_ROLE, SuppliedConfiguration
from .scheduler import template_digests

HISTORY_ITEMS = 4
HISTORY_BYTES = 8192


def single_agent_spec(template, *, run_id):
    """Explicitly derive a new worker identity, retaining scientific binding and limits."""
    return replace(
        template,
        schema_version="1.1",
        id=run_id,
        workflow_route="single_agent",
        role_templates=template_digests("single_agent"),
        tool_policy_digest=SINGLE_POLICY_DIGEST,
    )


class SingleAgentBroker(CampaignBroker):
    workflow_route = "single_agent"
    review_description = "self review"

    def summary(self):
        summary = super().summary()
        calls = [
            v
            for v in self.store.replay().invocations.values()
            if v.state == "completed" and v.normalized_output is not None
        ]
        history, included = [], []
        for call in calls[-HISTORY_ITEMS:]:
            item = {"invocation_id": call.id, "handoff": _history_handoff(call, self.store)}
            if len(canonical_json([*history, item]).encode()) <= HISTORY_BYTES:
                history.append(item)
                included.append(call.id)
        summary["agent_history"] = history
        summary["history_policy"] = {
            "version": "single-agent-history-1.0",
            "max_handoffs": HISTORY_ITEMS,
            "max_bytes": HISTORY_BYTES,
            "included_invocation_ids": included,
            "omitted_invocation_ids": [v.id for v in calls if v.id not in included],
            "raw_transcripts_included": False,
        }
        return summary

    def _coordinate(self, key, expected_role, *, may_freeze=False):
        # The one persona supplies these decisions directly. No orchestrator
        # handoff is manufactured or journaled for stages selected by the controller.
        phase = self.controller.store.replay().state
        if (
            may_freeze
            or {"candidate_pending": "implementer", "evidence_ready": "reviewer"}.get(phase)
            != expected_role
        ):
            raise StoreError("single-agent coordination is outside the current scientific phase")
        return None

    def _role(
        self, role, key, question, *, validate=None, expected_schema="role-handoff-1.0", **kwargs
    ):
        if expected_schema != "role-handoff-1.0" or role not in (
            "investigator",
            "implementer",
            "reviewer",
        ):
            raise StoreError("single-agent supplied stage is unsupported")
        expected = {
            "investigator": CandidateBrief,
            "implementer": SuppliedConfiguration,
            "reviewer": ReviewFindings,
        }[role]

        def check(value):
            if isinstance(value.output, NextStep):
                if role != "investigator" or value.output.action != "freeze":
                    raise ValueError("control action is outside the current single-agent stage")
                return
            if not isinstance(value.output, expected):
                raise ValueError("single-agent output differs from the current scientific phase")
            if validate is not None:
                validate(value)

        return super()._role(
            SINGLE_ROLE,
            f"{role}:{key}",
            question,
            validate=check,
            expected_schema="role-handoff-1.2",
            **kwargs,
        )

    def _propose_or_freeze(self, slot, can_investigate, validate):
        question = (
            "Propose an untried supplied intervention, freeze the current evidence or stop."
            if can_investigate
            else "The candidate allowance is exhausted. Freeze or stop."
        )

        def check(value):
            if not can_investigate:
                raise ValueError("candidate allowance exhausted")
            validate(value)

        return self._role("investigator", slot, question, validate=check)


def _history_handoff(call, store):
    # Only this persona's normalized output is copied, never raw transport bytes.
    from .records import RoleHandoff

    handoff = RoleHandoff.from_json(read_bytes(store.root, call.normalized_output).decode())
    if handoff.role != SINGLE_ROLE:
        raise StoreError("single-agent history contains a different role")
    return handoff.to_dict()
