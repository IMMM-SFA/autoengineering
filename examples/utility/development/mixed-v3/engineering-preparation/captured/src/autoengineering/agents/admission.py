"""Trusted source promotion. No worker operation invokes this module.

Approval is a caller-supplied review pinned independently of the worker bundle.
This prepares an application registry entry, not a scientific campaign mutation.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
import tempfile

from autoengineering.adapters.registration import (
    AdmissionReview,
    SourceRegistration,
    make_archive,
    extract_archive,
    load_registration,
    verify_evidence,
    execution_source_identity,
)
from autoengineering.campaign.artifacts import read_bytes, confined_file
from autoengineering.campaign.store import checked_directory, durable_write
from .interface import InterfaceSpec, verify_interface
from .qualification import CHECKS
from .workspaces import CandidateWorkspace, SourceCapture


CASE_FILES = {
    "intent.json",
    "container-id",
    "watchdog-job.json",
    "watchdog.log",
    "watchdog-ready.json",
    "watchdog-result.json",
    "result.json",
    "stdout.bin",
    "stderr.bin",
    "effective-policy.json",
    "stdin.bin",
    "stop-container.json",
}


def _tree(root, prefix, allowed):
    files = {}
    root = checked_directory(root)
    for index, path in enumerate(root.rglob("*")):
        if index >= 1024 or path.is_symlink():
            raise ValueError("registration evidence has too many entries or a symlink")
        if path.is_dir():
            continue
        name = path.relative_to(root).as_posix()
        if name not in allowed:
            raise ValueError("registration evidence contains an undeclared file")
        file = confined_file(root, name)
        if file.stat().st_size > 65536:
            raise ValueError("registration evidence member exceeds 64 KiB")
        files[f"{prefix}/{name}"] = file.read_bytes()
    return files


def _packet(workspace, capture, spec, interface_root, qualification_root):
    qualification_names = {"manifest.json", "qualification.json", "runtime.json", "private-labels"}
    for name in CHECKS:
        name = "parent-death" if name == "parent_death" else name
        qualification_names |= {f"{name}/{file}" for file in CASE_FILES | {"export/probe.py"}}
    interface_names = {"manifest.json", "receipt.json"}
    for index in range(len(spec.cases)):
        interface_names |= {
            f"case-{index:03d}/{file}"
            for file in CASE_FILES | {"export/adapter.py", "export/driver.py"}
        }
    files = _tree(qualification_root, "qualification", qualification_names)
    files.update(_tree(interface_root, "interface", interface_names))
    files["workspace/manifest.json"] = workspace.manifest.to_json().encode()
    for ref in (
        *workspace.manifest.base_sources.values(),
        *capture.sources.values(),
        capture.patch,
    ):
        files[f"workspace/{ref.path}"] = read_bytes(workspace.root, ref, max_bytes=65536)
    return files


def register_candidate(
    workspace: CandidateWorkspace,
    capture: SourceCapture,
    spec: InterfaceSpec,
    *,
    interface_root: Path,
    qualification_root: Path,
    review: AdmissionReview,
    trusted_review_digest: str,
    output: Path,
) -> SourceRegistration:
    if review.digest != trusted_review_digest:
        raise ValueError("admission review differs from the trusted caller pin")
    if review.decision != "approve" or review.capture_digest != capture.digest:
        raise ValueError("admission requires approval of the exact captured source")
    receipt = verify_interface(
        interface_root,
        workspace,
        capture,
        spec,
        qualification_root=qualification_root,
        qualification_digest=review.qualification_digest,
        expected_receipt_digest=review.interface_digest,
    )
    if receipt.status != "pass":
        raise ValueError("failed interface evidence cannot be registered")
    archive = make_archive(_packet(workspace, capture, spec, interface_root, qualification_root))
    driver = confined_file(Path(__file__).parent, "interface_worker.py").read_bytes()
    registration = SourceRegistration(
        "1.1",
        capture,
        spec,
        receipt,
        review,
        hashlib.sha256(driver).hexdigest(),
        hashlib.sha256(archive).hexdigest(),
        len(archive),
        execution_source_identity(),
    )
    output = Path(output).absolute()
    checked_directory(output.parent)
    if output.exists() or output.is_symlink():
        raise ValueError("trusted registration requires a fresh directory")
    # Recheck archive portability before publishing any registration files.
    with tempfile.TemporaryDirectory(prefix="registration-verify-", dir=output.parent) as scratch:
        unpacked = Path(scratch) / "evidence"
        extract_archive(archive, unpacked)
        verify_evidence(unpacked, registration)
    output.mkdir(mode=0o700)
    (output / "generated").mkdir(mode=0o700)
    payloads = {
        "registration.json": (registration.to_json() + "\n").encode(),
        "adapter.py": read_bytes(workspace.root, capture.sources["adapter.py"], max_bytes=65536),
        "driver.py": driver,
        "evidence.zip": archive,
    }
    for name, raw in payloads.items():
        durable_write(output / "generated" / name, raw)
    load_registration(output, expected_identity=registration.digest)
    return registration
