"""Native proposals with bounded callback evidence and no coupled-solver claims."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from autoengineering.campaign.artifacts import confined_file, read_bytes
from autoengineering.campaign.records import Scalar
from autoengineering.campaign.serialization import Record, canonical_json, digest, unique_json
from autoengineering.campaign.store import StoreError
from .contracts import identifier, sha256
from .engineering_native import SupervisedNativeDriver
from .engineering_process import EngineeringExecutionSpec, runtime_binding


@dataclass(frozen=True)
class CallbackDriverSpec(Record):
    schema: Literal["utility-callback-driver-v1"]
    execution: EngineeringExecutionSpec
    entrypoint: str
    options_json: str
    callback_limits: Mapping[str, int]
    timeout_seconds: float
    output_bytes: int

    def _validate(self):
        module, separator, function = self.entrypoint.partition(":")
        if (
            not separator
            or not all(p.isidentifier() for p in module.split("."))
            or not function.isidentifier()
        ):
            raise ValueError("callback driver requires a supplied module:function")
        if self.execution.schema not in (
            "utility-engineering-execution-v2",
            "utility-engineering-execution-v3",
        ):
            raise ValueError("callback driver requires case-bound execution v2")
        if len(self.options_json.encode()) > 65536:
            raise ValueError("callback driver options exceed limit")
        options = unique_json(self.options_json)
        if not isinstance(options, dict) or canonical_json(options) != self.options_json:
            raise ValueError("callback driver options require a canonical JSON object")
        if (
            not 1 <= len(self.callback_limits) <= 8
            or not all(1 <= n <= 128 for n in self.callback_limits.values())
            or sum(self.callback_limits.values()) > 128
        ):
            raise ValueError("callback driver needs positive callback caps with total at most 128")
        for kind in self.callback_limits:
            identifier(kind)
        if not 0 < self.timeout_seconds <= 3600 or not 1 <= self.output_bytes <= 65536:
            raise ValueError("callback process limits are outside this profile")


@dataclass(frozen=True)
class CallbackCall(Record):
    kind: str
    index: int
    status: Literal["started", "completed", "failed"]
    inputs: Mapping[str, float]
    outputs: Mapping[str, float]
    output_units: Mapping[str, str]

    def _validate(self):
        identifier(self.kind)
        if self.index < 1 or max(len(self.inputs), len(self.outputs)) > 128:
            raise ValueError("callback index or scalar dimensions exceed profile")
        if set(self.outputs) != set(self.output_units) or any(
            not u for u in self.output_units.values()
        ):
            raise ValueError("callback outputs require exact declared units")
        if self.status != "completed" and self.outputs:
            raise ValueError("unfinished or failed callbacks cannot provide outputs")


@dataclass(frozen=True)
class CallbackDriverJob(Record):
    schema: Literal["utility-callback-job-v1"]
    specification: CallbackDriverSpec
    source_root: str
    scratch_path: str
    binding_digest: str

    def _validate(self):
        sha256(self.binding_digest)


@dataclass(frozen=True)
class CallbackDriverResult(Record):
    schema: Literal["utility-callback-result-v1"]
    job_digest: str
    native_status: Literal["converged", "not_converged", "budget_exhausted", "failed"]
    driver_success: bool | None
    reported_feasible: bool
    final_configuration: Mapping[str, Scalar]
    configuration: Mapping[str, Scalar] | None
    calls: tuple[CallbackCall, ...]
    callback_limits: Mapping[str, int]

    def _validate(self):
        sha256(self.job_digest)
        if len(self.calls) > 128:
            raise ValueError("callback result exceeds trace limit")
        if self.native_status == "converged" and self.driver_success is not True:
            raise ValueError("native convergence requires driver success")
        for kind in {c.kind for c in self.calls}:
            indices = [c.index for c in self.calls if c.kind == kind]
            if indices != list(range(1, len(indices) + 1)):
                raise ValueError("callback trace has duplicate or missing indices")
        if self.configuration is not None and (
            self.native_status not in ("converged", "not_converged")
            or not self.reported_feasible
            or self.configuration != self.final_configuration
            or any(c.status == "started" for c in self.calls)
        ):
            raise ValueError("callback proposal lacks a resolved feasible final configuration")


@dataclass(frozen=True)
class CallbackDriverReport(Record):
    schema: Literal["utility-callback-report-v1"]
    specification_digest: str
    binding_digest: str
    job_digest: str
    reservation_id: str
    status: Literal["success", "model_failure", "infrastructure_failure", "timeout"]
    process_status: str
    process_identity: Mapping[str, str | int] | None
    stop_verified: bool
    elapsed_seconds: float
    result: CallbackDriverResult | None

    def _validate(self):
        for value in (self.specification_digest, self.binding_digest, self.job_digest):
            sha256(value)
        identifier(self.reservation_id)
        if not self.stop_verified or self.elapsed_seconds < 0:
            raise ValueError("callback report requires an original verified stop")
        if self.result is not None and self.result.job_digest != self.job_digest:
            raise ValueError("callback report belongs to another job")
        if self.status == "success" and (self.result is None or self.result.configuration is None):
            raise ValueError("successful callback report lacks an unscored proposal")


def callback_binding(spec, source_root):
    return {
        "profile": "supervised-native-callback-v1",
        "native": spec.to_dict(),
        "runtime": runtime_binding(spec.execution, source_root),
    }


def validate_callback_result(spec, job, result):
    if result.job_digest != job.digest:
        raise ValueError("callback result belongs to another original job")
    if result.callback_limits != spec.callback_limits:
        raise ValueError("callback result changed its frozen caps")
    counts = {}
    for call in result.calls:
        counts[call.kind] = counts.get(call.kind, 0) + 1
    if any(
        kind not in spec.callback_limits or count > spec.callback_limits[kind]
        for kind, count in counts.items()
    ):
        raise ValueError("callback result changed its kinds or exceeded frozen caps")
    if result.configuration is not None:
        spec.execution.study.run.search_space.encode(result.configuration)


class SupervisedCallbackDriver(SupervisedNativeDriver):
    """Use the same charged outer-process lifecycle with separate callback records."""

    worker_module = "autoengineering.utility.callback_native_worker"
    binding = staticmethod(callback_binding)

    @staticmethod
    def make_job(spec, source_root, directory, binding_digest):
        return CallbackDriverJob(
            "utility-callback-job-v1", spec, str(source_root), str(directory), binding_digest
        )

    def _decode(self, process):
        if not process.stopped:
            raise StoreError("callback process stop is not verified")
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
                result = CallbackDriverResult.from_json(process.stdout.decode())
                validate_callback_result(self.spec, self.job, result)
                status = "success" if result.configuration is not None else "model_failure"
            except (ValueError, UnicodeError):
                result, status = None, "model_failure"
        return CallbackDriverReport(
            "utility-callback-report-v1",
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


def verify_callback_report(batch, case_id, spec, report):
    """Read original receipts only. Never import the registered driver."""
    import hashlib
    from autoengineering.campaign.records import ArtifactRef

    if report.schema != "utility-callback-report-v1":
        raise StoreError("native report profile differs from callback driver")
    root = batch.root / "cases" / case_id / "native-drivers" / spec.digest
    binding = unique_json(confined_file(root, "binding.json").read_text())
    job = CallbackDriverJob.from_json(confined_file(root, "job.json").read_text())
    if (
        report.specification_digest != spec.digest
        or job.specification != spec
        or job.digest != report.job_digest
        or digest(binding) != report.binding_digest
        or job.binding_digest != report.binding_digest
        or binding.get("profile") != "supervised-native-callback-v1"
        or binding.get("native") != spec.to_dict()
        or binding.get("runtime", {}).get("execution") != spec.execution.to_dict()
        or binding.get("runtime", {}).get("source_root") != job.source_root
    ):
        raise StoreError("callback binding/job differs from original report")
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
        raise StoreError("callback report lacks original physical evidence")
    if unique_json(read_bytes(batch.root, observation.evidence[0]).decode()) != report.to_dict():
        raise StoreError("callback report differs from original observed bytes")
    completion = unique_json(confined_file(root, "process/completion.json").read_text())
    process_raw = confined_file(root, "process/job.json").read_bytes()
    process_job = unique_json(process_raw.decode())
    expected_command = [
        binding["runtime"]["python"],
        "-I",
        "-B",
        "-m",
        SupervisedCallbackDriver.worker_module,
        str(Path(job.scratch_path) / "job.json"),
    ]
    if (
        hashlib.sha256(process_raw).hexdigest() != completion["job_sha256"]
        or process_job["command"] != expected_command
        or process_job["cwd"] != job.scratch_path
        or not completion["stopped"]
        or completion["status"] != report.process_status
        or completion["identity"]
        != (dict(report.process_identity) if report.process_identity else None)
        or (
            completion["identity"] is not None
            and completion["identity"]["nonce"] != "native-" + job.digest[:32]
        )
    ):
        raise StoreError("callback process completion differs from original identity")
    stdout = ArtifactRef(
        "process/stdout.bin",
        completion["stdout_sha256"],
        completion["stdout_bytes"],
        "application/json",
        "original-supervisor",
        {},
    )
    raw = read_bytes(root, stdout, max_bytes=spec.output_bytes)
    if report.result is not None:
        if (
            completion["status"] != "completed"
            or completion["returncode"] != 0
            or CallbackDriverResult.from_json(raw.decode()) != report.result
        ):
            raise StoreError("callback result differs from original process output")
        validate_callback_result(spec, job, report.result)


def callback_cost_records(report, cell_digest):
    from .costs import CostRecord

    sha256(cell_digest)
    values = [("native_driver_process_starts", 1.0 if report.process_identity else None)]
    # No trace after a failed process means unknown work, not zero callbacks.
    result = report.result
    kinds = sorted(result.callback_limits) if result else ()
    values.append(("native_callback_entries", float(len(result.calls)) if result else None))
    for kind in kinds:
        calls = [c for c in result.calls if c.kind == kind]
        for status in ("attempted", "completed", "failed", "unresolved"):
            quantity = (
                len(calls)
                if status == "attempted"
                else sum(
                    c.status == ("started" if status == "unresolved" else status) for c in calls
                )
            )
            values.append((f"native_{kind}_callbacks_{status}", float(quantity)))
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
        for name, quantity in values
    )
