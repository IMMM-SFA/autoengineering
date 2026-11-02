"""Offline native wind cost joins from original producer metadata.

Wire records are decoded here without importing example, source or model code.
These checks establish metadata consistency, not OS or scientific admission.
"""

from __future__ import annotations

import calendar
from dataclasses import dataclass
import hashlib
import math
import re
from typing import Literal

from autoengineering.campaign.artifacts import confined_file, read_bytes
from autoengineering.campaign.records import ArtifactRef
from autoengineering.campaign.serialization import Record, canonical_json, digest, unique_json
from autoengineering.campaign.store import StoreError
from .confirmation import read_selected_state
from .contracts import identifier, sha256
from .costs import CostRecord
from .outcomes import OutcomeSpec
from .scoring import ConfirmationGrant, PublicScore, _read, read_receipt, validate_grant

MODEL_FILES = (
    "examples/utility/wind_hourly.py",
    "examples/utility/wind_parameters.py",
    "examples/utility/wind.py",
    "examples/utility/wind_annual.py",
    "pixi.lock",
)


def _hours(year):
    if type(year) is not int or not 2007 <= year <= 2014:
        raise ValueError("wind evidence requires a declared historical source year")
    return 24 * (366 if calendar.isleap(year) else 365)


@dataclass(frozen=True)
class WindScorePolicy(Record):
    schema: Literal["utility-wind-annual-score-v1"]
    scorer_source_digest: str
    model_digest: str
    plan_digest: str

    def _validate(self):
        for value in (self.scorer_source_digest, self.model_digest, self.plan_digest):
            sha256(value)


@dataclass(frozen=True)
class _Source(Record):
    year: int
    source_version: Literal["v1.0.0", "v1.1.0"]
    object_key: str
    object_identity_digest: str
    point_manifest_digest: str

    def _validate(self):
        _hours(self.year)
        version = "v1.1.0" if self.year == 2014 else "v1.0.0"
        if (
            self.source_version != version
            or self.object_key != f"conus/{version}/wtk_conus_{self.year}.h5"
        ):
            raise ValueError("wind source version and annual object differ")
        sha256(self.object_identity_digest)
        sha256(self.point_manifest_digest)


@dataclass(frozen=True)
class _Plan(Record):
    schema: Literal["utility-wind-annual-plan-v1"]
    sources: tuple[_Source, ...]
    model_digest: str
    geometry_digest: str
    interpretation_digest: str

    def _validate(self):
        years = tuple(source.year for source in self.sources)
        if not years or years != tuple(sorted(set(years))):
            raise ValueError("wind cost plan requires unique chronological years")
        for value in (self.model_digest, self.geometry_digest, self.interpretation_digest):
            sha256(value)


@dataclass(frozen=True)
class _Binding(Record):
    schema: Literal["utility-wind-annual-source-binding-v1"]
    task_id: str
    suite_digest: str
    plan: _Plan
    payloads: tuple[ArtifactRef, ...]
    claim_digest: str
    source_code_digest: str
    kernel_code_digest: str
    task_admitted: Literal[False] = False
    private_boundary_qualified: Literal[False] = False

    def _validate(self):
        identifier(self.task_id)
        for value in (
            self.suite_digest,
            self.claim_digest,
            self.source_code_digest,
            self.kernel_code_digest,
        ):
            sha256(value)
        if len(self.payloads) != len(self.plan.sources):
            raise ValueError("wind binding omitted an annual payload")
        for source, payload in zip(self.plan.sources, self.payloads, strict=True):
            if (
                payload.path != f"year-{source.year}.f64le"
                or payload.size_bytes != 16 * _hours(source.year)
                or payload.media_type != "application/octet-stream"
                or payload.metadata
                or payload.producer != "wind-annual-source"
            ):
                raise ValueError("wind payload role or fixed shape differs")


@dataclass(frozen=True)
class _Result(Record):
    year: int
    source_digest: str
    status: Literal[
        "success",
        "scientific_infeasible",
        "model_failure",
        "timeout",
        "infrastructure_failure",
        "not_attempted",
    ]
    energy_gwh: float | None

    def _validate(self):
        hours = _hours(self.year)
        sha256(self.source_digest)
        if self.status == "success":
            if self.energy_gwh is None or not 0 <= self.energy_gwh <= 8e6 * hours / 1e9 * (
                1 + 1e-10
            ):
                raise ValueError("wind energy exceeds the four-V80 profile")
        elif self.energy_gwh is not None:
            raise ValueError("unsuccessful wind evidence cannot supply a penalty energy")


@dataclass(frozen=True)
class _Run(Record):
    schema: Literal["utility-wind-annual-run-v1"]
    plan_digest: str
    configuration_digest: str
    results: tuple[_Result, ...]

    def _validate(self):
        sha256(self.plan_digest)
        sha256(self.configuration_digest)
        years = tuple(result.year for result in self.results)
        if not years or years != tuple(sorted(set(years))):
            raise ValueError("wind run requires unique chronological results")


@dataclass(frozen=True)
class _Work(Record):
    schema: Literal["utility-trusted-wind-annual-work-v1"]
    grant_digest: str
    scorer_digest: str
    source_binding_digest: str
    policy_digest: str
    source_access_digest: str
    kernel_record_digest: str
    score: PublicScore
    run: _Run
    attempted_model_starts: int
    completed_model_starts: int
    last_attempt_work_unknown: bool
    task_admitted: Literal[False] = False
    private_boundary_qualified: Literal[False] = False
    os_deadline_qualified: Literal[False] = False
    aggregate_rss_qualified: Literal[False] = False
    automatic_retries: Literal[0] = 0

    def _validate(self):
        for value in (
            self.grant_digest,
            self.scorer_digest,
            self.source_binding_digest,
            self.policy_digest,
            self.source_access_digest,
            self.kernel_record_digest,
        ):
            sha256(value)
        if not 0 <= self.completed_model_starts <= self.attempted_model_starts <= 8:
            raise ValueError("wind work counters exceed their bounded profile")


@dataclass(frozen=True)
class WindCostRegistration(Record):
    schema: Literal["utility-wind-cost-registration-v1"]
    binding_artifact: ArtifactRef
    callback_source_digest: str
    policy: WindScorePolicy
    expected_model_digest: str
    geometry_digest: str

    def _validate(self):
        for value in (
            self.callback_source_digest,
            self.expected_model_digest,
            self.geometry_digest,
        ):
            sha256(value)

    @property
    def outcome(self):
        return OutcomeSpec(
            "engineering-outcome-v1",
            "mean_annual_energy",
            "GWh",
            "maximize",
            "mean",
            digest(
                {
                    "kernel": self.policy.scorer_source_digest,
                    "aggregation": "equal-year-actual-duration",
                }
            ),
        )

    @property
    def code_digest(self):
        return digest(
            {
                "schema": "utility-trusted-annual-wind-callback-v1",
                "callback_source": self.callback_source_digest,
                "policy": self.policy.digest,
                "geometry": self.geometry_digest,
                "model": self.expected_model_digest,
                "outcome": self.outcome.digest,
            }
        )


@dataclass(frozen=True)
class WindCostInput(Record):
    grant: ConfirmationGrant
    registration: WindCostRegistration
    work_artifact: ArtifactRef | None


def _metadata(store, name):
    path = confined_file(store.root, name)
    if path.stat().st_size > 65536:
        raise ValueError("wind metadata exceeds the fixed envelope")
    blob = path.read_bytes()
    return blob, unique_json(blob.decode())


def _binding(store, registration):
    artifact = registration.binding_artifact
    if (
        re.fullmatch(r"wind-annual-source-bindings/[a-z][a-z0-9_-]{0,95}\.json", artifact.path)
        is None
        or artifact.media_type != "application/json"
        or artifact.producer != "wind-annual-source"
        or artifact.metadata
    ):
        raise ValueError("wind source binding artifact role differs")
    fixed = _Binding.from_json(read_bytes(store.root, artifact, max_bytes=65536).decode())
    task = next(t for t in store.spec.tasks if t.task_id == fixed.task_id)
    if (
        artifact.path != f"wind-annual-source-bindings/{fixed.task_id}.json"
        or artifact.media_type != "application/json"
        or artifact.producer != "wind-annual-source"
        or artifact.metadata
        or task.family != "wind"
        or fixed.suite_digest != store.spec.digest
        or task.partition_digest != fixed.plan.digest
        or fixed.plan.digest != registration.policy.plan_digest
        or fixed.plan.model_digest != registration.policy.model_digest
        or fixed.plan.geometry_digest != registration.geometry_digest
        or fixed.kernel_code_digest != registration.policy.scorer_source_digest
    ):
        raise ValueError("wind binding, policy and immutable task differ")
    _, claim = _metadata(store, f"wind-annual-source-claims/{fixed.task_id}.json")
    sha256(claim["scope_digest"])
    expected = {
        "schema": "utility-wind-annual-source-claim-v1",
        "task_id": fixed.task_id,
        "suite_digest": store.spec.digest,
        "plan_digest": fixed.plan.digest,
        "scope_digest": claim["scope_digest"],
        "source_code_digest": fixed.source_code_digest,
        "kernel_code_digest": fixed.kernel_code_digest,
        "automatic_retries": 0,
        "private_payload_writes_reserved": len(fixed.payloads),
        "scientific_starts": 0,
    }
    if digest(claim) != fixed.claim_digest or canonical_json(claim) != canonical_json(expected):
        raise ValueError("wind binding changed its original preparation claim")
    return fixed


def _source_access(store, grant, fixed):
    records = {}

    def expect(suffix, expected):
        name = f"wind-annual-source-accesses/{grant.digest}{suffix}.json"
        blob, _ = _metadata(store, name)
        if blob != canonical_json(expected).encode():
            raise ValueError("wind original read metadata changed")
        records[name] = hashlib.sha256(blob).hexdigest()

    count, size = len(fixed.payloads), sum(p.size_bytes for p in fixed.payloads)
    expect(
        "",
        {
            "grant_digest": grant.digest,
            "binding_digest": fixed.digest,
            "private_reads_reserved": count,
            "private_bytes_reserved": size,
            "automatic_retries": 0,
        },
    )
    for annual, payload in zip(fixed.plan.sources, fixed.payloads, strict=True):
        common = {
            "grant_digest": grant.digest,
            "source_digest": annual.digest,
            "payload_digest": payload.sha256,
        }
        expect(
            f"-{annual.year}-start",
            {
                **common,
                "status": "started",
                "private_bytes_reserved": payload.size_bytes,
                "automatic_retries": 0,
            },
        )
        expect(
            f"-{annual.year}-complete",
            {
                **common,
                "status": "verified",
                "completed_private_reads": 1,
                "verified_private_bytes": payload.size_bytes,
            },
        )
    expect(
        "-complete",
        {
            "grant_digest": grant.digest,
            "binding_digest": fixed.digest,
            "completed_private_reads": count,
            "verified_private_bytes": size,
            "automatic_retries": 0,
        },
    )
    return digest(records)


def _work(work, store, grant, fixed, registration, selected):
    if (
        work.grant_digest != grant.digest
        or work.scorer_digest != grant.scorer_digest
        or work.source_binding_digest != fixed.digest
        or work.policy_digest != registration.policy.digest
        or work.run.plan_digest != fixed.plan.digest
        or work.run.configuration_digest != digest(dict(selected.configuration))
        or tuple(r.year for r in work.run.results) != tuple(s.year for s in fixed.plan.sources)
        or work.source_access_digest != _source_access(store, grant, fixed)
    ):
        raise ValueError("wind work changed its source, grant or frozen configuration")
    failed, completed = None, 0
    for source, result in zip(fixed.plan.sources, work.run.results, strict=True):
        if source.digest != result.source_digest:
            raise ValueError("wind work substituted an annual source")
        if failed is None and result.status == "success":
            completed += 1
        elif failed is None and result.status != "not_attempted":
            failed = result.status
        elif failed is None or result.status != "not_attempted":
            raise ValueError("wind work reordered failed and unattempted cases")
    expected = PublicScore(
        failed or "success",
        "mean_annual_energy",
        "GWh",
        math.fsum(r.energy_gwh for r in work.run.results) / len(work.run.results)
        if failed is None
        else None,
        True if failed is None else False if failed == "scientific_infeasible" else None,
    )
    if (
        work.score != expected
        or work.completed_model_starts != completed
        or work.attempted_model_starts != completed + (failed is not None)
        or work.last_attempt_work_unknown != (failed is not None)
    ):
        raise ValueError("wind work score or bounded start counts differ")


def join_wind_costs(store, grant, registration, *, work_artifact=None):
    """Read an original grant and optional caller-pinned work; never scan for proof.

    Missing work leaves actual quantities unknown. Reservations stay charged.
    Failed model attempts do not establish total actual model starts or inner
    work. Known completions remain separate. These records confer no admission.
    """
    if type(grant) is not ConfirmationGrant or not isinstance(registration, WindCostRegistration):
        raise ValueError("wind costs require typed grant and registration")
    state = store.replay()
    selected = validate_grant(store, grant, state["frozen"])
    selected = read_selected_state(store.root, selected.selected_state)
    fixed = _binding(store, registration)
    identity = digest(
        {
            "schema": "utility-wind-annual-bound-scorer-v1",
            "binding_digest": fixed.digest,
            "scorer_code_digest": registration.code_digest,
        }
    )
    model = selected.model
    pins = {ref.path: ref.sha256 for ref in model.source_bundle}
    if (
        grant.scorer_digest != identity
        or grant.partition_digest != fixed.plan.digest
        or grant.outcome_digest != registration.outcome.digest
        or model.digest != registration.expected_model_digest
        or model.implementations != {"wind": "annual-hourly-noj-v1"}
        or digest({name: pins.get(name) for name in MODEL_FILES})
        != registration.policy.model_digest
        or pins.get("examples/utility/wind_annual_callback.py")
        != registration.callback_source_digest
        or pins.get("examples/utility/wind_annual_source.py") != fixed.source_code_digest
        or pins.get("examples/utility/wind_annual_scoring.py") != fixed.kernel_code_digest
        or model.graph_digest
        != digest(
            {
                "profile": "utility-wind-annual-model-v1",
                "model": fixed.plan.model_digest,
                "geometry": fixed.plan.geometry_digest,
                "interpretation": fixed.plan.interpretation_digest,
            }
        )
    ):
        raise ValueError("wind registration differs from original selected model and scorer")
    cell = next(c for c in store.spec.cells if c.digest == grant.cell_digest)
    caps = {r.name: r for r in grant.resources}
    needed = {
        "wind_model_starts": len(fixed.plan.sources),
        "private_wind_reads": len(fixed.payloads),
        "private_wind_bytes": sum(p.size_bytes for p in fixed.payloads),
    }
    for name, count in needed.items():
        cap = caps.get(name)
        if cap is None or (cap.units, cap.enforcement, cap.limit) != (
            "count",
            "reservation",
            count,
        ):
            raise ValueError("wind original grant lacks exact reserved inner work")
    active = caps.get("active_time")
    if (
        cell.task_id != fixed.task_id
        or cell.regime != "fixed_evaluations"
        or active is None
        or (active.units, active.enforcement) != ("s", "reservation")
        or active.limit <= 0
    ):
        raise ValueError("wind cost scope changed task, regime or active-time allocation")
    attempt = "confirmation-" + grant.cell_digest[:48]
    allocation, _ = state["attempts"].get(attempt, (None, None))
    if (
        allocation is None
        or allocation.phase != "confirmation"
        or allocation.child_digest != grant.digest
        or allocation.resources != grant.resources
    ):
        raise StoreError("wind costs need the original charged allocation")
    access = state["confirmation_accesses"].get(attempt)
    if (
        access is not None
        and _read(store.root, access, "confirmation-grant.json", ConfirmationGrant) != grant
    ):
        raise StoreError("wind costs changed original confirmation access")
    receipt_id = state["confirmation_scores"].get(attempt)
    receipt = read_receipt(store.root, receipt_id) if receipt_id else None
    if receipt is not None and (
        receipt.grant_digest != grant.digest
        or receipt.access_digest != access
        or receipt.outcome_contract != registration.outcome
    ):
        raise ValueError("wind score receipt differs from original grant")
    work = None
    if work_artifact is not None:
        if (
            not isinstance(work_artifact, ArtifactRef)
            or access is None
            or work_artifact.path != f"artifacts/{work_artifact.sha256}/annual-wind-work.json"
            or work_artifact.media_type != "application/json"
            or work_artifact.metadata
            or work_artifact.producer != "annual-wind-confirmation-work"
        ):
            raise ValueError("wind work artifact role differs")
        work = _Work.from_json(read_bytes(store.root, work_artifact, max_bytes=65536).decode())
        _work(work, store, grant, fixed, registration, selected)
        if receipt is not None and receipt.score != work.score:
            raise ValueError("wind work changed committed score")
    quantities = [
        ("wind_model_start_reservations", "count", needed["wind_model_starts"]),
        ("wind_private_read_reservations", "count", needed["private_wind_reads"]),
        ("wind_private_byte_reservations", "byte", needed["private_wind_bytes"]),
        ("wind_case_attempts", "count", work.attempted_model_starts if work else None),
        ("wind_completed_evaluations", "count", work.completed_model_starts if work else None),
        (
            "wind_model_starts",
            "count",
            work.attempted_model_starts if work and not work.last_attempt_work_unknown else None,
        ),
        ("wind_private_reads", "count", len(fixed.payloads) if work else None),
        ("wind_private_bytes", "byte", sum(p.size_bytes for p in fixed.payloads) if work else None),
        ("wind_inner_wake_calls", "count", None),
        ("wind_cpu_time", "CPU-s", None),
        ("wind_peak_rss", "byte", None),
    ]
    if store.replay()["head"] != state["head"]:
        raise StoreError("suite changed during wind cost reconstruction")
    return tuple(
        CostRecord(
            "wind-cost-" + digest({"grant": grant.digest, "resource": name})[:48],
            grant.digest,
            "confirmation",
            name,
            units,
            value,
            (grant.cell_digest,),
            (1.0,),
        )
        for name, units, value in quantities
    )
