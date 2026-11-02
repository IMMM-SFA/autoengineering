"""Trusted development callback for sealed annual wind drivers and fixed layouts.

No CLI registration, private runtime isolation or fixed-total-cost support.
Recovery reads original pinned metadata and never reopens drivers or models.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from importlib.metadata import version
import math
from pathlib import Path
from typing import Literal

from autoengineering.campaign.artifacts import confined_file, put_bytes, read_bytes, reference
from autoengineering.campaign.records import ArtifactRef, ModelSnapshot, PortContract
from autoengineering.campaign.serialization import Record, canonical_json, digest, unique_json
from autoengineering.campaign.store import checked_directory, durable_write
from autoengineering.utility.confirmation import read_selected_state
from autoengineering.utility.contracts import sha256
from autoengineering.utility.outcomes import OutcomeSpec
from autoengineering.utility.scoring import ConfirmationGrant, PublicScore, validate_grant
from examples.utility import wind_annual_source as source
from examples.utility import wind_annual_scoring as kernel
from examples.utility.wind_annual import AnnualWindRun


def source_identity():
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def outcome_contract(policy):
    return OutcomeSpec(
        "engineering-outcome-v1",
        "mean_annual_energy",
        "GWh",
        "maximize",
        "mean",
        digest(
            {"kernel": policy.scorer_source_digest, "aggregation": "equal-year-actual-duration"}
        ),
    )


def model_snapshot(geometry, plan, source_root):
    """Code-only closure: never include private annual payloads in worker sources."""
    names = (
        *kernel.MODEL_FILES,
        "examples/utility/wind_annual_scoring.py",
        "examples/utility/wind_annual_source.py",
        "examples/utility/wind_annual_callback.py",
    )
    refs = tuple(
        reference(Path(source_root), name, media_type="text/plain", producer="annual-wind-model")
        for name in names
    )
    pins = {ref.path: ref.sha256 for ref in refs}
    if (
        digest({name: pins[name] for name in kernel.MODEL_FILES}) != plan.model_digest
        or pins["examples/utility/wind_annual_scoring.py"] != kernel.source_identity()
        or pins["examples/utility/wind_annual_source.py"] != source.source_identity()
        or pins["examples/utility/wind_annual_callback.py"] != source_identity()
    ):
        raise ValueError("annual wind declared sources differ from the registered implementation")
    return ModelSnapshot(
        digest(
            {
                "profile": "utility-wind-annual-model-v1",
                "model": plan.model_digest,
                "geometry": geometry.digest,
                "interpretation": plan.interpretation_digest,
            }
        ),
        {"wind": "annual-hourly-noj-v1"},
        refs,
        digest(
            {
                "py-wake": "2.6.20",
                "lock": hashlib.sha256((Path(source_root) / "pixi.lock").read_bytes()).hexdigest(),
            }
        ),
        (),
        (
            PortContract(
                "mean_annual_energy",
                (),
                "GWh",
                "float",
                (),
                "scalar",
                digest({"grid": "annual-aggregate"}),
                None,
            ),
        ),
    )


@dataclass(frozen=True)
class AnnualWindWork(Record):
    schema: Literal["utility-trusted-wind-annual-work-v1"]
    grant_digest: str
    scorer_digest: str
    source_binding_digest: str
    policy_digest: str
    source_access_digest: str
    kernel_record_digest: str
    score: PublicScore
    run: AnnualWindRun
    attempted_model_starts: int
    completed_model_starts: int
    last_attempt_work_unknown: bool
    task_admitted: Literal[False] = False
    private_boundary_qualified: Literal[False] = False
    os_deadline_qualified: Literal[False] = False
    aggregate_rss_qualified: Literal[False] = False
    automatic_retries: Literal[0] = 0

    def _validate(self):
        for value in (
            self.grant_digest,
            self.scorer_digest,
            self.source_binding_digest,
            self.policy_digest,
            self.source_access_digest,
            self.kernel_record_digest,
        ):
            sha256(value)
        if not 0 <= self.completed_model_starts <= self.attempted_model_starts <= 8:
            raise ValueError("annual wind work counts exceed the bounded profile")


class TrustedAnnualWindScorer:
    def __init__(
        self,
        store,
        binding_artifact,
        public_root,
        private_root,
        source_root,
        work_root,
        *,
        geometry,
        expected_model,
        policy,
    ):
        self.store, self.binding_artifact = store, binding_artifact
        self.public_root, self.private_root = source._roots(store, public_root, private_root)
        self.source_root = Path(source_root)
        self.work_root = checked_directory(work_root)
        if any(
            self.work_root.is_relative_to(p) or p.is_relative_to(self.work_root)
            for p in (store.root, self.public_root, self.private_root)
        ):
            raise ValueError("annual wind callback work must be separate from data and suite")
        self.binding = source.read_binding(store, binding_artifact)
        self.geometry, self.expected_model, self.policy = geometry, expected_model, policy
        self.outcome_contract = outcome_contract(policy)
        self.code_digest = self._code_digest()
        self.identity = source.scorer_identity(self.binding, self.code_digest)
        self._verify_registration()

    def _code_digest(self):
        return digest(
            {
                "schema": "utility-trusted-annual-wind-callback-v1",
                "callback_source": source_identity(),
                "policy": self.policy.digest,
                "geometry": self.geometry.digest,
                "model": self.expected_model.digest,
                "outcome": self.outcome_contract.digest,
            }
        )

    def _verify_registration(self):
        if (
            not isinstance(self.policy, kernel.AnnualWindScorePolicy)
            or self.policy.scorer_source_digest != kernel.source_identity()
            or self.policy.model_digest != kernel.model_identity()
            or self.policy.plan_digest != self.binding.plan.digest
            or self.binding.plan.geometry_digest != self.geometry.digest
            or self.expected_model
            != model_snapshot(self.geometry, self.binding.plan, self.source_root)
            or self.code_digest != self._code_digest()
            or source.read_binding(self.store, self.binding_artifact) != self.binding
            or self.identity != source.scorer_identity(self.binding, self.code_digest)
        ):
            raise ValueError("annual wind callback registration or source changed")

    def _context(self, grant, model):
        self._verify_registration()
        if (
            type(grant) is not ConfirmationGrant
            or grant.scorer_digest != self.identity
            or grant.outcome_digest != self.outcome_contract.digest
            or model.sha256 != grant.model_digest
        ):
            raise ValueError("annual wind callback needs its original registered grant")
        state = self.store.replay()
        selected = validate_grant(self.store, grant, state["frozen"])
        cell = next(c for c in self.store.spec.cells if c.digest == grant.cell_digest)
        if cell.regime != "fixed_evaluations":
            raise ValueError("annual wind callback has no qualified fixed-total-cost boundary")
        bound = read_selected_state(self.store.root, selected.selected_state)
        if bound.model != self.expected_model:
            raise ValueError("annual wind callback selection changed its fixed model")
        self.geometry.validate(bound.configuration)
        caps = {cap.name: cap for cap in grant.resources}
        needed = {
            "wind_model_starts": len(self.binding.plan.sources),
            "private_wind_reads": len(self.binding.payloads),
            "private_wind_bytes": sum(p.size_bytes for p in self.binding.payloads),
        }
        for name, count in needed.items():
            cap = caps.get(name)
            if cap is None or (cap.units, cap.enforcement, cap.limit) != (
                "count",
                "reservation",
                count,
            ):
                raise ValueError("annual wind callback lacks its exact inner-work reservations")
        active = caps.get("active_time")
        if (
            active is None
            or (active.units, active.enforcement) != ("s", "reservation")
            or active.limit <= 0
        ):
            raise ValueError("annual wind callback requires declared active time")
        attempt = "confirmation-" + grant.cell_digest[:48]
        allocation, status = state["attempts"].get(attempt, (None, None))
        if (
            allocation is None
            or allocation.child_digest != grant.digest
            or allocation.resources != grant.resources
            or allocation.phase != "confirmation"
            or attempt not in state["confirmation_accesses"]
        ):
            raise ValueError("annual wind callback needs its original charged access")
        return state, attempt, status, dict(bound.configuration)

    def _validate_work(self, work, grant, configuration):
        if (
            work.grant_digest != grant.digest
            or work.scorer_digest != self.identity
            or work.source_binding_digest != self.binding.digest
            or work.policy_digest != self.policy.digest
            or work.source_access_digest != self._source_access_digest(grant)
            or work.run.plan_digest != self.binding.plan.digest
            or work.run.configuration_digest != digest(configuration)
            or tuple(r.year for r in work.run.results)
            != tuple(s.year for s in self.binding.plan.sources)
        ):
            raise ValueError("annual wind work changed its grant, source or selected layout")
        failed = None
        successes = 0
        for expected, result in zip(self.binding.plan.sources, work.run.results, strict=True):
            if result.source_digest != expected.digest:
                raise ValueError("annual wind work substituted a source")
            if failed is None and result.status == "success":
                successes += 1
            elif failed is None and result.status != "not_attempted":
                failed = result.status
            elif failed is None or result.status != "not_attempted":
                raise ValueError("annual wind work has an invalid failure/start sequence")
        score = PublicScore(
            failed or "success",
            "mean_annual_energy",
            "GWh",
            math.fsum(r.energy_gwh for r in work.run.results) / len(work.run.results)
            if failed is None
            else None,
            True if failed is None else False if failed == "scientific_infeasible" else None,
        )
        if (
            score != work.score
            or work.completed_model_starts != successes
            or work.attempted_model_starts != successes + (failed is not None)
            or work.last_attempt_work_unknown != (failed is not None)
        ):
            raise ValueError("annual wind work score or model-start accounting differs")

    def _source_access_digest(self, grant):
        """Join source-read metadata only; never inspect a private payload."""
        records = {}

        def expect(suffix, value):
            name = f"{source.ACCESSES}/{grant.digest}{suffix}.json"
            path = confined_file(self.store.root, name)
            if path.stat().st_size > 65536:
                raise ValueError("annual wind read record exceeds metadata envelope")
            blob = path.read_bytes()
            if blob != canonical_json(value).encode():
                raise ValueError("annual wind original source-read evidence changed")
            records[name] = hashlib.sha256(blob).hexdigest()

        count = len(self.binding.payloads)
        size = sum(p.size_bytes for p in self.binding.payloads)
        expect(
            "",
            {
                "grant_digest": grant.digest,
                "binding_digest": self.binding.digest,
                "private_reads_reserved": count,
                "private_bytes_reserved": size,
                "automatic_retries": 0,
            },
        )
        for annual, payload in zip(self.binding.plan.sources, self.binding.payloads, strict=True):
            common = {
                "grant_digest": grant.digest,
                "source_digest": annual.digest,
                "payload_digest": payload.sha256,
            }
            expect(
                f"-{annual.year}-start",
                {
                    **common,
                    "status": "started",
                    "private_bytes_reserved": payload.size_bytes,
                    "automatic_retries": 0,
                },
            )
            expect(
                f"-{annual.year}-complete",
                {
                    **common,
                    "status": "verified",
                    "completed_private_reads": 1,
                    "verified_private_bytes": payload.size_bytes,
                },
            )
        expect(
            "-complete",
            {
                "grant_digest": grant.digest,
                "binding_digest": self.binding.digest,
                "completed_private_reads": count,
                "verified_private_bytes": size,
                "automatic_retries": 0,
            },
        )
        return digest(records)

    def __call__(self, grant, model):
        state, attempt, status, configuration = self._context(grant, model)
        if status != "started" or attempt in state["confirmation_scores"]:
            raise ValueError("annual wind callback is not an active scoring attempt")
        if version("py-wake") != "2.6.20":
            raise ValueError("annual wind callback requires its pinned model dependency")
        root = self.work_root / grant.digest
        root.mkdir(mode=0o700)  # Existing or uncertain work always refuses.
        durable_write(
            root / "intent.json",
            canonical_json(
                {
                    "grant_digest": grant.digest,
                    "scorer_digest": self.identity,
                    "automatic_retries": 0,
                }
            ).encode(),
        )
        drivers = source.open_for_confirmation(
            self.store,
            grant,
            self.binding_artifact,
            self.public_root,
            self.private_root,
            scorer_code_digest=self.code_digest,
        )
        source_access_digest = self._source_access_digest(grant)
        scope = root / "kernel"
        scope.mkdir(mode=0o700)
        result = kernel.score_annual(
            configuration,
            self.geometry,
            self.binding.plan,
            drivers,
            scope,
            policy=self.policy,
            execution_digest=grant.digest,
        )
        path = confined_file(root, "kernel/complete.json")
        if path.stat().st_size > 65536:
            raise ValueError("annual wind kernel record exceeds the metadata envelope")
        record = unique_json(path.read_text())
        if (
            record["execution_digest"] != grant.digest
            or record["policy_digest"] != self.policy.digest
            or record["score"] != result.score.to_dict()
            or record["annual_run"] != result.run.to_dict()
            or record["attempted_model_starts"] != result.attempted_model_starts
            or record["completed_model_starts"] != result.completed_model_starts
            or record["last_attempt_work_unknown"] != result.last_attempt_work_unknown
        ):
            raise ValueError("annual wind kernel result differs from its original journal")
        work = AnnualWindWork(
            "utility-trusted-wind-annual-work-v1",
            grant.digest,
            self.identity,
            self.binding.digest,
            self.policy.digest,
            source_access_digest,
            digest(record),
            result.score,
            result.run,
            result.attempted_model_starts,
            result.completed_model_starts,
            result.last_attempt_work_unknown,
        )
        self._validate_work(work, grant, configuration)
        artifact = put_bytes(
            self.store.root,
            work.to_json().encode(),
            name="annual-wind-work.json",
            media_type="application/json",
            producer="annual-wind-confirmation-work",
        )
        durable_write(
            root / "complete.json",
            canonical_json(
                {
                    "schema": "utility-trusted-wind-annual-completion-v1",
                    "scorer_digest": self.identity,
                    "work_artifact": artifact.to_dict(),
                }
            ).encode(),
        )
        return work.score

    def _completed(self, grant, model):
        _, _, _, configuration = self._context(grant, model)
        path = confined_file(self.work_root, f"{grant.digest}/complete.json")
        if path.stat().st_size > 65536:
            raise ValueError("annual wind callback anchor exceeds the metadata envelope")
        anchor = unique_json(path.read_text())
        if (
            set(anchor) != {"schema", "scorer_digest", "work_artifact"}
            or anchor["schema"] != "utility-trusted-wind-annual-completion-v1"
            or anchor["scorer_digest"] != self.identity
        ):
            raise ValueError("annual wind callback completion changed")
        artifact = ArtifactRef.from_dict(anchor["work_artifact"])
        if (
            artifact.path != f"artifacts/{artifact.sha256}/annual-wind-work.json"
            or artifact.media_type != "application/json"
            or artifact.producer != "annual-wind-confirmation-work"
        ):
            raise ValueError("annual wind work artifact role differs")
        work = AnnualWindWork.from_json(
            read_bytes(self.store.root, artifact, max_bytes=65536).decode()
        )
        self._validate_work(work, grant, configuration)
        return artifact, work

    def recover(self, grant, model):
        return self._completed(grant, model)[1].score

    def public_work(self, grant, model):
        return self._completed(grant, model)[0]
