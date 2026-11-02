"""Bounded interface checks over immutable candidate snapshots.

The trusted caller supplies public unit fixtures and a pinned qualification.
Expected values stay outside the container. Passing these checks does not
register an adapter or establish scientific eligibility.
"""

from __future__ import annotations

from collections.abc import Mapping, Callable
from dataclasses import dataclass, asdict
import hashlib
import math
from pathlib import Path
from typing import Literal

from autoengineering.campaign.artifacts import read_bytes, confined_file
from autoengineering.campaign.records import PortContract, identifier, sha256, unique
from autoengineering.campaign.serialization import Record, canonical_json, digest, unique_json
from autoengineering.campaign.store import checked_directory, durable_write
from .containers import DockerBoundary, ContainerResult
from .qualification import verify_qualification
from .workspaces import CandidateWorkspace, SourceCapture, inspect_source

Values = Mapping[str, float | tuple[float, ...]]


class InterfaceRecord(Record):
    """Bound execution contracts independently of worker role and host records."""

    def __post_init__(self):
        super().__post_init__()
        if len(self.to_json().encode()) > 65536:
            raise ValueError("interface record exceeds 64 KiB")

    @classmethod
    def from_json(cls, text):
        if len(text.encode()) > 65536:
            raise ValueError("interface record exceeds 64 KiB")
        return super().from_json(text)


@dataclass(frozen=True)
class InterfaceCase(InterfaceRecord):
    id: str
    inputs: Values
    expected: Values

    def _validate(self):
        identifier(self.id)


def _check_shape(values, ports, *, raw=False):
    if not isinstance(values, Mapping) or set(values) != {p.name for p in ports}:
        raise ValueError("interface values differ from declared port names")
    count = 0
    for port in ports:
        value = values[port.name]
        if port.time is None:
            numbers = [value]
        else:
            if not isinstance(value, list if raw else tuple) or len(value) != len(port.time.dates):
                raise ValueError("interface values differ from the declared time axis")
            numbers = value
        if any(type(number) is not float or not math.isfinite(number) for number in numbers):
            raise ValueError("interface values must be finite floating point numbers")
        count += len(numbers)
    if count > 128:
        raise ValueError("initial interface supports at most 128 values per input or output")


@dataclass(frozen=True)
class InterfaceSpec(InterfaceRecord):
    schema_version: Literal["1.0"]
    inputs: tuple[PortContract, ...]
    outputs: tuple[PortContract, ...]
    cases: tuple[InterfaceCase, ...]
    absolute_tolerance: float = 1e-12

    def _validate(self):
        if not 1 <= len(self.cases) <= 4 or not 0 <= self.absolute_tolerance <= 1e-6:
            raise ValueError("interface fixture allowance or tolerance exceeds initial policy")
        unique([case.id for case in self.cases], "interface case")
        for ports in (self.inputs, self.outputs):
            if not 1 <= len(ports) <= 4 or any(p.dtype_family != "float" for p in ports):
                raise ValueError("initial interface requires one to four float ports")
            unique([p.name for p in ports], "interface port")
        for case in self.cases:
            _check_shape(case.inputs, self.inputs)
            _check_shape(case.expected, self.outputs)


@dataclass(frozen=True)
class InterfaceCheck(InterfaceRecord):
    case_id: str
    status: Literal["pass", "fail", "not_attempted", "reconciliation_required"]
    reason: str
    execution_digest: str | None

    def _validate(self):
        identifier(self.case_id)
        if self.execution_digest is not None:
            sha256(self.execution_digest)


@dataclass(frozen=True)
class InterfaceReceipt(InterfaceRecord):
    schema_version: Literal["1.0"]
    source_digest: str
    capture_digest: str
    specification_digest: str
    qualification_digest: str
    runner_identity: str
    status: Literal["pass", "fail", "reconciliation_required"]
    checks: tuple[InterfaceCheck, ...]

    def _validate(self):
        for value in (
            self.source_digest,
            self.capture_digest,
            self.specification_digest,
            self.qualification_digest,
            self.runner_identity,
        ):
            sha256(value)
        unique([c.case_id for c in self.checks], "interface check")
        expected = (
            "reconciliation_required"
            if any(c.status == "reconciliation_required" for c in self.checks)
            else (
                "pass" if self.checks and all(c.status == "pass" for c in self.checks) else "fail"
            )
        )
        if self.status != expected:
            raise ValueError("interface receipt contradicts its executed checks")


def runner_identity():
    package = Path(__file__).parent
    return digest(
        {
            name: hashlib.sha256(confined_file(package, name).read_bytes()).hexdigest()
            for name in ("interface.py", "interface_worker.py", "workspaces.py", "qualification.py")
        }
    )


def decode_output(raw, ports):
    """Validate the fixed driver envelope without consulting labels or fixture values."""
    output = unique_json(raw.decode("utf-8"))
    if (
        not isinstance(output, dict)
        or set(output) != {"schema_version", "outputs", "inputs_unchanged"}
        or output["schema_version"] != "1.0"
        or output["inputs_unchanged"] is not True
    ):
        raise ValueError("invalid output envelope or mutated inputs")
    _check_shape(output["outputs"], ports, raw=True)
    return output["outputs"]


def _validate_output(raw, case, spec):
    outputs = decode_output(raw, spec.outputs)
    for name, wanted in case.expected.items():
        actual = outputs[name]
        pairs = zip(actual, wanted) if isinstance(wanted, tuple) else [(actual, wanted)]
        if any(abs(left - right) > spec.absolute_tolerance for left, right in pairs):
            raise ValueError("public interface fixture value mismatch")


def _sources(workspace, capture):
    CandidateWorkspace(workspace.root, workspace.manifest).verify_capture(capture)
    if capture.issues or set(capture.sources) != {"adapter.py"}:
        raise ValueError("candidate capture has source policy failures")
    source = read_bytes(workspace.root, capture.sources["adapter.py"], max_bytes=65536)
    if inspect_source(source):
        raise ValueError("candidate source independently failed static policy")
    driver = confined_file(Path(__file__).parent, "interface_worker.py").read_bytes()
    if len(source) + len(driver) > 65536:
        raise ValueError("candidate and fixed driver exceed the source envelope")
    return {"adapter.py": source, "driver.py": driver}


def _check_result(result, case, spec):
    if not result.stopped:
        return "reconciliation_required", "container_stop_unverified"
    if result.status != "success":
        return "fail", result.status
    try:
        _validate_output(result.stdout, case, spec)
        return "pass", "public_fixture_passed"
    except (ValueError, TypeError, UnicodeError, RecursionError):
        return "fail", "output_contract_or_fixture_failed"


def _manifest(capture, spec, qualified, sources, execution_root):
    return {
        "schema_version": "1.1",
        "execution_root": str(execution_root),
        "capture": capture.to_dict(),
        "specification": spec.to_dict(),
        "qualification_digest": qualified.receipt_digest,
        "runtime": asdict(qualified.runtime),
        "runner_identity": runner_identity(),
        "driver_digest": hashlib.sha256(sources["driver.py"]).hexdigest(),
        "maximum_container_starts": len(spec.cases),
        "wall_seconds_per_case": 5,
    }


def check_interface(
    workspace: CandidateWorkspace,
    capture: SourceCapture,
    spec: InterfaceSpec,
    *,
    qualification_root: Path,
    qualification_digest: str,
    output: Path,
    cancelled: Callable[[], bool] = lambda: False,
) -> InterfaceReceipt:
    # Recheck the manifest, immutable capture and source policy independently of
    # a worker's claimed checks. Never import candidate code on the host.
    if cancelled():
        raise ValueError("interface checks cancelled before launch")
    sources = _sources(workspace, capture)
    qualified = verify_qualification(qualification_root, expected_digest=qualification_digest)
    output = Path(output).absolute()
    checked_directory(output.parent)
    if output.exists() or output.is_symlink():
        raise ValueError("interface check requires a fresh output directory")
    identity = runner_identity()
    manifest = _manifest(capture, spec, qualified, sources, output)
    manifest_raw = canonical_json(manifest).encode()
    if len(manifest_raw) > 65536:
        raise ValueError("interface manifest exceeds 64 KiB")
    output.mkdir(mode=0o700)
    durable_write(output / "manifest.json", manifest_raw)
    boundary = DockerBoundary(qualified.runtime)
    checks = []
    for index, case in enumerate(spec.cases):
        if cancelled():
            raise ValueError("interface checks cancelled between cases")
        if checks and checks[-1].status != "pass":
            checks.append(
                InterfaceCheck(case.id, "not_attempted", "earlier_case_did_not_pass", None)
            )
            continue
        payload = canonical_json(
            {"schema_version": "1.0", "inputs": case.to_dict()["inputs"]}
        ).encode()
        result = boundary.run_qualified(
            sources,
            qualification_root=qualification_root,
            qualification_digest=qualification_digest,
            entrypoint="driver.py",
            payload=payload,
            root=output / f"case-{index:03d}",
            limits=qualified.limits,
            wall_seconds=5,
            cancelled=cancelled,
        )
        status, reason = _check_result(result, case, spec)
        checks.append(InterfaceCheck(case.id, status, reason, result.receipt_digest))
    status = (
        "reconciliation_required"
        if any(c.status == "reconciliation_required" for c in checks)
        else ("pass" if all(c.status == "pass" for c in checks) else "fail")
    )
    receipt = InterfaceReceipt(
        "1.0",
        capture.source_digest,
        capture.digest,
        spec.digest,
        qualification_digest,
        identity,
        status,
        tuple(checks),
    )
    durable_write(output / "receipt.json", (receipt.to_json() + "\n").encode())
    return receipt


def _read(root, name, ceiling=65536):
    path = confined_file(root, name)
    if path.stat().st_size > ceiling:
        raise ValueError("interface artifact exceeds its byte ceiling")
    raw = path.read_bytes()
    if len(raw) > ceiling:
        raise ValueError("interface artifact exceeds its byte ceiling")
    return raw


def verify_interface(
    output: Path,
    workspace: CandidateWorkspace,
    capture: SourceCapture,
    spec: InterfaceSpec,
    *,
    qualification_root: Path,
    qualification_digest: str,
    expected_receipt_digest: str,
    relocated: bool = False,
) -> InterfaceReceipt:
    """Reconstruct checks and policy from pinned evidence without executing anything."""
    output = checked_directory(output)
    receipt = InterfaceReceipt.from_json(_read(output, "receipt.json").decode())
    if receipt.digest != expected_receipt_digest:
        raise ValueError("interface receipt differs from the trusted digest")
    sources = _sources(workspace, capture)
    qualified = verify_qualification(qualification_root, expected_digest=qualification_digest)
    manifest = unique_json(_read(output, "manifest.json").decode())
    origin = manifest.get("execution_root")
    if (
        type(relocated) is not bool
        or type(origin) is not str
        or not Path(origin).is_absolute()
        or ".." in Path(origin).parts
    ):
        raise ValueError("interface execution origin is invalid")
    expected_root = origin if relocated else str(output)
    if manifest != _manifest(capture, spec, qualified, sources, expected_root):
        raise ValueError("interface manifest, source, driver or runtime identity changed")
    if (
        receipt.source_digest != capture.source_digest
        or receipt.capture_digest != capture.digest
        or receipt.specification_digest != spec.digest
        or receipt.qualification_digest != qualification_digest
        or receipt.runner_identity != runner_identity()
        or tuple(check.case_id for check in receipt.checks) != tuple(case.id for case in spec.cases)
    ):
        raise ValueError("interface receipt has a different source or check context")
    executed = set()
    stopped_early = False
    boundary = DockerBoundary(qualified.runtime)
    for index, (case, check) in enumerate(zip(spec.cases, receipt.checks)):
        name = f"case-{index:03d}"
        if stopped_early:
            if check != InterfaceCheck(case.id, "not_attempted", "earlier_case_did_not_pass", None):
                raise ValueError("interface receipt hides or relabels a skipped case")
            continue
        executed.add(name)
        root = checked_directory(output / name)
        intent = unique_json(_read(root, "intent.json").decode())
        result = unique_json(_read(root, "result.json").decode())
        if digest(result) != check.execution_digest:
            raise ValueError("interface physical execution receipt changed")
        if (
            result.get("status")
            not in (
                "success",
                "model_failure",
                "timeout",
                "output_limit",
                "cancelled",
                "reconciliation_required",
            )
            or type(result.get("stopped")) is not bool
            or type(result.get("oom_killed")) is not bool
            or type(result.get("elapsed_seconds")) not in (int, float)
            or not math.isfinite(result["elapsed_seconds"])
            or result["elapsed_seconds"] < 0
        ):
            raise ValueError("interface execution receipt contains invalid status or timing")
        payload = canonical_json(
            {"schema_version": "1.0", "inputs": case.to_dict()["inputs"]}
        ).encode()
        if (
            intent.get("sources")
            != {name: hashlib.sha256(raw).hexdigest() for name, raw in sources.items()}
            or intent.get("version") != boundary.version
            or intent.get("entrypoint") != "driver.py"
            or intent.get("wall_seconds") != 5
            or intent.get("image_id") != qualified.runtime.image_id
            or intent.get("repository_digest") != qualified.runtime.repository_digest
            or intent.get("input_sha256") != hashlib.sha256(payload).hexdigest()
            or _read(root, "stdin.bin") != payload
            or result.get("intent_digest") != digest(intent)
            or result.get("nonce") != intent.get("nonce")
            or result.get("image_id") != qualified.runtime.image_id
            or _read(root, "container-id").decode() != result.get("container_id")
            or any(intent.get(key) != value for key, value in asdict(qualified.limits).items())
        ):
            raise ValueError("interface physical intent differs from the frozen fixture or limits")
        for filename, raw in sources.items():
            if _read(root, f"export/{filename}") != raw:
                raise ValueError("interface executed source bytes changed")
        policy_raw = _read(root, "effective-policy.json")
        if hashlib.sha256(policy_raw).hexdigest() != result.get("effective_policy_sha256"):
            raise ValueError("interface effective container policy changed")
        policy = unique_json(policy_raw.decode())
        boundary._verify_policy(
            {
                "Id": policy["id"],
                "Image": policy["image"],
                "HostConfig": policy["host"],
                "Config": policy["config"],
                "Mounts": policy["mounts"],
            },
            root=root,
            nonce=intent["nonce"],
            intent=digest(intent),
            export=Path(origin) / name / "export",
            limits=qualified.limits,
        )
        raw_streams = {}
        for stream in ("stdout", "stderr"):
            raw_streams[stream] = _read(root, f"{stream}.bin", qualified.limits.output_bytes)
            if hashlib.sha256(raw_streams[stream]).hexdigest() != result.get(f"{stream}_sha256"):
                raise ValueError("interface captured output changed")
        if sum(map(len, raw_streams.values())) > qualified.limits.output_bytes:
            raise ValueError("interface output exceeds the combined byte ceiling")
        actual = ContainerResult(
            result["status"],
            result["container_id"],
            raw_streams["stdout"],
            raw_streams["stderr"],
            result["stopped"],
            result["oom_killed"],
            result["elapsed_seconds"],
            digest(result),
        )
        status, reason = _check_result(actual, case, spec)
        if check != InterfaceCheck(case.id, status, reason, digest(result)):
            raise ValueError("interface check contradicts its executed fixture")
        stopped_early = status != "pass"
    if {p.name for p in output.glob("case-*")} != executed:
        raise ValueError("interface output contains unaccounted case artifacts")
    return receipt
