"""Seal new operating scenarios before selection, then read after the suite barrier.

This trusted preparer creates model inputs, not observed labels. It does not solve
or score the circuit, admit a task, or provide an OS boundary. One durable claim
per suite task prevents a new output scope from obtaining another random draw.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import hmac
import math
from pathlib import Path
import secrets
from typing import Literal, Mapping

from autoengineering.campaign.artifacts import confined_file
from autoengineering.campaign.serialization import Record, canonical_json, digest, unique_json
from autoengineering.campaign.store import checked_directory, durable_write
from autoengineering.utility.confirmation import read_manifest
from autoengineering.utility.contracts import identifier, sha256

AXES = ("ground_voltage", "resistor1_ohm", "resistor2_ohm")
UNITS = {"ground_voltage": "V", "resistor1_ohm": "ohm", "resistor2_ohm": "ohm"}
CLAIMS = "engineering-scenario-preparations"


def source_identity():
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


@dataclass(frozen=True)
class ScenarioPolicy(Record):
    schema: Literal["utility-engineering-generated-scenarios-v1"]
    task_id: str
    bounds: Mapping[str, tuple[float, float]]
    sampler_source_sha256: str
    count: Literal[24] = 24
    seed_bytes: Literal[32] = 32
    algorithm: Literal["hmac-sha256-52bit-v1"] = "hmac-sha256-52bit-v1"
    weights: Literal["uniform"] = "uniform"
    generation_stage: Literal["before_any_suite_selection"] = "before_any_suite_selection"

    def _validate(self):
        identifier(self.task_id)
        sha256(self.sampler_source_sha256)
        if (
            set(self.bounds) != set(AXES)
            or any(a >= b or not math.isfinite(b - a) for a, b in self.bounds.values())
            or any(self.bounds[name][0] <= 0 for name in AXES[1:])
        ):
            raise ValueError("engineering scenario policy requires ordered finite physical bounds")


def derive(seed, policy, suite_digest, generation_digest):
    """Deterministic private replay; never generates replacement randomness."""
    if not isinstance(policy, ScenarioPolicy) or not isinstance(seed, bytes) or len(seed) != 32:
        raise ValueError("engineering scenario sampler needs its exact policy and 32-byte seed")
    sha256(suite_digest)
    sha256(generation_digest)
    result = []
    for index in range(policy.count):
        forcing = {}
        for name in AXES:
            message = canonical_json(
                {
                    "schema": policy.algorithm,
                    "policy": policy.digest,
                    "suite": suite_digest,
                    "generation": generation_digest,
                    "index": index,
                    "axis": name,
                }
            ).encode()
            value = int.from_bytes(hmac.new(seed, message, hashlib.sha256).digest()[:7], "big") >> 4
            fraction = value / (2**52)
            lower, upper = policy.bounds[name]
            forcing[name] = lower + (upper - lower) * fraction
        result.append(
            {
                "scenario_id": f"generated-load-{index + 1:04d}",
                "forcing": forcing,
                "weight": 1.0 / policy.count,
            }
        )
    return tuple(result)


def _save(root, name, value):
    durable_write(root / name, canonical_json(value).encode())


def prepare(store, policy, public_root, private_root, *, expected_suite_digest):
    """Claim once under the suite writer before entropy or private source creation.

    The policy digest must already be the prospective partition identity. The
    completed source digest must enter final task/execution admission before work.
    Any prior suite event refuses generation. The trusted private reader requires
    the later complete selection barrier.
    Output scopes must be empty, separate and outside the public suite tree.
    """
    try:
        public, private = checked_directory(public_root), checked_directory(private_root)
        if (
            not isinstance(policy, ScenarioPolicy)
            or store.spec.digest != expected_suite_digest
            or policy.sampler_source_sha256 != source_identity()
            or public.is_relative_to(private)
            or private.is_relative_to(public)
            or any(public.iterdir())
            or any(private.iterdir())
            or any(
                p.is_relative_to(store.root) or store.root.is_relative_to(p)
                for p in (public, private)
            )
        ):
            raise ValueError("engineering scenario source or output identity differs")
        with store.writer():
            state = store.replay()
            if state["frozen"] is not None or state["events"]:
                raise ValueError(
                    "engineering source must be frozen before any suite selection work"
                )
            generation_digest = digest(
                {
                    "suite": store.spec.digest,
                    "policy": policy.digest,
                    "owner_scope": digest(str(store.root)),
                }
            )
            task = next(t for t in store.spec.tasks if t.task_id == policy.task_id)
            if task.family != "engineering" or task.partition_digest != policy.digest:
                raise ValueError("engineering sampling policy was not frozen in the task")
            claims = store.root / CLAIMS
            if claims.is_symlink():
                raise ValueError("engineering scenario claim scope is a symlink")
            claims.mkdir(mode=0o700, exist_ok=True)
            checked_directory(claims)
            name = policy.task_id + ".json"
            if (claims / name).exists() or (claims / name).is_symlink():
                raise ValueError(
                    "engineering scenario generation already intended; saved-evidence reading only"
                )
            claim = {
                "schema": "utility-engineering-scenario-claim-v1",
                "suite_digest": expected_suite_digest,
                "generation_digest": generation_digest,
                "policy_digest": policy.digest,
                "sampler_source_sha256": policy.sampler_source_sha256,
                "scope_digest": digest({"public": str(public), "private": str(private)}),
                "entropy_draws_reserved": 1,
                "automatic_retries": 0,
                "scientific_starts": 0,
            }
            _save(claims, name, claim)
            _save(public, "preparation-claim.json", claim)
            _save(private, "preparation-claim.json", claim)
            seed = secrets.token_bytes(policy.seed_bytes)
            scenarios = derive(seed, policy, expected_suite_digest, generation_digest)
            private_record = {
                "schema": "utility-engineering-private-scenarios-v1",
                "claim_digest": digest(claim),
                "policy": policy.to_dict(),
                "suite_digest": expected_suite_digest,
                "generation_digest": generation_digest,
                "seed_hex": seed.hex(),
                "scenarios": list(scenarios),
                "units": UNITS,
                "task_admitted": False,
            }
            _save(private, "scenarios.json", private_record)
            result = {
                "schema": "utility-engineering-public-scenarios-v1",
                "claim_digest": digest(claim),
                "policy": policy.to_dict(),
                "suite_digest": expected_suite_digest,
                "generation_digest": generation_digest,
                "seed_commitment": hashlib.sha256(seed).hexdigest(),
                "private_record_digest": digest(private_record),
                "scenario_count": len(scenarios),
                "units": UNITS,
                "outputs_evaluated": False,
                "task_admitted": False,
                "historical_data_independence_attested": False,
                "private_boundary_qualified": False,
            }
            _save(public, "manifest.json", result)
            return result
    except Exception:
        pass
    raise ValueError("engineering scenario preparation failed") from None


def read_public(root, *, expected_manifest_digest):
    """Metadata-only read, without entropy, private source access or solver imports."""
    try:
        root = checked_directory(root)
        content = confined_file(root, "manifest.json").read_bytes()
        if len(content) > 65536 or hashlib.sha256(content).hexdigest() != expected_manifest_digest:
            raise ValueError("engineering public scenario identity differs")
        result = unique_json(content.decode())
        if (
            set(result)
            != {
                "schema",
                "claim_digest",
                "policy",
                "suite_digest",
                "generation_digest",
                "seed_commitment",
                "private_record_digest",
                "scenario_count",
                "units",
                "outputs_evaluated",
                "task_admitted",
                "historical_data_independence_attested",
                "private_boundary_qualified",
            }
            or result["schema"] != "utility-engineering-public-scenarios-v1"
        ):
            raise ValueError("engineering public scenario schema differs")
        policy = ScenarioPolicy.from_dict(result["policy"])
        claim = _read(root, "preparation-claim.json")
        _validate_claim(claim)
        if (
            digest(claim) != result["claim_digest"]
            or claim["policy_digest"] != policy.digest
            or claim["suite_digest"] != result["suite_digest"]
            or claim["generation_digest"] != result["generation_digest"]
            or result["scenario_count"] != 24
            or result["units"] != UNITS
            or any(
                result[name] is not False
                for name in (
                    "outputs_evaluated",
                    "task_admitted",
                    "historical_data_independence_attested",
                    "private_boundary_qualified",
                )
            )
        ):
            raise ValueError("engineering public scenario metadata differs")
        for name in ("seed_commitment", "private_record_digest"):
            sha256(result[name])
        return result
    except Exception:
        pass
    raise ValueError("engineering public scenario verification failed") from None


def _read(root, name, limit=65536):
    path = confined_file(root, name)
    if path.stat().st_size > limit:
        raise ValueError("engineering scenario document exceeds cap")
    return unique_json(path.read_text())


def _verify_private(public, private, policy):
    expected = {
        "schema",
        "claim_digest",
        "policy",
        "suite_digest",
        "generation_digest",
        "seed_hex",
        "scenarios",
        "units",
        "task_admitted",
    }
    if (
        set(private) != expected
        or private["schema"] != "utility-engineering-private-scenarios-v1"
        or private["task_admitted"] is not False
        or private["units"] != UNITS
        or private["policy"] != policy.to_dict()
        or policy.sampler_source_sha256 != source_identity()
    ):
        raise ValueError("engineering private scenario schema or source differs")
    sha256(private["seed_hex"])
    seed = bytes.fromhex(private["seed_hex"])
    rows = derive(seed, policy, private["suite_digest"], private["generation_digest"])
    if list(rows) != private["scenarios"]:
        raise ValueError("engineering scenario source does not reproduce from saved seed")
    for name in ("claim_digest", "suite_digest", "generation_digest"):
        if public[name] != private[name]:
            raise ValueError("engineering scenario source and public identity differ")
    if (
        hashlib.sha256(seed).hexdigest() != public["seed_commitment"]
        or digest(private) != public["private_record_digest"]
    ):
        raise ValueError("engineering scenario private digest or seed commitment differs")
    return rows


def read_private(
    store, public_root, private_root, *, expected_manifest_digest, expected_selection_digest
):
    """Trusted source replay; opens no solver or new entropy source."""
    try:
        public = read_public(public_root, expected_manifest_digest=expected_manifest_digest)
        state = store.replay()
        if (
            public["suite_digest"] != store.spec.digest
            or state["frozen"] is None
            or state["frozen"] != expected_selection_digest
        ):
            raise ValueError(
                "engineering private source requires the complete frozen suite barrier"
            )
        read_manifest(store.root, expected_selection_digest)
        shared = _read(
            checked_directory(store.root / CLAIMS),
            ScenarioPolicy.from_dict(public["policy"]).task_id + ".json",
        )
        if digest(shared) != public["claim_digest"]:
            raise ValueError("engineering private source differs from its original suite claim")
        private = checked_directory(private_root)
        source = _read(private, "scenarios.json")
        claim = _read(private, "preparation-claim.json")
        if digest(claim) != public["claim_digest"]:
            raise ValueError("engineering private claim differs")
        return _verify_private(public, source, ScenarioPolicy.from_dict(public["policy"]))
    except Exception:
        pass
    raise ValueError("engineering private scenario verification failed") from None


def recover_public(store, public_root, private_root, *, expected_claim_digest):
    """Publish only an already committed draw, with no replacement randomness.

    Missing private completion is uncertain and refuses. The suite claim prevents
    regenerating through another pair of output scopes. This is data preparation,
    not confirmation score recovery or independent task admission.
    """
    try:
        public, private = checked_directory(public_root), checked_directory(private_root)
        with store.writer():
            claim = _read(public, "preparation-claim.json")
            if (
                digest(claim) != expected_claim_digest
                or _read(private, "preparation-claim.json") != claim
            ):
                raise ValueError("engineering recovery claim differs")
            data = _read(private, "scenarios.json")
            policy = ScenarioPolicy.from_dict(data["policy"])
            shared = _read(checked_directory(store.root / CLAIMS), policy.task_id + ".json")
            state = store.replay()
            if (
                claim != shared
                or claim["suite_digest"] != store.spec.digest
                or state["frozen"] is not None
                or state["events"]
                or claim["policy_digest"] != policy.digest
                or claim["scope_digest"] != digest({"public": str(public), "private": str(private)})
                or any(e.operation == "confirmation_access" for e in state["events"])
            ):
                raise ValueError("engineering recovery suite, barrier or scope differs")
            result = {
                "schema": "utility-engineering-public-scenarios-v1",
                "claim_digest": expected_claim_digest,
                "policy": policy.to_dict(),
                "suite_digest": store.spec.digest,
                "generation_digest": claim["generation_digest"],
                "seed_commitment": hashlib.sha256(bytes.fromhex(data["seed_hex"])).hexdigest(),
                "private_record_digest": digest(data),
                "scenario_count": policy.count,
                "units": UNITS,
                "outputs_evaluated": False,
                "task_admitted": False,
                "historical_data_independence_attested": False,
                "private_boundary_qualified": False,
            }
            _verify_private(result, data, policy)
            path = public / "manifest.json"
            if path.exists() or path.is_symlink():
                if _read(public, "manifest.json") != result:
                    raise ValueError("engineering source already has conflicting public completion")
            else:
                _save(public, "manifest.json", result)
            return read_public(public, expected_manifest_digest=digest(result))
    except Exception:
        pass
    raise ValueError("engineering scenario recovery failed") from None


def _validate_claim(claim):
    fields = {
        "schema",
        "suite_digest",
        "generation_digest",
        "policy_digest",
        "sampler_source_sha256",
        "scope_digest",
        "entropy_draws_reserved",
        "automatic_retries",
        "scientific_starts",
    }
    if set(claim) != fields or claim["schema"] != "utility-engineering-scenario-claim-v1":
        raise ValueError("engineering scenario claim schema differs")
    for name in (
        "suite_digest",
        "generation_digest",
        "policy_digest",
        "sampler_source_sha256",
        "scope_digest",
    ):
        sha256(claim[name])
    for name, value in (
        ("entropy_draws_reserved", 1),
        ("automatic_retries", 0),
        ("scientific_starts", 0),
    ):
        if type(claim[name]) is not int or claim[name] != value:
            raise ValueError("engineering scenario claim allowance differs")
