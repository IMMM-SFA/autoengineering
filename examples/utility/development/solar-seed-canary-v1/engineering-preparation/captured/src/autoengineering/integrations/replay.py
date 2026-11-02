"""Serial ask/tell transcript for qualified disposable in-memory policies.

This strategy is unsuitable for remote clients or persistent trial databases.
Every fresh policy must reproduce saved asks from its identity and transcript.
No pickle, framework database, evaluator, retry or physical launch lives here.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
import fcntl
import os
from pathlib import Path
from typing import Literal, Protocol

from autoengineering.campaign.artifacts import confined_file
from autoengineering.campaign.records import Scalar, identifier, sha256
from autoengineering.campaign.serialization import Record
from autoengineering.campaign.store import checked_directory, durable_write

from .contracts import IntegrationSpec


@dataclass(frozen=True)
class Proposal(Record):
    external_id: str
    configuration: Mapping[str, Scalar]


@dataclass(frozen=True)
class Observation(Record):
    result_digest: str
    status: Literal[
        "success", "scientific_infeasible", "model_failure", "timeout", "infrastructure_failure"
    ]
    feasible: bool
    objective: float | None

    def _validate(self):
        sha256(self.result_digest)
        if self.status != "success" or not self.feasible:
            if self.objective is not None:
                raise ValueError("failed or infeasible trials cannot supply an objective")
        elif self.objective is None:
            raise ValueError("feasible success requires an objective")


@dataclass(frozen=True)
class Transition(Record):
    revision: int
    previous_digest: str
    action_id: str
    ledger_prefix_digest: str
    phase: Literal["ask_intent", "proposal", "tell_intent", "synchronized"]
    proposal: Proposal | None
    observation: Observation | None

    def _validate(self):
        identifier(self.action_id)
        sha256(self.previous_digest)
        sha256(self.ledger_prefix_digest)
        if self.revision < 1:
            raise ValueError("invalid transcript revision")
        if self.phase == "ask_intent":
            if self.proposal is not None or self.observation is not None:
                raise ValueError("ask intent must precede proposal and observation")
        elif self.proposal is None:
            raise ValueError("transition requires a proposal")
        if (self.phase in ("tell_intent", "synchronized")) != (self.observation is not None):
            raise ValueError("tell and synchronization require an observation")


class ReplayPolicy(Protocol):
    """Trusted implementation must have no durable or remote side effects."""

    def ask(self) -> Proposal: ...
    def tell(self, proposal: Proposal, observation: Observation) -> None: ...


class ReconciliationRequired(ValueError):
    pass


class ReplayJournal:
    def __init__(self, root: Path, identity: IntegrationSpec):
        self.root = checked_directory(root)
        self.identity = identity
        with self._writer():
            path = self.root / "identity.json"
            if path.exists():
                saved = IntegrationSpec.from_json(confined_file(self.root, path.name).read_text())
                saved.require_compatible(identity)
            else:
                if list(self.root.glob("transition-*.json")):
                    raise ReconciliationRequired("missing integration identity")
                durable_write(path, identity.to_json().encode())

    @contextmanager
    def _writer(self):
        checked_directory(self.root)
        fd = os.open(self.root / ".integration.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            yield
        finally:
            os.close(fd)

    def read(self) -> tuple[Transition, ...]:
        previous = self.identity.digest
        rows = []
        active = None
        completed = set()
        for index, path in enumerate(sorted(self.root.glob("transition-*.json")), 1):
            if path.name != f"transition-{index:08d}.json":
                raise ReconciliationRequired("missing or unexpected transcript entry")
            row = Transition.from_json(confined_file(self.root, path.name).read_text())
            if row.revision != index or row.previous_digest != previous:
                raise ReconciliationRequired("transcript hash chain differs")
            if row.phase == "ask_intent":
                if active is not None or row.action_id in completed:
                    raise ReconciliationRequired("overlapping or repeated action")
            else:
                expected = {"ask_intent": "proposal", "proposal": "tell_intent",
                            "tell_intent": "synchronized"}
                if active is None or expected.get(active.phase) != row.phase:
                    raise ReconciliationRequired("invalid transcript phase order")
                if (row.action_id, row.ledger_prefix_digest) != (
                    active.action_id, active.ledger_prefix_digest
                ):
                    raise ReconciliationRequired("action identity changed")
                if active.proposal is not None and active.proposal != row.proposal:
                    raise ReconciliationRequired("saved proposal changed")
                if active.observation is not None and active.observation != row.observation:
                    raise ReconciliationRequired("saved observation changed")
            active = row
            if row.phase == "synchronized":
                completed.add(row.action_id)
                active = None
            previous = row.digest
            rows.append(row)
        return tuple(rows)

    def _append(self, rows, action_id, prefix, phase, proposal=None, observation=None):
        row = Transition(
            len(rows) + 1, rows[-1].digest if rows else self.identity.digest,
            action_id, prefix, phase, proposal, observation,
        )
        durable_write(
            self.root / f"transition-{row.revision:08d}.json", row.to_json().encode()
        )
        return (*rows, row)

    def _restore(self, factory: Callable[[], ReplayPolicy], rows):
        policy = factory()
        pending = None
        for row in rows:
            if row.phase == "ask_intent":
                pending = policy.ask()
                if not isinstance(pending, Proposal):
                    raise ValueError("policy did not return a Proposal")
            elif row.phase == "proposal" and pending != row.proposal:
                raise ReconciliationRequired("policy replay differs from saved proposal")
            elif row.phase == "tell_intent":
                policy.tell(row.proposal, row.observation)
        return policy, pending

    def propose(self, action_id: str, prefix: str, factory: Callable[[], ReplayPolicy]) -> Proposal:
        with self._writer():
            rows = self.read()
            for row in rows:
                if row.action_id == action_id and row.phase == "proposal":
                    if row.ledger_prefix_digest != prefix:
                        raise ReconciliationRequired("proposal ledger prefix changed")
                    self._restore(factory, rows)
                    return row.proposal
            if rows and rows[-1].phase != "synchronized":
                last = rows[-1]
                if (last.action_id, last.ledger_prefix_digest, last.phase) != (
                    action_id, prefix, "ask_intent"
                ):
                    raise ReconciliationRequired("another external action is outstanding")
            else:
                rows = self._append(rows, action_id, prefix, "ask_intent")
            _, proposal = self._restore(factory, rows)
            if any(
                row.proposal is not None and row.proposal.external_id == proposal.external_id
                for row in rows if row.phase == "proposal"
            ):
                raise ReconciliationRequired("policy reused an external trial ID")
            self._append(rows, action_id, prefix, "proposal", proposal)
            return proposal

    def observe(
        self, action_id: str, observation: Observation, factory: Callable[[], ReplayPolicy],
        *, committed_result: Callable[[str, str], bool],
    ) -> None:
        """The caller verifies the exact result digest in its authoritative ledger."""
        with self._writer():
            rows = self.read()
            matching = [r for r in rows if r.action_id == action_id]
            if not matching or matching[-1].phase == "ask_intent":
                raise ReconciliationRequired("no saved proposal for result")
            last = matching[-1]
            if not committed_result(action_id, observation.result_digest):
                raise ReconciliationRequired("result is not committed in authoritative ledger")
            if last.observation is not None and last.observation != observation:
                raise ReconciliationRequired("conflicting observation")
            if last.phase == "synchronized":
                return
            if last.phase == "proposal":
                rows = self._append(rows, action_id, last.ledger_prefix_digest,
                                    "tell_intent", last.proposal, observation)
            self._restore(factory, rows)
            self._append(rows, action_id, last.ledger_prefix_digest,
                         "synchronized", last.proposal, observation)
