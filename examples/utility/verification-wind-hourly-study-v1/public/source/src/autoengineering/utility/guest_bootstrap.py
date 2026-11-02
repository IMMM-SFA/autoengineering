"""Fixed one-shot stdio bootstrap for the candidate tmpfs inference guest.

The owner must attach before the single container start, stream one request and
close stdin. Output artifacts leave on stdout before PID 1 exits and tmpfs vanishes.
No daemon, installation, image acquisition or runtime admission occurs here.
"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass
import hashlib
import io
from pathlib import Path
import struct
import sys
from typing import Literal

from autoengineering.campaign.artifacts import confined_file, put_bytes, read_bytes
from autoengineering.campaign.records import ArtifactRef
from autoengineering.campaign.serialization import Record, unique_json
from autoengineering.campaign.store import StoreError, checked_directory, durable_write
from .contracts import sha256
from .guest_inputs import (
    GuestInputPackage,
    MAX_TAR_BYTES,
    verify_guest_inputs,
    verify_guest_input_contents,
)
from .guest_receipts import GuestLaunchIntent, GuestStdinPolicy
from .inference_execution import FrozenGuestInferenceJob, FrozenInferenceResult

REQUEST_MAGIC = b"AEGUEST1\n"
RESPONSE_MAGIC = b"AEGUEST-RESULT1\n"
MAX_HEADER = 4 * 1024 * 1024
MAX_RESULT_HEADER = 65536
MAX_PREDICTION = 1048576


@dataclass(frozen=True)
class GuestBootstrapRequest(Record):
    schema: Literal["utility-guest-bootstrap-request-v1"]
    job: FrozenGuestInferenceJob
    launch: GuestLaunchIntent
    claim: ArtifactRef
    package: GuestInputPackage
    input_intent_json: str

    def _validate(self):
        if not isinstance(self.launch.policy, GuestStdinPolicy):
            raise ValueError("guest bootstrap requires the versioned stdin policy")
        if len(self.input_intent_json.encode()) > 65536:
            raise ValueError("guest bootstrap input intent exceeds bound")
        if not any(
            e.artifact.path == "src/autoengineering/utility/guest_bootstrap.py"
            and e.role == "core_source"
            for e in self.package.entries
        ):
            raise ValueError("guest bootstrap code is absent from frozen transfer closure")
        from .guest_observations import _launch

        _launch(self.job, self.launch)
        if (self.package.job_digest, self.package.launch_digest, self.package.claim_digest) != (
            self.job.digest,
            self.launch.digest,
            self.claim.sha256,
        ) or self.launch.claim_digest != self.claim.sha256:
            raise ValueError("guest bootstrap header belongs to another original transfer")
        # Full closure and original claim bytes are checked with the archive.
        if self.package.archive.size_bytes > MAX_TAR_BYTES:
            raise ValueError("guest bootstrap transfer exceeds bound")


@dataclass(frozen=True)
class GuestBootstrapResponse(Record):
    schema: Literal["utility-guest-bootstrap-response-v1"]
    job_digest: str
    launch_digest: str
    package_digest: str
    result: FrozenInferenceResult
    artifacts: tuple[ArtifactRef, ...]

    def _validate(self):
        for value in (self.job_digest, self.launch_digest, self.package_digest):
            sha256(value)
        refs = tuple(
            ref for ref in (self.result.outputs, self.result.predictions) if ref is not None
        )
        if self.artifacts != refs:
            raise ValueError("guest response must contain only original result artifacts")
        for ref, name, media in (
            (self.result.outputs, "outputs.npz", "application/x-npz"),
            (self.result.predictions, "predictions.json", "application/json"),
        ):
            if ref is not None and (
                ref.path != f"artifacts/{ref.sha256}/{name}"
                or ref.media_type != media
                or ref.metadata
            ):
                raise ValueError("guest response artifact is outside fixed outputs")
        if (
            self.result.predictions is not None
            and self.result.predictions.size_bytes > MAX_PREDICTION
        ):
            raise ValueError("guest response predictions exceed bound")
        if self.result.outputs is not None and self.result.outputs.size_bytes > 64 * 1024 * 1024:
            raise ValueError("guest response outputs exceed bound")


@dataclass(frozen=True)
class GuestBootstrapCapture(Record):
    schema: Literal["utility-guest-bootstrap-capture-v1"]
    job_digest: str
    launch_digest: str
    package_digest: str
    response_digest: str
    worker_result: ArtifactRef

    def _validate(self):
        for value in (
            self.job_digest,
            self.launch_digest,
            self.package_digest,
            self.response_digest,
        ):
            sha256(value)
        if self.worker_result.size_bytes > MAX_RESULT_HEADER:
            raise ValueError("guest captured result exceeds bound")


def _read(stream, size):
    chunks = bytearray()
    while len(chunks) < size:
        part = stream.read(min(size - len(chunks), 65536))
        if not isinstance(part, bytes) or not part:
            raise StoreError("guest transport ended before its bounded frame")
        chunks.extend(part)
    return bytes(chunks)


def _write(stream, raw):
    view = memoryview(raw)
    while view:
        size = min(len(view), 65536)
        written = stream.write(view[:size])
        if type(written) is not int or not 0 < written <= size:
            raise StoreError("guest transport output did not complete")
        view = view[written:]


def _header(stream, magic, kind, limit):
    if _read(stream, len(magic)) != magic:
        raise StoreError("guest transport frame version differs")
    size = struct.unpack("!I", _read(stream, 4))[0]
    if not 0 < size <= limit:
        raise StoreError("guest transport header exceeds bound")
    raw = _read(stream, size)
    try:
        record = kind.from_json(raw.decode())
    except (ValueError, TypeError, UnicodeError):
        raise StoreError("guest transport header is malformed") from None
    if record.to_json().encode() != raw:
        raise StoreError("guest transport header is not canonical")
    return record


def _frame(magic, record, limit):
    raw = record.to_json().encode()
    if len(raw) > limit:
        raise StoreError("guest transport header exceeds bound")
    return magic + struct.pack("!I", len(raw)) + raw


def encode_request(owner):
    """Build one request from committed inputs; no original driver/root access."""
    m = owner.manifest
    if not isinstance(m.launch.policy, GuestStdinPolicy):
        raise StoreError("guest stdin transport refuses legacy direct-worker policy")
    package = verify_guest_inputs(owner.root, m.job, m.launch, m.claim)
    request = GuestBootstrapRequest(
        "utility-guest-bootstrap-request-v1",
        m.job,
        m.launch,
        m.claim,
        package,
        confined_file(owner.root, "input-intent.json").read_text(),
    )
    raw = read_bytes(owner.root, package.archive, max_bytes=MAX_TAR_BYTES)
    return _frame(REQUEST_MAGIC, request, MAX_HEADER) + raw


def decode_request(stream):
    request = _header(stream, REQUEST_MAGIC, GuestBootstrapRequest, MAX_HEADER)
    raw = _read(stream, request.package.archive.size_bytes)
    if stream.read(1) != b"":
        raise StoreError("guest request has trailing input")
    contents = verify_guest_input_contents(
        request.package,
        request.job,
        request.launch,
        request.claim,
        unique_json(request.input_intent_json),
        raw,
    )
    return request, contents


def _result_binding(result, job):
    if (result.grant_digest, result.executor_digest, result.nonce) != (
        job.grant.digest,
        job.executor_digest,
        job.nonce,
    ):
        raise StoreError("guest result belongs to another original job")
    if (
        result.outputs is not None
        and result.outputs.size_bytes > job.grant.inference.output_limit_bytes
    ):
        raise StoreError("guest result exceeds reserved output allowance")


def encode_response(root, request):
    """Capture only fixed result/output files while the tmpfs guest still lives."""
    path = confined_file(root, "worker-result.json")
    if path.stat().st_size > MAX_RESULT_HEADER:
        raise StoreError("guest result envelope exceeds bound")
    raw_result = path.read_bytes()
    result = FrozenInferenceResult.from_json(raw_result.decode())
    if raw_result != result.to_json().encode():
        raise StoreError("guest original result is not canonical")
    _result_binding(result, request.job)
    refs = tuple(ref for ref in (result.outputs, result.predictions) if ref is not None)
    response = GuestBootstrapResponse(
        "utility-guest-bootstrap-response-v1",
        request.job.digest,
        request.launch.digest,
        request.package.digest,
        result,
        refs,
    )
    payload = [read_bytes(root, ref, max_bytes=64 * 1024 * 1024) for ref in refs]
    return _frame(RESPONSE_MAGIC, response, MAX_RESULT_HEADER) + b"".join(payload)


def capture_response(root, stream, job, launch, package):
    """Publish a complete original response last; interrupted reads cannot relaunch."""
    root = checked_directory(root)
    path = root / "bootstrap-capture.json"
    if path.exists() or path.is_symlink():
        raise StoreError("original guest capture already exists; use saved evidence")
    response = _header(stream, RESPONSE_MAGIC, GuestBootstrapResponse, MAX_RESULT_HEADER)
    if (response.job_digest, response.launch_digest, response.package_digest) != (
        job.digest,
        launch.digest,
        package.digest,
    ):
        raise StoreError("guest response belongs to another original transfer")
    _result_binding(response.result, job)
    raw = bytearray(_frame(RESPONSE_MAGIC, response, MAX_RESULT_HEADER))
    payloads = []
    for ref in response.artifacts:
        content = _read(stream, ref.size_bytes)
        if hashlib.sha256(content).hexdigest() != ref.sha256:
            raise StoreError("guest response artifact digest differs")
        raw.extend(content)
        payloads.append(content)
    if stream.read(1) != b"":
        raise StoreError("guest response has trailing output")
    # No partial transport output is published as a completed worker result.
    for ref, content in zip(response.artifacts, payloads, strict=True):
        saved = put_bytes(
            root,
            content,
            name=Path(ref.path).name,
            media_type=ref.media_type,
            producer=ref.producer,
        )
        if saved != ref:
            raise StoreError("guest captured artifact differs from original result")
    result = put_bytes(
        root,
        response.result.to_json().encode(),
        name="worker-result.json",
        media_type="application/json",
        producer="guest-transport",
    )
    capture = GuestBootstrapCapture(
        "utility-guest-bootstrap-capture-v1",
        job.digest,
        launch.digest,
        package.digest,
        hashlib.sha256(raw).hexdigest(),
        result,
    )
    durable_write(root / "bootstrap-capture.json", capture.to_json().encode())
    return capture


def read_capture(root, job, launch, package):
    """Verify an original completed capture without a stream, model or writes."""
    root = checked_directory(root)
    path = confined_file(root, "bootstrap-capture.json")
    if path.stat().st_size > MAX_RESULT_HEADER:
        raise StoreError("guest saved capture exceeds bound")
    capture = GuestBootstrapCapture.from_json(path.read_text())
    if (capture.job_digest, capture.launch_digest, capture.package_digest) != (
        job.digest,
        launch.digest,
        package.digest,
    ):
        raise StoreError("guest saved capture belongs to another original transfer")
    result = FrozenInferenceResult.from_json(
        read_bytes(root, capture.worker_result, max_bytes=MAX_RESULT_HEADER).decode()
    )
    _result_binding(result, job)
    refs = tuple(ref for ref in (result.outputs, result.predictions) if ref is not None)
    response = GuestBootstrapResponse(
        "utility-guest-bootstrap-response-v1",
        job.digest,
        launch.digest,
        package.digest,
        result,
        refs,
    )
    digest = hashlib.sha256(_frame(RESPONSE_MAGIC, response, MAX_RESULT_HEADER))
    for ref in refs:
        digest.update(read_bytes(root, ref, max_bytes=64 * 1024 * 1024))
    if digest.hexdigest() != capture.response_digest:
        raise StoreError("guest saved response differs from original capture")
    return capture


class _NoDiagnostics(io.TextIOBase):
    def __init__(self):
        self.count = 0

    def write(self, text):
        self.count += len(text)
        if self.count > 65536:
            raise StoreError("guest diagnostic output exceeds bound")
        return len(text)


def run(root, incoming, outgoing):
    """Validate, unpack into this process's private root, run once and stream back.

    The fixed worker performs its existing actual interpreter/installed-wheel
    checks before driver interpretation or model access. No uploaded code executes.
    """
    root = checked_directory(root)
    if any(root.iterdir()):
        raise StoreError("guest bootstrap requires a fresh empty workspace")
    request, contents = decode_request(incoming)
    from .inference_guest import observe_python

    try:
        observed = observe_python()
    except ValueError:
        observed = None
    if observed != request.job.guest.python:
        raise StoreError("guest bootstrap interpreter differs from fixed profile")
    for entry in request.package.entries:
        ref = entry.artifact
        parent = root
        for part in Path(ref.path).parts[:-1]:
            parent = parent / part
            parent.mkdir(mode=0o700, exist_ok=True)
            checked_directory(parent)
        durable_write(root / ref.path, contents[ref.path])
    request.job.validate_runtime(root)
    from .inference_worker import main as worker

    with contextlib.redirect_stdout(_NoDiagnostics()), contextlib.redirect_stderr(_NoDiagnostics()):
        worker(root / "job.json")
    _write(outgoing, encode_response(root, request))
    outgoing.flush()
    return 0


def main():
    if sys.argv[1:] != ["/work/job.json"]:
        return 2
    try:
        return run(Path("/work"), sys.stdin.buffer, sys.stdout.buffer)
    except Exception:
        # Deliberately emit no raw exception, path, model or driver content.
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
