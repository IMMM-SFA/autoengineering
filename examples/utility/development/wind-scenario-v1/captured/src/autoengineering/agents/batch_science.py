"""A trusted campaign controller that reserves shared batch science starts.

Scientific rules, budgets, execution and recovery remain in CampaignController.
The batch charge is never refunded when the inner campaign charges zero cost.
"""

from __future__ import annotations

import hashlib

from autoengineering.campaign.artifacts import read_bytes
from autoengineering.campaign.controller import CampaignController
from autoengineering.campaign.execution import live_members
from autoengineering.campaign.serialization import digest, unique_json
from autoengineering.campaign.store import StoreError

from .batch import BatchStore, PhysicalObservation, PhysicalReservation


class BatchCampaignController(CampaignController):
    def __init__(self, store, spec, *, batch: BatchStore, case_id: str, **kwargs):
        self.batch, self.case_id = batch, case_id
        if case_id not in {case.id for case in batch.spec.cases}:
            raise StoreError("scientific case is absent from frozen batch")
        if batch._trusted_pin != batch.digest:
            raise StoreError("scientific batch controller requires a caller-pinned manifest")
        if not store.root.resolve().is_relative_to(batch.root / "cases" / case_id):
            raise StoreError("scientific campaign lies outside its frozen batch case")
        super().__init__(store, spec, **kwargs)

    def _batch_key(self, attempt_id):
        return (
            "science-"
            + digest({"case": self.case_id, "campaign": self.spec.digest, "attempt": attempt_id})[
                :32
            ]
        )

    def _batch_observation(self, reservation, attempt_id):
        state = self.state()
        attempt = next((a for a in state.budget.attempts if a.id == attempt_id), None)
        if attempt is None or attempt.receipt is None:
            raise StoreError("scientific batch result lacks original attempt evidence")
        raw = read_bytes(self.store.root, attempt.receipt, max_bytes=65536)
        receipt = unique_json(raw.decode())
        identity = receipt.get("identity", {})
        stopped = (
            attempt.state in ("finished", "reconciled")
            and not attempt.uncertain_cost
            and receipt.get("stopped") is True
            and identity.get("nonce") == attempt.launch_nonce
            and type(identity.get("pgid")) is int
            and identity.get("pgid") == identity.get("pid")
            and not live_members(identity["pgid"])
        )
        evaluation = next((v for v in state.evaluations if v.attempt_id == attempt_id), None)
        status = evaluation.status if evaluation is not None else receipt["status"]
        proof = self.batch.evidence(
            {
                "kind": "campaign_attempt_observation",
                "campaign": self.spec.digest,
                "scope": str(self.store.root),
                "attempt": attempt.to_dict(),
                "receipt_sha256": hashlib.sha256(raw).hexdigest(),
                "stop_verified": stopped,
                "evaluation_status": status,
            }
        )
        return PhysicalObservation(
            reservation.id,
            status if stopped else "reconciliation_required",
            stopped,
            0,
            {},
            None,
            "not_applicable",
            attempt.elapsed_seconds,
            (proof,),
        )

    def _physical_attempt(
        self, model_id, model, adapter_id, parameters, role, reservation_id, **kwargs
    ):
        if self.remaining is not None and self.remaining < 1:
            return None
        attempt_id = f"attempt-{len(self.state().budget.attempts) + 1:06d}"
        identity = digest(
            {
                "case": self.case_id,
                "campaign": self.spec.digest,
                "attempt": attempt_id,
                "model_id": model_id,
                "model": model.digest,
                "adapter": adapter_id,
                "parameters": dict(parameters),
                "role": role,
                "reservation": reservation_id,
                "options": {
                    k: v.to_dict() if hasattr(v, "to_dict") else v for k, v in kwargs.items()
                },
            }
        )
        reservation = PhysicalReservation(
            self._batch_key(attempt_id),
            self.case_id,
            "science",
            identity,
            None,
            self.batch.clock(),
            self.spec.execution.timeout_seconds,
            0,
            0,
            0,
        )
        return self.batch.execute(
            reservation,
            lambda _: super(BatchCampaignController, self)._physical_attempt(
                model_id, model, adapter_id, parameters, role, reservation_id, **kwargs
            ),
            lambda r, _: self._batch_observation(r, attempt_id),
        )

    def reconcile_batch(self):
        """Read underlying recovery receipts. Never start a replacement evaluation."""
        with self.batch.operation():
            self.recover()
            attempts = {self._batch_key(a.id): a for a in self.state().budget.attempts}
            for reservation in self.batch.replay().pending:
                if reservation.resource != "science" or reservation.case_id != self.case_id:
                    continue
                attempt = attempts.get(reservation.id)
                if attempt is None:
                    raise StoreError("scientific reservation has no committed original attempt")
                self.batch.observe(self._batch_observation(reservation, attempt.id))
