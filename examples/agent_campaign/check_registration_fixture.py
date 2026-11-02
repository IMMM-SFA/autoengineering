"""Bounded trusted registration and standalone lifecycle over authored code.

The review record is a fixture approval, not a claim of human author approval.
No campaign, provider, scientific selection or controller registration is run.
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import shutil
import time

import numpy as np

from autoengineering.adapters.contracts import AdapterRegistry, PrepareContext
from autoengineering.adapters.isolated import registration_entry
from autoengineering.adapters.python import run_lifecycle
from autoengineering.adapters.registration import AdmissionReview, load_registration
from autoengineering.agents.admission import register_candidate
from autoengineering.agents.interface import InterfaceSpec, InterfaceCase, check_interface
from autoengineering.agents.workspaces import CandidateWorkspace
from autoengineering.campaign.records import PortContract, ModelSnapshot
from autoengineering.campaign.serialization import canonical_json, digest
from autoengineering.campaign.store import checked_directory, durable_write

BASE = b'def predict(inputs):\n return {"prediction":inputs["forcing"]}\n'
SOURCE = b'def predict(inputs):\n return {"prediction":inputs["forcing"]*2.0}\n'


def exercise(output: Path, qualification_root: Path, qualification_digest: str):
    output = Path(output).absolute()
    checked_directory(output.parent)
    if output.exists() or output.is_symlink():
        raise ValueError("registration fixture requires a fresh output directory")
    output.mkdir(mode=0o700)
    manifest = {
        "schema_version": "1.0",
        "purpose": "authored-standalone-registration-fixture",
        "maximum_container_starts": 4,
        "max_elapsed_seconds": 60,
        "provider_calls": 0,
        "scientific_campaigns": 0,
        "human_approval_claimed": False,
        "qualification_digest": qualification_digest,
        "fixture_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    durable_write(output / "manifest.json", canonical_json(manifest).encode())
    began = time.monotonic()

    def port(name):
        return PortContract(name, (), "mm/day", "float", (), "scalar", digest([]), None)

    spec = InterfaceSpec(
        "1.0",
        (port("forcing"),),
        (port("prediction"),),
        (
            InterfaceCase("first", {"forcing": 1.5}, {"prediction": 3.0}),
            InterfaceCase("second", {"forcing": 2.5}, {"prediction": 5.0}),
        ),
    )
    work = CandidateWorkspace.create(
        output / "workspace",
        run_id="fixture",
        task_id="implementation",
        baseline={"adapter.py": BASE},
    )
    (work.candidate / "adapter.py").write_bytes(SOURCE)
    capture = work.capture()
    print("Checking authored implementation", flush=True)
    interface = check_interface(
        work,
        capture,
        spec,
        qualification_root=qualification_root,
        qualification_digest=qualification_digest,
        output=output / "interface",
    )
    starts = sum(check.execution_digest is not None for check in interface.checks)
    review = AdmissionReview(
        "1.0",
        "response",
        capture.digest,
        interface.digest,
        qualification_digest,
        {},
        "fixture-caller",
        "Explicit authored-fixture approval, not human review",
        "approve",
    )
    registration = register_candidate(
        work,
        capture,
        spec,
        interface_root=output / "interface",
        qualification_root=qualification_root,
        review=review,
        trusted_review_digest=review.digest,
        output=output / "registration",
    )
    durable_write(output / "review.json", (review.to_json() + "\n").encode())
    # Preserve originals at different paths rather than deleting evidence.
    (output / "workspace").rename(output / "workspace-original")
    (output / "interface").rename(output / "interface-original")
    shutil.copytree(output / "registration", output / "registration-copy")
    runs = []
    for name in ("registration", "registration-copy"):
        if time.monotonic() - began > 60 or starts >= 4:
            raise ValueError("registration fixture allowance exhausted")
        print(f"Running {name}", flush=True)
        root = output / name
        entry = registration_entry(root, expected_identity=registration.digest)
        registry = AdapterRegistry((entry,))
        _, refs = load_registration(root, expected_identity=registration.digest)
        model = ModelSnapshot(
            digest({"single-component": "response"}),
            {"response": entry.id},
            refs,
            digest([]),
            spec.inputs,
            spec.outputs,
        )
        scratch = output / f"{name}-scratch"
        scratch.mkdir(mode=0o700)
        context = PrepareContext(model, {}, 17, str(scratch), ())
        registry.validate(entry.id, model, root)
        adapter = registry.create(entry.id)
        result = run_lifecycle(
            adapter, context, {"forcing": np.asarray(4.0)}, model.inputs, model.outputs
        )
        starts += 1
        expected = float(result.outputs["prediction"]) == 8.0
        stopped = adapter.last_result.stopped
        runs.append(
            {
                "name": name,
                "prediction": float(result.outputs["prediction"]),
                "status": "pass" if expected and stopped else "fail",
                "stopped": stopped,
                "execution_root": str(adapter.last_execution.relative_to(output)),
            }
        )
    elapsed = time.monotonic() - began
    result = {
        **manifest,
        "status": "pass"
        if all(r["status"] == "pass" for r in runs) and starts == 4 and elapsed <= 60
        else "fail",
        "container_starts": starts,
        "registration_identity": registration.digest,
        "adapter_id": registration.adapter_id,
        "runs": runs,
        "elapsed_seconds": elapsed,
    }
    durable_write(output / "result.json", canonical_json(result).encode())
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--qualification-root", type=Path, required=True)
    parser.add_argument("--qualification-digest", required=True)
    args = parser.parse_args()
    result = exercise(args.output, args.qualification_root, args.qualification_digest)
    print(canonical_json(result))
    return 0 if result["status"] == "pass" else 4


if __name__ == "__main__":
    raise SystemExit(main())
