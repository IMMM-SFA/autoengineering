"""Bounded macOS private JSON-vector scorer using existing sandbox/supervision.

The profile scores frozen predictions only. It does not import models, train,
fetch labels, or qualify any host's access to the private directory.
"""
from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

from autoengineering.agents.process import supervise_process, read_completion
from autoengineering.agents.sandbox import MacOSBoundary, BoundaryLimits
from autoengineering.campaign.artifacts import read_bytes, confined_file
from autoengineering.campaign.serialization import canonical_json, digest, unique_json
from autoengineering.campaign.store import checked_directory, durable_write, StoreError
from .scoring import PublicScore


class PrivateRMSEScorer:
    def __init__(self, public_root, private_root, *, labels, predictions, partition_digest,
                 outcome_contract, timeout_seconds=5., limits=BoundaryLimits()):
        self.public_root, self.private_root = checked_directory(public_root), checked_directory(private_root)
        if self.private_root.is_relative_to(self.public_root) or self.public_root.is_relative_to(self.private_root):
            raise StoreError("private scoring scope must be separate from the public suite")
        if outcome_contract.name != "rmse" or outcome_contract.direction != "minimize":
            raise ValueError("private vector profile supports registered minimized RMSE only")
        if type(timeout_seconds) not in (float, int) or not 0 < timeout_seconds <= 60:
            raise ValueError("private scoring needs a positive timeout of at most 60 seconds")
        self.labels, self.predictions = labels, predictions
        self.partition_digest, self.outcome_contract = partition_digest, outcome_contract
        self.timeout, self.limits = float(timeout_seconds), limits
        self.boundary = MacOSBoundary()  # No permissive fallback on other platforms.
        if not data_limit_available(self.limits.memory_bytes):
            raise StoreError("private scoring memory boundary is unqualified on this platform")
        self.worker = Path(__file__).with_name("private_score_worker.py")
        self.worker_bytes = confined_file(self.worker.parent, self.worker.name).read_bytes()
        # Bind private bytes without exposing their path or contents publicly.
        read_bytes(self.private_root, labels)
        read_bytes(self.public_root, predictions)
        self.identity = digest({"profile": "private-json-rmse-macos-v1", "labels": labels.sha256,
            "predictions": predictions.sha256, "partition": partition_digest,
            "outcome": outcome_contract.digest, "worker": hashlib.sha256(self.worker_bytes).hexdigest(),
            "boundary": self.boundary.identity(self.private_root, limits), "timeout": self.timeout})

    def _scope(self, grant, model):
        if (grant.scorer_digest, grant.partition_digest, grant.outcome_digest) != (
                self.identity, self.partition_digest, self.outcome_contract.digest):
            raise StoreError("private scorer grant differs from registration")
        active = next((r for r in grant.resources if r.name == "active_time"), None)
        if active is None or active.units != "s" or active.enforcement != "reservation" or active.limit < self.timeout + .4:
            raise StoreError("private scorer needs reserved time covering timeout and stop grace")
        if model.sha256 != grant.model_digest:
            raise StoreError("private scorer model differs from grant")
        return self.private_root / grant.digest

    def __call__(self, grant, model):
        root = self._scope(grant, model)
        if root.exists() or root.is_symlink():
            raise StoreError("private scorer attempt already exists; explicit recovery required")
        labels = read_bytes(self.private_root, self.labels)
        document = unique_json(read_bytes(self.public_root, self.predictions).decode())
        if not isinstance(document, dict) or set(document) != {"model_sha256", "partition_digest", "selection_digest", "prediction"}:
            raise StoreError("frozen predictions have invalid schema")
        if (document["model_sha256"], document["partition_digest"], document["selection_digest"]) != (
                model.sha256, self.partition_digest, grant.selection_digest):
            raise StoreError("frozen predictions differ from selected model or partition")
        root.mkdir(mode=0o700)
        work = root / "workspace"
        work.mkdir(mode=0o700)
        durable_write(work / "score.py", self.worker_bytes)
        durable_write(work / "labels.json", labels)
        durable_write(work / "job.json", canonical_json({"prediction": document["prediction"],
            "outcome": self.outcome_contract.name, "units": self.outcome_contract.units}).encode())
        durable_write(root / "binding.json", canonical_json({"grant": grant.digest,
            "scorer": self.identity, "model": model.sha256}).encode())
        result = supervise_process(self.boundary.command(work, "score.py", self.limits),
            directory=root / "process", cwd=work, environment={}, nonce="score-" + grant.digest[:32],
            stdin=b"", timeout_seconds=self.timeout, max_output_bytes=self.limits.output_bytes,
            on_launch=lambda identity: durable_write(root / "launch.json", canonical_json(identity).encode()),
            parent_watchdog=True)
        if result.status != "completed" or result.returncode != 0 or not result.stopped or result.truncated:
            raise StoreError("private scorer did not produce a verified bounded result")
        score = PublicScore.from_json(result.stdout.decode())
        if (score.outcome, score.units) != (self.outcome_contract.name, self.outcome_contract.units):
            raise StoreError("private scorer returned incompatible public semantics")
        durable_write(root / "public-score.json", score.to_json().encode())
        return score

    def recover(self, grant, model):
        """Read an already-completed private worker; never restart it or open labels."""
        root = checked_directory(self._scope(grant, model))
        binding = unique_json(confined_file(root, "binding.json").read_text())
        if binding != {"grant": grant.digest, "scorer": self.identity, "model": model.sha256}:
            raise StoreError("private recovery binding changed")
        receipt = read_completion(root / "process")
        if (receipt["status"] != "completed" or receipt["returncode"] != 0
                or not receipt["stopped"] or receipt["truncated"]):
            raise StoreError("private process completion remains uncertain")
        raw = confined_file(root / "process", "stdout.bin").read_bytes()
        if hashlib.sha256(raw).hexdigest() != receipt["stdout_sha256"]:
            raise StoreError("private scorer public output changed")
        score = PublicScore.from_json(raw.decode())
        if (score.outcome, score.units) != (self.outcome_contract.name, self.outcome_contract.units):
            raise StoreError("private recovery public semantics changed")
        return score


def data_limit_available(memory_bytes):
    """Test the requested kernel limit without reading private data or running a model."""
    code = ("import resource; resource.setrlimit(resource.RLIMIT_DATA, "
            f"({int(memory_bytes)},{int(memory_bytes)}))")
    try:
        result = subprocess.run((sys.executable, "-I", "-S", "-c", code),
                                capture_output=True, timeout=2, check=False)
        return result.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False
