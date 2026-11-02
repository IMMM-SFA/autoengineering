"""Engineering scientific tools over existing event, optimizer and batch stores.

Only trusted supplied scalar models on exposed development scenarios are admitted.
A route broker may call these tools. This module does not implement a host route.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Literal

from autoengineering.campaign.artifacts import confined_file, put_bytes, read_bytes
from autoengineering.campaign.records import (
    ArtifactRef,
    CampaignEvent,
    DecisionRecord,
    ModelSnapshot,
    Request,
    Response,
    Scalar,
)
from autoengineering.campaign.serialization import Record, canonical_json, digest, unique_json
from autoengineering.campaign.store import EventStore, StoreError, checked_directory, durable_write
from autoengineering.optimization import EvaluationAction
from .confirmation import SelectedState
from .contracts import identifier
from .engineering_process import (
    EngineeringExecutionSpec,
    engineering_invocation_identity,
    EngineeringScenarioJob,
    EngineeringScenarioResult,
    SupervisedEngineeringExecutor,
)
from .engineering_native import (
    NativeDriverSpec,
    NativeDriverReport,
    SupervisedNativeDriver,
    verify_native_report,
)
from .outcomes import EngineeringEvaluation, engineering_decision
from .studies import EngineeringReconciliationRequired, EngineeringStudy


@dataclass(frozen=True)
class EngineeringDesign(Record):
    id: str
    configuration: Mapping[str, Scalar]

    def _validate(self):
        identifier(self.id)
        if self.id in ("baseline", "calibration"):
            raise ValueError("engineering design uses a reserved identity")


@dataclass(frozen=True)
class EngineeringCampaignSpec(Record):
    schema: Literal["utility-engineering-campaign-v1"]
    name: str
    execution: EngineeringExecutionSpec
    model: ModelSnapshot
    baseline_configuration: Mapping[str, Scalar]
    designs: tuple[EngineeringDesign, ...]
    max_requests: int
    purpose: Literal["exposed_development_only"] = "exposed_development_only"

    def _validate(self):
        identifier(self.name)
        if len({item.id for item in self.designs}) != len(self.designs):
            raise ValueError("engineering designs need unique identities")
        space = self.execution.study.run.search_space
        for configuration in (
            self.baseline_configuration,
            *(d.configuration for d in self.designs),
        ):
            space.encode(configuration)
        declared = {ref.path: ref for ref in (*self.execution.sources, self.execution.lock)}
        if any(declared.get(ref.path) != ref for ref in self.model.source_bundle):
            raise ValueError("engineering model sources differ from execution closure")
        if any(port.dimensions for port in (*self.model.inputs, *self.model.outputs)):
            raise ValueError("engineering campaign supports scalar model ports only")
        if not 4 <= self.max_requests <= 1024:
            raise ValueError("engineering campaign request cap must be between 4 and 1024")

    @property
    def scientific_starts(self):
        return (
            1 + len(self.designs) + self.execution.study.run.study.budget.max_evaluations
        ) * len(self.execution.scenarios)

    def action(self, candidate):
        if candidate == "baseline":
            configuration = self.baseline_configuration
        else:
            design = next((item for item in self.designs if item.id == candidate), None)
            if design is None:
                raise StoreError("engineering design is outside the frozen catalogue")
            configuration = design.configuration
        return EvaluationAction.system(
            "fixed-" + digest({"campaign": self.digest, "candidate": candidate})[:32],
            configuration,
            seed=self.execution.study.run.study.seed,
            suggested_by="engineering-catalogue",
        )


@dataclass(frozen=True)
class EngineeringNativeCampaignSpec(EngineeringCampaignSpec):
    schema: Literal["utility-engineering-campaign-v2"]
    native: NativeDriverSpec | None = None

    def _validate(self):
        super()._validate()
        if self.native is None or self.native.execution != self.execution:
            raise ValueError("native campaign requires its exact scenario execution profile")
        if any(d.id == "native" for d in self.designs):
            raise ValueError("native is reserved for the registered driver")

    @property
    def scientific_starts(self):
        # One outer native process and fresh scenario evaluations. Inner calls
        # have their own frozen ceiling and are never counted as one model solve.
        return super().scientific_starts + 1 + len(self.execution.scenarios)

    def native_action(self, configuration):
        self.execution.study.run.search_space.encode(configuration)
        return EvaluationAction.system(
            "native-choice-" + self.digest[:32],
            configuration,
            seed=self.execution.study.run.study.seed,
            suggested_by="registered-native-driver",
        )


class EngineeringCampaign:
    """Durable scientific tools with no worker-controlled import or configuration."""

    def __init__(self, root, batch, *, executor=None, fault=lambda _: None):
        self.store = EventStore(root, fault=fault)
        self.batch, self.executor, self.fault = batch, executor, fault
        document = unique_json(confined_file(self.store.root, "engineering.json").read_text())
        kind = (
            EngineeringNativeCampaignSpec
            if document.get("schema") == "utility-engineering-campaign-v2"
            else EngineeringCampaignSpec
        )
        self.spec = kind.from_dict(document)
        self.identity = unique_json(confined_file(self.store.root, "identity.json").read_text())
        if (
            self.identity.get("campaign") != self.spec.digest
            or self.identity.get("batch") != batch.digest
        ):
            raise StoreError("engineering campaign or batch identity differs")
        self.case_id = self.identity["case_id"]
        case_root = batch.root / "cases" / self.case_id
        if (
            self.identity.get("root") != str(self.store.root)
            or unique_json(confined_file(case_root, "engineering-campaign.json").read_text())
            != self.identity
        ):
            raise StoreError("engineering campaign differs from its original case binding")
        if executor is not None and (
            not isinstance(executor, SupervisedEngineeringExecutor)
            or executor.spec != self.spec.execution
            or executor.batch.root != batch.root
            or executor.case_id != self.case_id
            or executor.binding_digest != self.identity["binding"]
        ):
            raise StoreError("engineering campaign executor differs from original binding")
        if executor is not None:
            prior_cancelled = executor.cancelled
            executor.cancelled = lambda: prior_cancelled() or self._cancelled()
        self.service = self  # Shared broker request/recovery surface.
        self.state()  # Verify committed scientific evidence before serving any tool.

    @classmethod
    def create(cls, root, spec, executor, *, fault=lambda _: None):
        if executor.spec != spec.execution:
            raise StoreError("engineering campaign execution differs")
        case = next(item for item in executor.batch.spec.cases if item.id == executor.case_id)
        if case.scientific_starts < spec.scientific_starts:
            raise StoreError("batch cannot cover the complete engineering campaign reserve")
        identity = {
            "campaign": spec.digest,
            "batch": executor.batch.digest,
            "case_id": executor.case_id,
            "binding": executor.binding_digest,
            "root": str(Path(root).absolute()),
        }
        case_root = executor.batch.root / "cases" / executor.case_id
        with executor.batch.operation():
            if executor.batch.replay().active_case != executor.case_id:
                raise StoreError("engineering campaign requires its active case")
            binding = case_root / "engineering-campaign.json"
            if binding.exists():
                if unique_json(confined_file(case_root, binding.name).read_text()) != identity:
                    raise StoreError("engineering case already owns a different campaign")
            else:
                durable_write(binding, canonical_json(identity).encode())
        store = EventStore.create(root, fault=fault)
        durable_write(store.root / "engineering.json", spec.to_json().encode())
        durable_write(store.root / "identity.json", canonical_json(identity).encode())
        return cls(root, executor.batch, executor=executor, fault=fault)

    def _cancelled(self):
        return any((self.store.root / "control").glob("cancel-*.json"))

    def cancel(self, request_id):
        """Queue a revocation without waiting for an active scientific writer."""
        identifier(request_id)
        path = self.store.root / "control" / ("cancel-" + request_id + ".json")
        raw = canonical_json({"intent": "cancel"})
        try:
            durable_write(path, raw.encode())
        except FileExistsError:
            if confined_file(self.store.root, "control/" + path.name).read_text() != raw:
                raise StoreError("engineering cancellation intent differs")
        return {"request_id": request_id, "campaign_id": self.spec.name, "operation": "cancel"}

    def _ref(self, value, name):
        return put_bytes(
            self.store.root,
            value.to_json().encode(),
            name=name,
            media_type="application/json",
            producer="trusted-engineering",
        )

    def _verify_value(self, action, value):
        rules = self.spec.execution.study.rules
        engineering_decision(value, (), rules)
        self.spec.execution.study.run.search_space.encode(action.config)
        if (
            value.evaluation.id != action.id
            or value.evaluation.model_id != self.spec.model.digest
            or dict(value.evaluation.configuration) != dict(action.config)
            or tuple(s.scenario_id for s in value.scenarios)
            != self.spec.execution.study.scenario_ids
        ):
            raise StoreError("engineering result differs from original model, action or scenarios")
        state = self.batch.replay()
        statuses, seconds = [], 0.0
        for scenario, score in zip(self.spec.execution.scenarios, value.scenarios):
            identity = engineering_invocation_identity(
                self.spec.execution, action, scenario.scenario_id, self.case_id
            )
            directory = (
                self.batch.root / "cases" / self.case_id / "engineering-processes" / identity
            )
            # The original input root is part of the persisted execution binding.
            binding = unique_json(confined_file(directory.parent, "execution.json").read_text())
            if digest(binding) != self.identity["binding"]:
                raise StoreError("engineering physical execution binding changed")
            job = EngineeringScenarioJob(
                "utility-engineering-job-v1",
                self.spec.execution,
                action.id,
                action.config,
                action.seed,
                scenario.scenario_id,
                binding["source_root"],
                str(directory),
                self.identity["binding"],
            )
            reservation = state.reservations.get("science-" + identity[:32])
            observation = state.observations.get(reservation.id) if reservation else None
            if (
                reservation is None
                or reservation.case_id != self.case_id
                or reservation.resource != "science"
                or reservation.invocation_digest != identity
                or reservation.timeout_seconds != self.spec.execution.timeout_seconds + 5.0
                or observation is None
                or not observation.stop_verified
            ):
                raise StoreError("engineering result lacks original stopped physical evidence")
            proofs = [
                unique_json(read_bytes(self.batch.root, ref).decode())
                for ref in observation.evidence
            ]
            if len(proofs) != 1:
                raise StoreError("engineering result needs one original supervised receipt")
            proof = proofs[0]
            if (
                proof.get("profile") != "supervised-engineering-v1"
                or not proof.get("stop_verified")
                or proof.get("execution_digest") != self.spec.execution.digest
                or proof.get("status") != observation.status
                or proof.get("job_digest") != job.digest
                or score.forcing_digest != SupervisedEngineeringExecutor._forcing_digest(scenario)
            ):
                raise StoreError("engineering process receipt differs")
            if proof["result"] is None:
                if (
                    any(v is not None for v in score.values.values())
                    or observation.status == "success"
                ):
                    raise StoreError("failed engineering process acquired numeric outcomes")
            else:
                physical = EngineeringScenarioResult.from_dict(proof["result"])
                if physical.job_digest != job.digest or physical.score != score:
                    raise StoreError("engineering score differs from original process receipt")
            statuses.append(observation.status)
            seconds += observation.elapsed_seconds
        if (
            value.evaluation.status != next((s for s in statuses if s != "success"), "success")
            or value.evaluation.elapsed_seconds != seconds
        ):
            raise StoreError("engineering status or timing differs from physical evidence")

    def state(self):
        projection = self.store.replay()
        evaluations, decision, selected, native = {}, None, None, {}
        for event in projection.events:
            if event.response.status != "ok":
                continue
            if event.operation == "evaluate":
                decision = None
            for ref in event.artifacts:
                document = unique_json(read_bytes(self.store.root, ref).decode())
                if ref.path.endswith("engineering-values.json"):
                    for item in document["values"]:
                        action = EvaluationAction.from_dict(item["action"])
                        value = EngineeringEvaluation.from_dict(item["value"])
                        self._verify_value(action, value)
                        if action.id in evaluations and evaluations[action.id] != value:
                            raise StoreError("engineering evaluation identity was reused")
                        evaluations[action.id] = value
                    decision = None
                elif ref.path.endswith("engineering-native.json"):
                    if not isinstance(self.spec, EngineeringNativeCampaignSpec):
                        raise StoreError("native evidence requires engineering campaign v2")
                    report = NativeDriverReport.from_dict(document)
                    verify_native_report(self.batch, self.case_id, self.spec.native, report)
                    if report.reservation_id in native and native[report.reservation_id] != report:
                        raise StoreError("native report identity was reused")
                    native[report.reservation_id] = report
                elif ref.path.endswith("engineering-decision.json"):
                    decision = DecisionRecord.from_dict(document)
                    if decision != self._decision(tuple(evaluations.values())):
                        raise StoreError("engineering decision differs from committed evidence")
                elif ref.path.endswith("selected-state.json"):
                    selected = SelectedState.from_dict(document)
                    if (
                        decision is None
                        or selected.model != self.spec.model
                        or selected.evaluation != evaluations[decision.selected_id].evaluation
                    ):
                        raise StoreError("engineering selected state differs from decision")
        return {
            "projection": projection,
            "evaluations": tuple(evaluations.values()),
            "decision": decision,
            "selected": selected,
            "native_reports": tuple(native.values()),
        }

    def _decision(self, values):
        baseline_id = self.spec.action("baseline").id
        baseline = next((v for v in values if v.evaluation.id == baseline_id), None)
        if baseline is None:
            raise StoreError("engineering decision requires its original baseline")
        return engineering_decision(
            baseline, tuple(v for v in values if v is not baseline), self.spec.execution.study.rules
        )

    def _error(self, request, code, revision):
        return Response(request.request_id, "error", revision, {}, code, ())

    def handle(self, request, *, resume_scenarios=False):
        if type(resume_scenarios) is not bool:
            raise ValueError("engineering scenario continuation must be explicitly boolean")
        with self.store.writer():
            state = self.state()
            projection = state["projection"]
            previous = projection.responses.get(request.request_id)
            if previous:
                return (
                    previous[1]
                    if previous[0] == request.digest
                    else self._error(request, "request_conflict", projection.revision)
                )
            if request.campaign_id != self.spec.name:
                return self._error(request, "identity_mismatch", projection.revision)
            if request.operation == "state" and not request.payload:
                return Response(
                    request.request_id,
                    "ok",
                    projection.revision,
                    {"state": projection.state, "evaluations": len(state["evaluations"])},
                    None,
                    (),
                )
            if request.expected_revision != projection.revision:
                return self._error(request, "stale_revision", projection.revision)
            if projection.revision >= self.spec.max_requests:
                return self._error(request, "budget_exhausted", projection.revision)
            if projection.state in ("selection_frozen", "cancelled"):
                return self._error(request, "invalid_transition", projection.revision)
            if self.executor is None:
                raise StoreError("read-only engineering controller cannot mutate")
            if (
                self.batch._trusted_pin != self.batch.digest
                or self.batch.replay().active_case != self.case_id
            ):
                raise StoreError("engineering mutations require their pinned active batch case")
            pending = []
            for path in (self.store.root / "attempts").iterdir():
                checked_directory(path)
                if not any(path.iterdir()):
                    continue  # No durable request means this controller could not dispatch.
                intent = Request.from_json(confined_file(path, "request.json").read_text())
                if intent.request_id not in projection.responses:
                    pending.append(intent)
            if pending and (len(pending) != 1 or pending[0] != request):
                conflict = any(p.request_id == request.request_id for p in pending)
                return self._error(
                    request,
                    "request_conflict" if conflict else "reconciliation_required",
                    projection.revision,
                )
            if (
                self._cancelled()
                and request.operation != "cancel"
                and not (pending and request.operation == "evaluate" and not resume_scenarios)
            ):
                return self._error(request, "invalid_transition", projection.revision)
            if request.operation == "evaluate":
                if self.executor is None:
                    raise StoreError("read-only engineering controller cannot dispatch")
                if set(request.payload) != {"candidate_id", "mode"}:
                    return self._error(request, "schema_error", projection.revision)
                candidate, mode = request.payload["candidate_id"], request.payload["mode"]
                if not (
                    (
                        mode == "fixed"
                        and candidate in ("baseline", *(d.id for d in self.spec.designs))
                    )
                    or (mode == "calibrated" and candidate == "calibration")
                    or (
                        mode == "native"
                        and candidate == "native"
                        and isinstance(self.spec, EngineeringNativeCampaignSpec)
                    )
                ):
                    return self._error(request, "schema_error", projection.revision)
                if not state["evaluations"] and candidate != "baseline":
                    return self._error(request, "invalid_transition", projection.revision)
                directory = self.store.root / "attempts" / request.digest
                recovering = directory.exists() and any(directory.iterdir())
                if recovering:
                    if (
                        Request.from_json(confined_file(directory, "request.json").read_text())
                        != request
                    ):
                        raise StoreError("engineering request intent differs")
                else:
                    directory.mkdir(mode=0o700, exist_ok=True)
                    checked_directory(directory)
                    self.fault("engineering_campaign_before_intent")
                    durable_write(directory / "request.json", request.to_json().encode())
                refs = self._evaluate(request, state, recovering, resume_scenarios)
                destination, result = "evidence_ready", {"candidate_id": candidate}
                if mode == "native":
                    report = next(
                        ref for ref in refs if ref.path.endswith("engineering-native.json")
                    )
                    result["execution_status"] = NativeDriverReport.from_json(
                        read_bytes(self.store.root, report).decode()
                    ).status
            elif request.operation in ("review", "freeze") and not request.payload:
                if not state["evaluations"]:
                    return self._error(request, "invalid_transition", projection.revision)
                decision = self._decision(state["evaluations"])
                if request.operation == "review":
                    refs = (self._ref(decision, "engineering-decision.json"),)
                    destination, result = "selection_ready", {"outcome": decision.outcome}
                else:
                    if state["decision"] != decision:
                        return self._error(request, "invalid_transition", projection.revision)
                    chosen = next(
                        (
                            v
                            for v in state["evaluations"]
                            if v.evaluation.id == decision.selected_id
                        ),
                        None,
                    )
                    refs = (
                        ()
                        if chosen is None
                        else (
                            self._ref(
                                SelectedState(
                                    "utility-selected-state-v1",
                                    self.spec.model,
                                    chosen.evaluation.configuration,
                                    chosen.evaluation,
                                ),
                                "selected-state.json",
                            ),
                        )
                    )
                    destination, result = "selection_frozen", {"outcome": decision.outcome}
            elif request.operation == "cancel" and not request.payload:
                destination, result, refs = "cancelled", {"state": "cancelled"}, ()
            else:
                return self._error(request, "schema_error", projection.revision)
            revision = projection.revision + 1
            response = Response(
                request.request_id, "ok", revision, result, None, tuple(ref.sha256 for ref in refs)
            )
            self.fault("engineering_campaign_result_ready")
            return self.store.commit(
                CampaignEvent(
                    revision,
                    request.digest,
                    projection.head_hash,
                    "controller",
                    request.operation,
                    projection.state,
                    destination,
                    response,
                    refs,
                )
            )

    def _evaluate(self, request, state, recovering, resume_scenarios):
        candidate = request.payload["candidate_id"]
        pairs, native_refs = [], ()
        if request.payload["mode"] == "native":
            driver = SupervisedNativeDriver(self.spec.native, self.executor, fault=self.fault)
            report = driver.run(recover_only=recovering and not resume_scenarios)
            verify_native_report(self.batch, self.case_id, self.spec.native, report)
            native_refs = (self._ref(report, "engineering-native.json"),)
            if report.status != "success":
                return native_refs
            action = self.spec.native_action(report.result.configuration)
            existing = next((v for v in state["evaluations"] if v.evaluation.id == action.id), None)
            if existing is not None:
                pairs.append((action, existing))
            else:
                value = (
                    self.executor.recover_completed(action)
                    if recovering and not resume_scenarios
                    else self.executor(action)
                )
                pairs.append(
                    (
                        action,
                        replace(
                            value,
                            evaluation=replace(value.evaluation, model_id=self.spec.model.digest),
                        ),
                    )
                )
        elif request.payload["mode"] == "fixed":
            action = self.spec.action(candidate)
            existing = next((v for v in state["evaluations"] if v.evaluation.id == action.id), None)
            if existing is not None:
                pairs.append((action, existing))
            else:
                value = (
                    self.executor.recover_completed(action)
                    if recovering and not resume_scenarios
                    else self.executor(action)
                )
                pairs.append(
                    (
                        action,
                        replace(
                            value,
                            evaluation=replace(value.evaluation, model_id=self.spec.model.digest),
                        ),
                    )
                )
        else:
            bridge = EngineeringStudy(
                self.spec.execution.study,
                self.batch,
                self.case_id,
                self.executor,
                resume_scenarios=recovering and resume_scenarios,
            )
            if recovering and not resume_scenarios:
                bridge.run(max_new_evaluations=0)
                if bridge.study.stop_reason is None:
                    raise EngineeringReconciliationRequired(
                        "explicit continuation is required for incomplete calibration"
                    )
            else:
                bridge.run()
            for action, result in bridge.study.ledger.entries():
                document = unique_json(
                    confined_file(bridge.directory, action.id + "-result.json").read_text()
                )
                value = EngineeringEvaluation.from_json(
                    read_bytes(
                        self.batch.root, ArtifactRef.from_dict(document["evidence"])
                    ).decode()
                )
                if bridge._resolve(action) != result or result.to_dict() != document["result"]:
                    raise StoreError("calibration result differs from original optimization ledger")
                pairs.append(
                    (
                        action,
                        replace(
                            value,
                            evaluation=replace(value.evaluation, model_id=self.spec.model.digest),
                        ),
                    )
                )
        for action, value in pairs:
            self._verify_value(action, value)
        raw = {
            "values": [
                {"action": action.to_dict(), "value": value.to_dict()} for action, value in pairs
            ]
        }
        return (
            *native_refs,
            put_bytes(
                self.store.root,
                canonical_json(raw).encode(),
                name="engineering-values.json",
                media_type="application/json",
                producer="trusted-engineering",
            ),
        )
