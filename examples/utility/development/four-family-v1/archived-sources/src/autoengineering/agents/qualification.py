"""Read trusted, pinned boundary qualification evidence without executing code.

The expected receipt digest comes from a trusted caller. Worker handoffs cannot
select or approve a qualification receipt. Verification grants no scientific
admission or authority to execute a generated implementation.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
import platform

from autoengineering.campaign.artifacts import confined_file
from autoengineering.campaign.serialization import digest, unique_json
from autoengineering.campaign.store import checked_directory
from .containers import ContainerRuntime, boundary_source_identity
from .sandbox import BoundaryLimits


CHECKS = (
    "startup",
    "privacy",
    "network",
    "memory",
    "cpu",
    "output",
    "sleep",
    "pids",
    "parent_death",
)


@dataclass(frozen=True)
class VerifiedQualification:
    receipt_digest: str
    boundary_identity: str
    runtime: ContainerRuntime
    limits: BoundaryLimits


def _raw(root: Path, name: str, ceiling: int = 65536) -> bytes:
    path = confined_file(root, name)
    if path.stat().st_size > ceiling:
        raise ValueError("qualification artifact exceeds its byte ceiling")
    value = path.read_bytes()
    if len(value) > ceiling:
        raise ValueError("qualification artifact exceeds its byte ceiling")
    return value


def _record(root: Path, name: str):
    return unique_json(_raw(root, name).decode())


def verify_qualification(root: Path, *, expected_digest: str) -> VerifiedQualification:
    """Reconstruct a caller-pinned local qualification, failing on changed evidence."""
    root = checked_directory(root)
    raw = _raw(root, "qualification.json")
    if hashlib.sha256(raw).hexdigest() != expected_digest:
        raise ValueError("qualification receipt differs from the trusted digest")
    receipt = unique_json(raw.decode())
    manifest = _record(root, "manifest.json")
    if any(receipt.get(key) != value for key, value in manifest.items()):
        raise ValueError("qualification receipt differs from its frozen manifest")
    if (
        receipt.get("schema_version") != "1.0"
        or receipt.get("purpose") != "generated-boundary-qualification"
        or receipt.get("status") != "qualified"
        or receipt.get("remaining_gate") is not None
        or receipt.get("max_probe_executions") != 9
        or receipt.get("max_elapsed_seconds") != 90
        or receipt.get("provider_calls") != 0
        or receipt.get("scientific_campaigns") != 0
        or receipt.get("image_download_attempted") is not False
    ):
        raise ValueError("qualification has an incomplete or unsupported outcome")
    elapsed = receipt.get("elapsed_seconds")
    if type(elapsed) not in (int, float) or not 0 < elapsed <= 90:
        raise ValueError("qualification elapsed allowance was exceeded")
    if (
        receipt.get("boundary_source_identity") != boundary_source_identity()
        or receipt.get("platform") != platform.platform()
    ):
        raise ValueError("qualification boundary source or platform changed")
    runtime_record = _record(root, "runtime.json")
    if receipt.get("runtime") != runtime_record:
        raise ValueError("qualification runtime identity changed")
    runtime = ContainerRuntime(**runtime_record)
    limits = BoundaryLimits(**receipt["limits"])
    if limits != BoundaryLimits(cpu_seconds=1, memory_bytes=128 * 1024 * 1024, output_bytes=4096):
        raise ValueError("qualification used unsupported resource limits")
    checks = receipt.get("checks", [])
    if tuple(check.get("name") for check in checks) != CHECKS:
        raise ValueError("qualification has missing, repeated or reordered probes")
    for check in checks:
        name = check["name"]
        if check.get("status") != "pass" or check.get("stopped") is not True:
            raise ValueError("qualification has a failed or unstopped probe")
        probe = checked_directory(root / ("parent-death" if name == "parent_death" else name))
        intent = _record(probe, "intent.json")
        job = _record(probe, "watchdog-job.json")
        cid = _raw(probe, "container-id").decode()
        if (
            intent.get("image_id") != runtime.image_id
            or intent.get("repository_digest") != runtime.repository_digest
            or job.get("container_id") != cid
            or job.get("nonce") != intent.get("nonce")
            or job.get("intent_digest") != digest(intent)
            or job.get("endpoint") != runtime.endpoint
            or job.get("docker") != runtime.docker
            or intent.get("cpu_seconds") != limits.cpu_seconds
            or intent.get("memory_bytes") != limits.memory_bytes
            or intent.get("output_bytes") != limits.output_bytes
        ):
            raise ValueError("qualification execution intent differs from runtime or limits")
        if hashlib.sha256(_raw(probe, "stdin.bin")).hexdigest() != intent.get("input_sha256"):
            raise ValueError("qualification input bytes changed")
        source = _raw(probe, "export/probe.py")
        if intent.get("sources") != {"probe.py": hashlib.sha256(source).hexdigest()}:
            raise ValueError("qualification probe source changed")
        if (
            name != "parent_death"
            and check.get("probe_sha256") != hashlib.sha256(source).hexdigest()
        ):
            raise ValueError("qualification probe identity differs from its execution")
        filename = "watchdog-result.json" if name == "parent_death" else "result.json"
        result_raw = _raw(probe, filename)
        result = unique_json(result_raw.decode())
        # Normal receipts use canonical record hashes. The parent-death probe
        # deliberately has no supervisor result and pins the watchdog bytes.
        observed_digest = (
            hashlib.sha256(result_raw).hexdigest() if name == "parent_death" else digest(result)
        )
        if observed_digest != check.get("execution_receipt"):
            raise ValueError("qualification execution receipt changed")
        if (
            result.get("container_id") != cid
            or result.get("nonce") != intent.get("nonce")
            or result.get("stopped") is not True
        ):
            raise ValueError("qualification execution ownership or stop receipt changed")
        if name == "parent_death":
            if result.get("reason") != "timeout":
                raise ValueError("qualification parent-death deadline was not enforced")
            continue
        if result.get("intent_digest") != digest(intent):
            raise ValueError("qualification result has a different execution intent")
        streams = {}
        for stream in ("stdout", "stderr"):
            streams[stream] = _raw(probe, f"{stream}.bin", limits.output_bytes)
            if hashlib.sha256(streams[stream]).hexdigest() != result.get(f"{stream}_sha256"):
                raise ValueError("qualification output bytes changed")
        if sum(map(len, streams.values())) > limits.output_bytes:
            raise ValueError("qualification output ceiling was exceeded")
        expected_status = {
            "memory": "model_failure",
            "cpu": "model_failure",
            "output": "output_limit",
            "sleep": "timeout",
        }.get(name, "success")
        if (
            result.get("status") != expected_status
            or check.get("observed_status") != expected_status
        ):
            raise ValueError("qualification probe did not enforce the expected boundary")
        if result.get("oom_killed") is not (name == "memory"):
            raise ValueError("qualification memory result differs from the tested outcome")
    return VerifiedQualification(
        expected_digest, receipt["boundary_source_identity"], runtime, limits
    )
