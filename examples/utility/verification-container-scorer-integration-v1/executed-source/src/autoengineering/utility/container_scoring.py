"""Candidate fixed container scorer for explicitly admitted confirmation grants.

This profile has no CLI or registry activation. Its runtime and real-data use
still require qualification/admission. It accepts frozen predictions, never
executes a supplied model, and preserves access and charges after uncertainty.
"""

from __future__ import annotations

import hashlib
import math
from pathlib import Path

from autoengineering.campaign.artifacts import confined_file, read_bytes
from autoengineering.campaign.serialization import canonical_json, digest, unique_json
from autoengineering.campaign.store import checked_directory, durable_write, StoreError
from .private_container_runtime import FixedScorerRuntime
from .scoring import PublicScore


class ContainerRMSEScorer:
    """App-owned candidate callback. Construction and recovery do not open labels."""

    def __init__(
        self,
        public_root,
        private_root,
        *,
        labels,
        predictions,
        partition_digest,
        outcome_contract,
        runtime: FixedScorerRuntime,
    ):
        self.public_root = checked_directory(public_root)
        self.private_root = checked_directory(private_root)
        if self.private_root.is_relative_to(self.public_root) or self.public_root.is_relative_to(
            self.private_root
        ):
            raise StoreError("private scoring scope must be separate from the public suite")
        if outcome_contract.name != "rmse" or outcome_contract.direction != "minimize":
            raise ValueError("container vector profile supports minimized RMSE only")
        if labels.size_bytes > 1048576 or predictions.size_bytes > 1048576:
            raise ValueError("container vector inputs exceed the fixed one MiB envelope")
        self.labels, self.predictions = labels, predictions
        self.partition_digest, self.outcome_contract = partition_digest, outcome_contract
        self.runtime = runtime
        self.identity = digest(
            {
                "profile": "private-json-rmse-container-candidate-v1",
                "parent_source": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "labels": labels.sha256,
                "predictions": predictions.sha256,
                "partition": partition_digest,
                "outcome": outcome_contract.digest,
                "runtime": runtime.identity,
            }
        )

    def _scope(self, grant, model):
        if (grant.scorer_digest, grant.partition_digest, grant.outcome_digest) != (
            self.identity,
            self.partition_digest,
            self.outcome_contract.digest,
        ):
            raise StoreError("container scorer grant differs from registration")
        active = next((r for r in grant.resources if r.name == "active_time"), None)
        if (
            active is None
            or active.units != "s"
            or active.enforcement != "reservation"
            or active.limit < 64
        ):
            raise StoreError(
                "container scoring needs 64 reserved seconds for bounded lifecycle work"
            )
        if model.sha256 != grant.model_digest:
            raise StoreError("container scorer model differs from grant")
        return self.private_root / grant.digest

    def _access_binding(self, grant, model, job):
        return {
            "schema": "private-json-rmse-container-access-v1",
            "grant": grant.digest,
            "scorer": self.identity,
            "model": model.sha256,
            "labels_sha256": self.labels.sha256,
            "predictions_sha256": self.predictions.sha256,
            "public_job_sha256": hashlib.sha256(job).hexdigest(),
            "runtime_identity": self.runtime.identity,
        }

    def _score(self, document):
        score = PublicScore.from_dict(document)
        if (score.outcome, score.units) != (
            self.outcome_contract.name,
            self.outcome_contract.units,
        ):
            raise StoreError("container score differs from public outcome semantics")
        return score

    def __call__(self, grant, model):
        root = self._scope(grant, model)
        if root.exists() or root.is_symlink():
            raise StoreError("container scoring attempt already exists; explicit recovery required")
        document = unique_json(
            read_bytes(self.public_root, self.predictions, max_bytes=1048576).decode()
        )
        if not isinstance(document, dict) or set(document) != {
            "model_sha256",
            "partition_digest",
            "selection_digest",
            "prediction",
        }:
            raise StoreError("frozen predictions have invalid schema")
        if (
            document["model_sha256"],
            document["partition_digest"],
            document["selection_digest"],
        ) != (model.sha256, self.partition_digest, grant.selection_digest):
            raise StoreError("frozen predictions differ from selected model or partition")
        predicted = document["prediction"]
        if (
            not isinstance(predicted, list)
            or not predicted
            or any(type(v) not in (int, float) or not math.isfinite(v) for v in predicted)
        ):
            raise StoreError("frozen public predictions must be a nonempty finite numeric vector")
        job = canonical_json(
            {
                "prediction": predicted,
                "outcome": self.outcome_contract.name,
                "units": self.outcome_contract.units,
            }
        ).encode()
        # A changed daemon/image refuses before label reads. No fallback runtime.
        version = self.runtime.preflight()
        root.mkdir(mode=0o700)
        work = root / "workspace"
        work.mkdir(mode=0o700)
        durable_write(work / "job.json", job)
        durable_write(
            root / "binding.json",
            canonical_json(
                {
                    "grant": grant.digest,
                    "scorer": self.identity,
                    "model": model.sha256,
                }
            ).encode(),
        )
        durable_write(
            root / "private-access.json",
            canonical_json(self._access_binding(grant, model, job)).encode(),
        )
        # First private-byte access follows both suite and scorer durable intents.
        labels = read_bytes(self.private_root, self.labels, max_bytes=1048576)
        durable_write(work / "labels.json", labels)
        score = self._score(self.runtime.run(root, api_version=version))
        durable_write(root / "public-score.json", score.to_json().encode())
        return score

    def recover(self, grant, model):
        """Verify public bindings and completed original output without opening labels."""
        root = checked_directory(self._scope(grant, model))
        if unique_json(confined_file(root, "binding.json").read_text()) != {
            "grant": grant.digest,
            "scorer": self.identity,
            "model": model.sha256,
        }:
            raise StoreError("container recovery binding differs")
        work = checked_directory(root / "workspace")
        job = confined_file(work, "job.json").read_bytes()
        access = unique_json(confined_file(root, "private-access.json").read_text())
        if access != self._access_binding(grant, model, job):
            raise StoreError("container recovery access binding differs")
        return self._score(self.runtime.recover(root))
