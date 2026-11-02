"""Bounded JSON tool boundary and durable request idempotency."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import hashlib
import uuid

from .records import ArtifactRef, CampaignEvent, Request, Response, Scalar, identifier
from .serialization import canonical_json, digest, unique_json
from .spec import CampaignSpec
from .store import EventStore, Projection, durable_write, WriterBusy


class CampaignError(ValueError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class TransitionRule:
    owner: str
    preconditions: tuple[str, ...]
    destinations: tuple[str, ...]
    result_schema: str
    retry_allowance: int
    stop_rule: str


TRANSITIONS = {
    "diagnostics": TransitionRule(
        "controller",
        ("baseline_ready",),
        ("proposal_open",),
        "diagnostic_artifact",
        2,
        "missing_diagnostics",
    ),
    "propose": TransitionRule(
        "controller",
        ("proposal_open",),
        ("candidate_pending",),
        "proposal_artifact",
        2,
        "candidate_limit",
    ),
    "admit": TransitionRule(
        "controller",
        ("candidate_pending",),
        ("candidate_ready", "proposal_open"),
        "snapshot_or_rejection",
        2,
        "admission_rejected",
    ),
    "evaluate": TransitionRule(
        "controller",
        ("created", "candidate_ready", "evaluating"),
        (
            "created",
            "candidate_ready",
            "evaluating",
            "baseline_ready",
            "evidence_ready",
            "reconciliation_required",
            "completed",
        ),
        "evaluation_record",
        0,
        "budget_or_execution_failure",
    ),
    "review": TransitionRule(
        "controller",
        ("evidence_ready", "reconciliation_required"),
        (
            "proposal_open",
            "selection_frozen",
            "evidence_ready",
            "evaluating",
            "completed",
            "report_ready",
            "reconciliation_required",
        ),
        "decision_or_reconciliation",
        2,
        "insufficient_evidence",
    ),
    "freeze": TransitionRule(
        "controller",
        ("proposal_open",),
        ("selection_frozen",),
        "frozen_selection",
        0,
        "selection_immutable",
    ),
    "confirm": TransitionRule(
        "controller",
        ("selection_frozen", "evaluating"),
        ("selection_frozen", "report_ready", "reconciliation_required", "completed"),
        "confirmation_record",
        0,
        "one_shot_confirmation",
    ),
    "report": TransitionRule(
        "controller", ("report_ready",), ("completed",), "report_artifact", 0, "completed"
    ),
}

# Required and optional payload fields. Artifact IDs never become import paths or commands.
PAYLOAD_FIELDS = {
    "state": (set(), set()),
    "diagnostics": ({"artifact_id"}, {"repair_of"}),
    "propose": ({"proposal_id"}, {"repair_of"}),
    "admit": ({"snapshot_id"}, {"repair_of"}),
    "evaluate": ({"candidate_id", "mode"}, set()),
    "review": (set(), {"evaluation_id", "reconcile_attempt_id", "repair_of"}),
    "freeze": (set(), set()),
    "confirm": (set(), set()),
    "cancel": (set(), set()),
    "report": (set(), set()),
}


@dataclass(frozen=True)
class Transition:
    state: str
    result: Mapping[str, Scalar]
    artifacts: tuple[ArtifactRef, ...] = ()


class CampaignService:
    """Trusted handlers own scientific work. Default callers have read-only authority.

    A broker supplies handlers and explicitly enables scientific commands. No handler is
    derived from request text. The single writer remains held during a scientific command;
    the separate cancellation inbox remains writable without that lock.
    """

    def __init__(
        self,
        store: EventStore,
        spec: CampaignSpec,
        *,
        handlers: Mapping[str, Callable[[Request, Projection], Transition]] | None = None,
        allow_scientific: bool = False,
        cancel_handler: Callable | None = None,
        report_reader: Callable | None = None,
    ):
        self.store, self.spec = store, spec
        self.handlers = dict(handlers or {})
        self.allow_scientific = allow_scientific
        self.cancel_handler, self.report_reader = cancel_handler, report_reader

    def _response(self, request_id, code, revision):
        return Response(request_id, "error", revision, {}, code, ())

    def _used(self, projection):
        return sum(
            not event.response.request_id.startswith("internal-") for event in projection.events
        ) + len(tuple((self.store.root / "control").glob("transport-*.json")))

    def _side_rejection(self, request, code, revision):
        # Conflicting logical IDs cannot be inserted twice in the domain journal.
        # Keep a bounded, digest-addressed transport receipt instead.
        receipt_id = digest({"request": request.digest, "error": code})
        path = self.store.root / "control" / f"transport-{receipt_id}.json"
        if path.is_file() and not path.is_symlink():
            return Response.from_dict(unique_json(path.read_text())["response"])
        try:
            with self.store.writer():
                projection = self.store.replay()
                response = self._response(request.request_id, code, revision)
                if self._used(projection) >= self.spec.workflow.max_transport_requests:
                    return self._response(
                        request.request_id, "budget_exhausted", projection.revision
                    )
                if not path.exists():
                    durable_write(
                        path,
                        canonical_json(
                            {"request_digest": request.digest, "response": response.to_dict()}
                        ).encode(),
                    )
                return response
        except WriterBusy:
            # A running owner cannot be displaced by a duplicate or conflicting caller.
            return self._response(request.request_id, code, revision)

    def _repair(self, request: Request, projection: Projection) -> tuple[str, int]:
        return self._repair_values(request.request_id, request.payload, projection)

    def _repair_values(self, request_id, payload, projection):
        repaired = payload.get("repair_of") if isinstance(payload, Mapping) else None
        if repaired is None:
            return request_id, 0
        if not isinstance(repaired, str):
            raise CampaignError("schema_error")
        previous = projection.responses.get(repaired)
        if previous is None or previous[1].status != "error":
            raise CampaignError("schema_error")
        result = previous[1].result
        root = result.get("repair_root", repaired)
        count = result.get("repair_count", 0) + 1
        # Count all prior repairs in this lineage, including branching repairs.
        count = max(
            count,
            1
            + sum(
                event.response.result.get("repair_root") == root
                and event.response.result.get("repair_count", 0) > 0
                for event in projection.events
            ),
        )
        return root, count

    def _commit(
        self,
        request: Request,
        projection: Projection,
        transition: Transition,
        error: str | None = None,
    ) -> Response:
        projection = self.store.replay()
        revision = projection.revision + 1
        result = dict(transition.result)
        response = Response(
            request.request_id,
            "error" if error else "ok",
            revision,
            result,
            error,
            tuple(ref.sha256 for ref in transition.artifacts),
        )
        event = CampaignEvent(
            revision,
            request.digest,
            projection.head_hash,
            "controller",
            request.operation,
            projection.state,
            transition.state,
            response,
            transition.artifacts,
        )
        return self.store.commit(event)

    def handle(self, request: Request) -> Response:
        projection = self.store.replay()
        if request.request_id.startswith("internal-"):
            return self._side_rejection(request, "schema_error", projection.revision)
        previous = projection.responses.get(request.request_id)
        if previous is not None:
            if previous[0] == request.digest:
                return previous[1]
            return self._side_rejection(request, "request_conflict", projection.revision)
        if request.operation == "state":
            if request.campaign_id != self.spec.name:
                return self._side_rejection(request, "identity_mismatch", projection.revision)
            if request.payload:
                return self._side_rejection(request, "schema_error", projection.revision)
            return Response(
                request.request_id, "ok", projection.revision, {"state": projection.state}, None, ()
            )
        if request.operation == "cancel" or (
            request.operation == "report" and projection.state != "report_ready"
        ):
            if request.campaign_id != self.spec.name or request.payload:
                return self._side_rejection(request, "schema_error", projection.revision)
            callback = self.cancel_handler if request.operation == "cancel" else self.report_reader
            if callback is None:
                return self._side_rejection(request, "invalid_transition", projection.revision)
            return callback(request, projection)
        if not self.allow_scientific:
            return self._side_rejection(request, "invalid_transition", projection.revision)
        with self.store.writer():
            projection = self.store.replay()
            previous = projection.responses.get(request.request_id)
            if previous is not None:
                if previous[0] == request.digest:
                    return previous[1]
                return self._response(request.request_id, "request_conflict", projection.revision)
            if self._used(projection) >= self.spec.workflow.max_transport_requests:
                return self._response(request.request_id, "budget_exhausted", projection.revision)
            if request.campaign_id != self.spec.name:
                return self._commit(
                    request, projection, Transition(projection.state, {}), "identity_mismatch"
                )
            if request.expected_revision != projection.revision:
                return self._commit(
                    request, projection, Transition(projection.state, {}), "stale_revision"
                )
            root, count = request.request_id, 0
            try:
                root, count = self._repair(request, projection)
                if count > self.spec.workflow.max_repairs:
                    raise CampaignError("budget_exhausted")
                required, optional = PAYLOAD_FIELDS[request.operation]
                if (
                    set(request.payload) - required - optional
                    or required - set(request.payload)
                    or any(not isinstance(value, str) for value in request.payload.values())
                ):
                    raise CampaignError("schema_error")
                if request.operation == "evaluate" and request.payload["mode"] not in (
                    "fixed",
                    "calibrate",
                ):
                    raise CampaignError("schema_error")
                rule = TRANSITIONS.get(request.operation)
                if projection.state == "reconciliation_required" and request.operation != "review":
                    raise CampaignError("reconciliation_required")
                if rule is None or projection.state not in rule.preconditions:
                    raise CampaignError("invalid_transition")
                handler = self.handlers.get(request.operation)
                if handler is None:
                    raise CampaignError("invalid_transition")
                transition = handler(request, projection)
                if transition.state not in rule.destinations:
                    raise RuntimeError("trusted handler violated its transition contract")
                result = dict(transition.result, repair_root=root, repair_count=count)
                return self._commit(
                    request, projection, Transition(transition.state, result, transition.artifacts)
                )
            except CampaignError as error:
                return self._commit(
                    request,
                    projection,
                    Transition(
                        self.store.replay().state,
                        {
                            "repair_root": root,
                            "repair_count": count,
                        },
                    ),
                    error.code,
                )

    def request_json(self, text: str) -> str:
        try:
            request = Request.from_json(text)
        except (ValueError, TypeError, UnicodeError):
            # A well-formed JSON object with a valid logical ID is a rejected
            # domain command, even when its fields/operation are unsupported.
            parsed = None
            try:
                if len(text.encode()) <= 65536:
                    parsed = unique_json(text)
                if not isinstance(parsed, dict):
                    raise ValueError("not an envelope")
                identifier(parsed.get("request_id"))
                if parsed["request_id"].startswith("internal-"):
                    raise ValueError("reserved request namespace")
            except (ValueError, TypeError, UnicodeError):
                parsed = None
            if parsed is not None:
                request_id, request_digest = parsed["request_id"], digest(parsed)
                with self.store.writer():
                    projection = self.store.replay()
                    previous = projection.responses.get(request_id)
                    if previous is not None:
                        if previous[0] == request_digest:
                            return previous[1].to_json()
                        response = self._response(
                            request_id, "request_conflict", projection.revision
                        )
                        path = self.store.root / "control" / f"transport-{request_digest}.json"
                        if path.exists():
                            return Response.from_dict(
                                unique_json(path.read_text())["response"]
                            ).to_json()
                        if self._used(projection) >= self.spec.workflow.max_transport_requests:
                            return self._response(
                                request_id, "budget_exhausted", projection.revision
                            ).to_json()
                        durable_write(
                            path,
                            canonical_json(
                                {"request_digest": request_digest, "response": response.to_dict()}
                            ).encode(),
                        )
                        return response.to_json()
                    if self._used(projection) >= self.spec.workflow.max_transport_requests:
                        return self._response(
                            request_id, "budget_exhausted", projection.revision
                        ).to_json()
                    root, count, code = request_id, 0, "schema_error"
                    try:
                        root, count = self._repair_values(
                            request_id, parsed.get("payload"), projection
                        )
                        if count > self.spec.workflow.max_repairs:
                            code = "budget_exhausted"
                    except CampaignError as error:
                        code = error.code
                    response = Response(
                        request_id,
                        "error",
                        projection.revision + 1,
                        {"repair_root": root, "repair_count": count},
                        code,
                        (),
                    )
                    event = CampaignEvent(
                        response.revision,
                        request_digest,
                        projection.head_hash,
                        "controller",
                        "rejected",
                        projection.state,
                        projection.state,
                        response,
                        (),
                    )
                    return self.store.commit(event).to_json()
            return self.reject_transport(text.encode(errors="replace"))
        return self.handle(request).to_json()

    def request_bytes(self, raw: bytes) -> str:
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            return self.reject_transport(raw)
        return self.request_json(text)

    def reject_transport(self, raw: bytes) -> str:
        """Keep byte provenance, without storing untrusted or private transport content."""
        transport_id = f"transport-{uuid.uuid4().hex}"
        with self.store.writer():
            projection = self.store.replay()
            code = "budget_exhausted"
            if self._used(projection) < self.spec.workflow.max_transport_requests:
                durable_write(
                    self.store.root / "control" / f"{transport_id}.json",
                    canonical_json(
                        {
                            "id": transport_id,
                            "size_bytes": len(raw),
                            "sha256": hashlib.sha256(raw).hexdigest(),
                            "status": "schema_error",
                        }
                    ).encode(),
                )
                code = "schema_error"
        return self._response(transport_id, code, projection.revision).to_json()
