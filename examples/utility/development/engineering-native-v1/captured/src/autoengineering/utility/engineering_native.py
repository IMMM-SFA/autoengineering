"""Bounded trusted native-driver jobs with separate inner model-call evidence.

A batch scientific reservation covers one driver process. It does not represent
one inner solve. Frozen inner limits and returned call records remain separate.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import math
import sys
from typing import Literal

from autoengineering.agents.batch import PhysicalObservation, PhysicalReservation
from autoengineering.agents.process import recover_completed_process, supervise_process
from autoengineering.campaign.artifacts import confined_file, read_bytes
from autoengineering.campaign.records import Scalar
from autoengineering.campaign.serialization import Record, canonical_json, digest, unique_json
from autoengineering.campaign.store import StoreError, checked_directory, durable_write
from .contracts import identifier, sha256
from .engineering_process import (
    EngineeringExecutionSpec,
    SupervisedEngineeringExecutor,
    runtime_binding,
    verify_sources,
)


@dataclass(frozen=True)
class NativeDriverSpec(Record):
    schema: Literal["utility-native-driver-v1"]
    execution: EngineeringExecutionSpec
    entrypoint: str
    max_iterations: int
    max_model_solves: int
    timeout_seconds: float
    output_bytes: int

    def _validate(self):
        module, separator, function = self.entrypoint.partition(":")
        if (
            not separator
            or not all(p.isidentifier() for p in module.split("."))
            or not function.isidentifier()
        ):
            raise ValueError("native driver requires a supplied module:function")
        if (
            not 1 <= self.max_iterations <= 1000
            or not len(self.execution.scenarios) < self.max_model_solves <= 128
        ):
            raise ValueError("native iteration/solve limits are outside this profile")
        if self.timeout_seconds <= 0 or not 1 <= self.output_bytes <= 65536:
            raise ValueError("native process limits must be positive and bounded")


@dataclass(frozen=True)
class NativeSolverState(Record):
    converged: bool
    residual_norm: float
    residual_tolerance: float
    residual_units: Literal["A", "V", "W", "m"]
    solver_iterations: int
    component_calls: int
    derivative_calls: int

    def _validate(self):
        if (
            self.residual_norm < 0
            or self.residual_tolerance < 0
            or min(self.solver_iterations, self.component_calls, self.derivative_calls) < 0
        ):
            raise ValueError("native solver diagnostics must be nonnegative")
        if self.converged and self.residual_norm > self.residual_tolerance:
            raise ValueError("native convergence contradicts residual evidence")


@dataclass(frozen=True)
class NativeSolveRecord(Record):
    phase: Literal["driver", "scenario"]
    scenario_id: str | None
    counter_scope: Literal["shared_problem_snapshot", "independent_problem"]
    diagnostics: NativeSolverState

    def _validate(self):
        if (self.phase == "scenario") != (self.scenario_id is not None):
            raise ValueError("native scenario calls need their original scenario identity")
        if self.scenario_id is not None:
            identifier(self.scenario_id)
        if self.counter_scope != (
            "shared_problem_snapshot" if self.phase == "driver" else "independent_problem"
        ):
            raise ValueError("native counters differ from their problem scope")


@dataclass(frozen=True)
class NativeDriverJob(Record):
    schema: Literal["utility-native-job-v1"]
    specification: NativeDriverSpec
    source_root: str
    scratch_path: str
    binding_digest: str

    def _validate(self):
        sha256(self.binding_digest)


@dataclass(frozen=True)
class NativeDriverResult(Record):
    schema: Literal["utility-native-result-v1"]
    job_digest: str
    configuration: Mapping[str, Scalar]
    driver_success: bool
    solves: tuple[NativeSolveRecord, ...]

    def _validate(self):
        sha256(self.job_digest)
        if not self.solves or len(self.solves) > 128:
            raise ValueError("native result needs bounded inner-call evidence")


@dataclass(frozen=True)
class NativeDriverReport(Record):
    schema: Literal["utility-native-report-v1"]
    specification_digest: str
    binding_digest: str
    job_digest: str
    reservation_id: str
    status: Literal["success", "model_failure", "infrastructure_failure", "timeout"]
    process_status: str
    process_identity: Mapping[str, str | int] | None
    stop_verified: bool
    elapsed_seconds: float
    result: NativeDriverResult | None

    def _validate(self):
        for value in (self.specification_digest, self.binding_digest, self.job_digest):
            sha256(value)
        identifier(self.reservation_id)
        if not self.stop_verified or self.elapsed_seconds < 0:
            raise ValueError("native report requires original stopped process evidence")
        if self.result is not None and self.result.job_digest != self.job_digest:
            raise ValueError("native report result belongs to another job")
        if self.status == "success" and (self.result is None or not self.result.driver_success):
            raise ValueError("successful native report lacks a successful driver result")


def native_binding(spec, source_root):
    return {
        "profile": "supervised-native-driver-v1",
        "native": spec.to_dict(),
        "runtime": runtime_binding(spec.execution, source_root),
    }


class SupervisedNativeDriver:
    """One original driver process, never a free retry or an inner-solve count."""

    def __init__(self, spec, executor, *, fault=lambda _: None):
        if (
            not isinstance(executor, SupervisedEngineeringExecutor)
            or spec.execution != executor.spec
        ):
            raise StoreError("native and scenario executors differ")
        self.spec, self.executor, self.fault = spec, executor, fault
        self.batch, self.case_id, self.source_root = (
            executor.batch,
            executor.case_id,
            executor.source_root,
        )
        verify_sources(spec.execution, self.source_root, additional_entrypoints=(spec.entrypoint,))
        self.directory = self.batch.root / "cases" / self.case_id / "native-drivers" / spec.digest
        if any(p.is_symlink() for p in (self.directory, self.directory.parent)):
            raise StoreError("native driver directory cannot contain a symlink")
        self.directory.parent.mkdir(mode=0o700, exist_ok=True)
        checked_directory(self.directory.parent)
        self.directory.mkdir(mode=0o700, exist_ok=True)
        checked_directory(self.directory)
        binding = native_binding(spec, self.source_root)
        self.binding_digest = digest(binding)
        self.reservation_id = "native-" + spec.digest[:32]
        with self.batch.operation():
            path = self.directory / "binding.json"
            if path.exists():
                if confined_file(self.directory, path.name).read_text() != canonical_json(binding):
                    raise StoreError("native source/environment binding changed")
            else:
                if self.reservation_id in self.batch.replay().reservations:
                    raise StoreError("original native permission lacks its binding")
                durable_write(path, canonical_json(binding).encode())
        self.job = NativeDriverJob(
            "utility-native-job-v1",
            spec,
            str(self.source_root),
            str(self.directory),
            self.binding_digest,
        )

    def run(self, *, recover_only=False):
        if type(recover_only) is not bool:
            raise ValueError("native recovery must be explicitly boolean")
        verify_sources(
            self.spec.execution, self.source_root, additional_entrypoints=(self.spec.entrypoint,)
        )
        with self.batch.operation():
            state = self.batch.replay()
            reservation = state.reservations.get(self.reservation_id)
            nonce = "native-" + self.job.digest[:32]
            if reservation is None:
                if recover_only or state.pending:
                    raise StoreError("native job is undispatched or original work is uncertain")
                if any(p.name != "binding.json" for p in self.directory.iterdir()):
                    raise StoreError("undispatched native job contains unexplained files")
                reservation = PhysicalReservation(
                    self.reservation_id,
                    self.case_id,
                    "science",
                    self.job.digest,
                    None,
                    self.batch.clock(),
                    self.spec.timeout_seconds + 5.0,
                    0,
                    0,
                    0,
                )
                self.batch.reserve(reservation)
                durable_write(self.directory / "job.json", self.job.to_json().encode())
                self.fault("native_reserved")
                now = self.batch.clock()
                if (
                    not math.isfinite(now)
                    or now < reservation.recorded_at
                    or now + reservation.timeout_seconds
                    > self.batch.created_at + self.batch.spec.limits.elapsed_seconds
                ):
                    raise StoreError("native batch deadline changed before launch; charge retained")
                process = supervise_process(
                    (
                        sys.executable,
                        "-I",
                        "-B",
                        "-m",
                        "autoengineering.utility.engineering_native_worker",
                        str(self.directory / "job.json"),
                    ),
                    directory=self.directory / "process",
                    cwd=self.directory,
                    environment={},
                    nonce=nonce,
                    stdin=b"",
                    timeout_seconds=self.spec.timeout_seconds,
                    max_output_bytes=self.spec.output_bytes,
                    on_launch=lambda _: None,
                    parent_watchdog=True,
                )
                self.fault("native_process_saved")
            else:
                if (
                    reservation.invocation_digest != self.job.digest
                    or reservation.case_id != self.case_id
                    or reservation.timeout_seconds != self.spec.timeout_seconds + 5.0
                    or confined_file(self.directory, "job.json").read_text() != self.job.to_json()
                ):
                    raise StoreError("original native job permission differs")
                process = recover_completed_process(
                    self.directory / "process", nonce=nonce, max_output_bytes=self.spec.output_bytes
                )
            report = self._decode(process)
            proof = self.batch.evidence(report.to_dict())
            self.batch.observe(
                PhysicalObservation(
                    reservation.id,
                    report.status,
                    True,
                    0,
                    {},
                    None,
                    "not_applicable",
                    process.elapsed_seconds,
                    (proof,),
                )
            )
            self.fault("native_observed")
            return report

    def _decode(self, process):
        if not process.stopped:
            raise StoreError("native process stop is not verified")
        result = None
        if process.status == "timeout":
            status = "timeout"
        elif process.status != "completed" or process.returncode != 0 or process.truncated:
            status = (
                "model_failure"
                if process.returncode == 3 or process.status == "output_limit"
                else "infrastructure_failure"
            )
        else:
            try:
                result = NativeDriverResult.from_json(process.stdout.decode())
                validate_native_result(self.spec, self.job, result)
                status = "success" if result.driver_success else "model_failure"
            except (ValueError, UnicodeError):
                result, status = None, "model_failure"
        return NativeDriverReport(
            "utility-native-report-v1",
            self.spec.digest,
            self.binding_digest,
            self.job.digest,
            self.reservation_id,
            status,
            process.status,
            process.identity.to_dict() if process.identity else None,
            True,
            process.elapsed_seconds,
            result,
        )


def validate_native_result(spec, job, result):
    spec.execution.study.run.search_space.encode(result.configuration)
    if result.job_digest != job.digest or len(result.solves) > spec.max_model_solves:
        raise ValueError("native result differs from job or inner-call ceiling")
    driver = tuple(r for r in result.solves if r.phase == "driver")
    scenarios = tuple(r for r in result.solves if r.phase == "scenario")
    if (
        not driver
        or result.solves != driver + scenarios
        or tuple(r.scenario_id for r in scenarios) != spec.execution.study.scenario_ids
    ):
        raise ValueError("native inner-call evidence omits driver/scenario work")


def verify_native_report(batch, case_id, spec, report):
    """Offline receipt checks. No scientific import, subprocess or source re-execution."""
    if report.specification_digest != spec.digest:
        raise StoreError("native report specification differs")
    root = batch.root / "cases" / case_id / "native-drivers" / spec.digest
    binding = unique_json(confined_file(root, "binding.json").read_text())
    job = NativeDriverJob.from_json(confined_file(root, "job.json").read_text())
    if (
        digest(binding) != report.binding_digest
        or job.binding_digest != report.binding_digest
        or job.digest != report.job_digest
        or job.specification != spec
    ):
        raise StoreError("native report binding/job differs")
    state = batch.replay()
    reservation = state.reservations.get(report.reservation_id)
    observation = state.observations.get(report.reservation_id)
    if (
        reservation is None
        or reservation.case_id != case_id
        or reservation.resource != "science"
        or reservation.invocation_digest != job.digest
        or observation is None
        or not observation.stop_verified
        or observation.status != report.status
        or observation.elapsed_seconds != report.elapsed_seconds
        or len(observation.evidence) != 1
    ):
        raise StoreError("native report lacks original physical evidence")
    if unique_json(read_bytes(batch.root, observation.evidence[0]).decode()) != report.to_dict():
        raise StoreError("native report differs from original observed bytes")
    if report.result is not None:
        validate_native_result(spec, job, report.result)


def native_cost_records(report, cell_digest):
    """Keep driver jobs, inner model calls and cumulative counters distinct."""
    from .costs import CostRecord

    sha256(cell_digest)
    quantities = (
        ("native_driver_process_starts", 1.0 if report.process_identity is not None else None),
        ("native_inner_model_calls", float(len(report.result.solves)) if report.result else None),
    )
    return tuple(
        CostRecord(
            "native-cost-" + digest({"report": report.digest, "resource": name})[:48],
            report.digest,
            "selection",
            name,
            "count",
            quantity,
            (cell_digest,),
            (1.0,),
        )
        for name, quantity in quantities
    )
