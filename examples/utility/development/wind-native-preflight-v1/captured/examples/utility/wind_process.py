"""Source-bound native wind jobs using the shared owned-process supervisor.

One outer reservation covers a driver process. Wake and gradient callback entries
remain separate bounded work. A successful report is an unscored proposal.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import Literal

from autoengineering.campaign.artifacts import confined_file, read_bytes
from autoengineering.campaign.records import ArtifactRef
from autoengineering.campaign.serialization import Record, digest, unique_json
from autoengineering.campaign.store import StoreError
from autoengineering.optimization import ContinuousParameter
from autoengineering.utility.contracts import identifier, sha256
from autoengineering.utility.engineering_native import SupervisedNativeDriver
from autoengineering.utility.engineering_process import (
    EngineeringExecutionSpec,
    runtime_binding,
    verify_sources,
)
from examples.utility.wind_proposal import WindNativeProposal, WindNativeSpec, propose
from examples.utility.wind_scenario import GEOMETRY_PATH, rules


@dataclass(frozen=True)
class WindDriverSpec(Record):
    schema: Literal["utility-wind-driver-v1"]
    execution: EngineeringExecutionSpec
    native: WindNativeSpec
    entrypoint: str
    timeout_seconds: float
    output_bytes: int

    def _validate(self):
        module, separator, function = self.entrypoint.partition(":")
        if (
            not separator
            or not all(p.isidentifier() for p in module.split("."))
            or not function.isidentifier()
        ):
            raise ValueError("wind driver requires a supplied module:function")
        if self.execution.schema not in (
            "utility-engineering-execution-v2",
            "utility-engineering-execution-v3",
        ):
            raise ValueError("wind driver requires case-bound engineering execution v2")
        geometry = self.native.geometry
        if (
            self.execution.schema == "utility-engineering-execution-v3"
            and self.execution.preflight != geometry.preflight
        ):
            raise ValueError("wind preflight constraints differ from frozen physical spacing")
        expected = geometry.bounds
        space = self.execution.study.run.search_space
        if tuple(p.name for p in space.parameters) != tuple(expected) or any(
            not isinstance(p, ContinuousParameter)
            or p.scale != "linear"
            or p.active_when
            or (p.lower, p.upper) != expected[p.name]
            for p in space.parameters
        ):
            raise ValueError("wind driver parameter domain differs from fixed geometry")
        if self.execution.study.rules != rules() or len(self.execution.scenarios) != 1:
            raise ValueError("wind driver requires the registered bundled scenario and rules")
        if dict(self.execution.scenarios[0].forcing) != {
            "direction_step": float(geometry.direction_step)
        }:
            raise ValueError("wind driver cannot change its frozen distribution")
        if not 0 < self.timeout_seconds <= 3600 or not 1 <= self.output_bytes <= 65536:
            raise ValueError("wind driver process limits are outside this profile")


@dataclass(frozen=True)
class WindDriverJob(Record):
    schema: Literal["utility-wind-driver-job-v1"]
    specification: WindDriverSpec
    source_root: str
    scratch_path: str
    binding_digest: str

    def _validate(self):
        sha256(self.binding_digest)


@dataclass(frozen=True)
class WindDriverResult(Record):
    schema: Literal["utility-wind-driver-result-v1"]
    job_digest: str
    proposal: WindNativeProposal

    def _validate(self):
        sha256(self.job_digest)


@dataclass(frozen=True)
class WindDriverReport(Record):
    schema: Literal["utility-wind-driver-report-v1"]
    specification_digest: str
    binding_digest: str
    job_digest: str
    reservation_id: str
    status: Literal["success", "model_failure", "infrastructure_failure", "timeout"]
    process_status: str
    process_identity: Mapping[str, str | int] | None
    stop_verified: bool
    elapsed_seconds: float
    result: WindDriverResult | None

    def _validate(self):
        for value in (self.specification_digest, self.binding_digest, self.job_digest):
            sha256(value)
        identifier(self.reservation_id)
        if not self.stop_verified or self.elapsed_seconds < 0:
            raise ValueError("wind report requires verified original process stop")
        if self.result is not None and self.result.job_digest != self.job_digest:
            raise ValueError("wind report belongs to another job")
        if self.status == "success" and (
            self.result is None or self.result.proposal.configuration is None
        ):
            raise ValueError("successful wind driver needs an unscored feasible proposal")


def wind_binding(spec, source_root):
    return {
        "profile": "supervised-wind-native-v1",
        "native": spec.to_dict(),
        "runtime": runtime_binding(spec.execution, source_root),
    }


def validate_result(job, result):
    if result.job_digest != job.digest or result.proposal.specification != job.specification.native:
        raise ValueError("wind driver changed its job, hardware or callback limits")
    configuration = result.proposal.configuration
    if configuration is not None:
        job.specification.execution.study.run.search_space.encode(configuration)


def verify_wind_sources(spec, source_root):
    verify_sources(
        spec.execution,
        source_root,
        additional_entrypoints=(spec.entrypoint, "examples.utility.wind_process:run_driver"),
    )
    ref = next((r for r in spec.execution.sources if r.path == GEOMETRY_PATH), None)
    if (
        ref is None
        or read_bytes(Path(source_root), ref, max_bytes=65536).decode()
        != spec.native.geometry.to_json()
    ):
        raise StoreError("wind native geometry differs from original scenario input")
    # These trusted bootstrap modules load before the captured entrypoint. Bind
    # their actual installed bytes as well as the captured worker's bytes.
    for name in (
        "wind_process.py",
        "wind_proposal.py",
        "wind_native.py",
        "wind_parameters.py",
        "wind_scenario.py",
        "wind.py",
    ):
        relative = "examples/utility/" + name
        ref = next((r for r in spec.execution.sources if r.path == relative), None)
        if (
            ref is None
            or read_bytes(Path(source_root), ref) != Path(__file__).with_name(name).read_bytes()
        ):
            raise StoreError("wind native bootstrap source differs from captured input")


class SupervisedWindDriver(SupervisedNativeDriver):
    """Reuse reservations, cancellation, stop checks and original-process recovery."""

    worker_module = "autoengineering.utility.wind_native_worker"
    binding = staticmethod(wind_binding)

    @staticmethod
    def make_job(spec, source_root, directory, binding_digest):
        return WindDriverJob(
            "utility-wind-driver-job-v1", spec, str(source_root), str(directory), binding_digest
        )

    def __init__(self, spec, executor, *, fault=lambda _: None):
        verify_wind_sources(spec, executor.source_root)
        super().__init__(spec, executor, fault=fault)

    def run(self, *, recover_only=False):
        verify_wind_sources(self.spec, self.source_root)
        return super().run(recover_only=recover_only)

    def _decode(self, process):
        if not process.stopped:
            raise StoreError("wind process stop is unverified")
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
                result = WindDriverResult.from_json(process.stdout.decode())
                validate_result(self.job, result)
                status = "success" if result.proposal.configuration is not None else "model_failure"
            except (ValueError, UnicodeError):
                result, status = None, "model_failure"
        return WindDriverReport(
            "utility-wind-driver-report-v1",
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


def run_driver(job):
    return WindDriverResult(
        "utility-wind-driver-result-v1", job.digest, propose(job.specification.native)
    )


def verify_report(batch, case_id, spec, report):
    """Check original bindings and observed report bytes without running science."""
    root = batch.root / "cases" / case_id / "native-drivers" / spec.digest
    binding = unique_json(confined_file(root, "binding.json").read_text())
    job = WindDriverJob.from_json(confined_file(root, "job.json").read_text())
    if (
        report.specification_digest != spec.digest
        or job.specification != spec
        or digest(binding) != report.binding_digest
        or job.binding_digest != report.binding_digest
        or job.digest != report.job_digest
    ):
        raise StoreError("wind report differs from original binding/job")
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
        raise StoreError("wind report lacks original physical evidence")
    if unique_json(read_bytes(batch.root, observation.evidence[0]).decode()) != report.to_dict():
        raise StoreError("wind report differs from observed bytes")
    completion = unique_json(confined_file(root, "process/completion.json").read_text())
    process_job = confined_file(root, "process/job.json").read_bytes()
    if (
        hashlib.sha256(process_job).hexdigest() != completion["job_sha256"]
        or not completion["stopped"]
        or completion["identity"]
        != (dict(report.process_identity) if report.process_identity else None)
        or completion["status"] != report.process_status
        or (
            completion["identity"] is not None
            and completion["identity"]["nonce"] != "native-" + job.digest[:32]
        )
    ):
        raise StoreError("wind process completion differs from observed identity")
    stdout = ArtifactRef(
        "process/stdout.bin",
        completion["stdout_sha256"],
        completion["stdout_bytes"],
        "application/json",
        "original-supervisor",
        {},
    )
    raw = read_bytes(root, stdout, max_bytes=spec.output_bytes)
    if (
        binding.get("profile") != "supervised-wind-native-v1"
        or binding.get("native") != spec.to_dict()
        or binding.get("runtime", {}).get("execution") != spec.execution.to_dict()
        or binding.get("runtime", {}).get("source_root") != job.source_root
    ):
        raise StoreError("wind saved binding changed its source or execution")
    if report.result is not None:
        if completion["status"] != "completed" or completion["returncode"] != 0:
            raise StoreError("wind result lacks a completed original process")
        if WindDriverResult.from_json(raw.decode()) != report.result:
            raise StoreError("wind result differs from original process output")
        validate_result(job, report.result)


def cost_records(report, cell_digest):
    """Outer process starts and callback entries, never inferred inner wake solves."""
    from autoengineering.utility.costs import CostRecord

    sha256(cell_digest)
    work = report.result.proposal.work if report.result else None
    quantities = [("wind_native_process_starts", 1.0 if report.process_identity else None)]
    for kind in ("wake", "gradient"):
        for status in ("attempted", "completed", "failed", "unresolved"):
            quantities.append(
                (
                    f"wind_native_{kind}_callbacks_{status}",
                    float(work[kind][status]) if work is not None else None,
                )
            )
    return tuple(
        CostRecord(
            "wind-cost-" + digest({"report": report.digest, "resource": name})[:48],
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
