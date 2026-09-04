"""Deterministic baseline optimization policies.

The ledger is the durable sequence state.  These stateless policies derive
every action ID, seed, and sampling offset from the immutable study and the
ledger supplied to each call, so a resumed process can replay a suggestion
without restoring mutable optimizer state.
"""

# Random draws use explicit StudySpec seeds through SeedSequence.  # waterology: allow-unseeded

from __future__ import annotations

from collections.abc import Mapping
import math
import re
from typing import Protocol, runtime_checkable

import numpy as np
from scipy.stats import qmc

from .ledger import ObservationLedgerReader
from .records import (
    BackendDiagnostics,
    EvaluationAction,
    EvaluationScope,
    EvaluationStatus,
    JSONValue,
    Recommendation,
    Scalar,
)
from .space import CategoricalParameter, ContinuousParameter, IntegerParameter, SearchSpace
from .spec import StudySpec


class SearchSpaceExhausted(RuntimeError):
    """Raised when a policy cannot produce the requested distinct configurations."""


@runtime_checkable
class OptimizerBackend(Protocol):
    """Public protocol shared by baseline and model-based optimization policies."""

    name: str
    spec: StudySpec
    space: SearchSpace

    def suggest(self, ledger: ObservationLedgerReader, n: int = 1) -> tuple[EvaluationAction, ...]:
        """Return valid, distinct system actions or raise ``SearchSpaceExhausted``."""

    def recommend(self, ledger: ObservationLedgerReader) -> Recommendation:
        """Return the best feasible successful observation in ``ledger``."""

    def diagnostics(self, ledger: ObservationLedgerReader) -> BackendDiagnostics:
        """Return truthful policy diagnostics for ``ledger``."""

    def identity_dict(self) -> dict[str, JSONValue]:
        """Return stable constructor identity without fitted or diagnostic state."""

    def state_dict(self) -> dict[str, JSONValue]:
        """Return canonical JSON-compatible local policy state."""


_ACTION_ID = re.compile(r"^eval-([0-9]+)$")
_RETRY_LIMIT = 1024
_FINITE_ENUMERATION_LIMIT = 100_000
_SOBOL_RETRIES_PER_CANDIDATE = 64


def _canonical_config(config: Mapping[str, Scalar]) -> tuple[tuple[str, str, Scalar], ...]:
    """Return a typed key that does not conflate booleans and integers."""
    return tuple(sorted((name, type(value).__qualname__, value) for name, value in config.items()))


class _BaselineBackend:
    """Shared validation, recommendation, and provenance behavior for baselines."""

    name: str

    def __init__(self, spec: StudySpec, space: SearchSpace) -> None:
        if not isinstance(spec, StudySpec):
            raise TypeError("spec must be a StudySpec")
        if not isinstance(space, SearchSpace):
            raise TypeError("space must be a SearchSpace")
        self.spec = spec
        self.space = space

    def recommend(self, ledger: ObservationLedgerReader) -> Recommendation:
        """Rank successful feasible observations by objective, cost, then action ID."""
        candidates: list[tuple[float, float, str, EvaluationAction, Mapping[str, float]]] = []
        for action, result in ledger.entries():
            if result.status is not EvaluationStatus.SUCCESS:
                continue
            required_outcomes = (self.spec.objective.outcome,) + tuple(
                constraint.outcome for constraint in self.spec.constraints
            )
            if any(outcome not in result.outcomes for outcome in required_outcomes):
                continue
            if not all(
                result.outcomes[constraint.outcome] >= constraint.threshold
                if constraint.operator == ">="
                else result.outcomes[constraint.outcome] <= constraint.threshold
                for constraint in self.spec.constraints
            ):
                continue
            objective = result.outcomes[self.spec.objective.outcome]
            ranking_objective = (
                -objective if self.spec.objective.direction == "maximize" else objective
            )
            candidates.append((ranking_objective, result.cost, action.id, action, result.outcomes))
        if not candidates:
            return Recommendation(
                action_id=None,
                config={},
                outcomes={},
                feasible=False,
                message="no feasible successful observation with all required outcomes",
            )
        _, _, _, action, outcomes = min(candidates, key=lambda candidate: candidate[:3])
        return Recommendation(
            action_id=action.id,
            config=action.config,
            outcomes=outcomes,
            feasible=True,
            message="best feasible observed configuration",
        )

    def diagnostics(self, ledger: ObservationLedgerReader) -> BackendDiagnostics:
        """Report baseline sampling facts without claiming a fitted surrogate."""
        entries = ledger.entries()
        return BackendDiagnostics(
            backend=self.name,
            fit_state="stateless_baseline",
            fallback_reasons=("baseline policy does not fit a surrogate",),
            details={
                "ledger_entries": len(entries),
                "successful_entries": sum(
                    result.status is EvaluationStatus.SUCCESS for _, result in entries
                ),
                "sequence_state": "derived_from_ledger",
            },
        )

    def identity_dict(self) -> dict[str, JSONValue]:
        """Return the policy choices that must match across process resumes."""
        return {
            "schema_version": "1.0",
            "name": self.name,
            "constructor": {
                "retry_limit": _RETRY_LIMIT,
                "finite_enumeration_limit": _FINITE_ENUMERATION_LIMIT,
            },
        }

    def state_dict(self) -> dict[str, JSONValue]:
        """Return JSON data for a policy whose sequence state lives in the ledger."""
        return {
            "name": self.name,
            "study_seed": self.spec.seed,
            "retry_limit": _RETRY_LIMIT,
            "finite_enumeration_limit": _FINITE_ENUMERATION_LIMIT,
            "sequence_state": "derived_from_ledger",
        }

    def finite_space_exhausted(self, ledger: ObservationLedgerReader) -> bool:
        """Inspect finite enumeration without fitting or advancing a policy sequence."""
        finite_configs = self._finite_configs()
        if finite_configs is None:
            return False
        _, observed = self._next_index_and_observed(ledger)
        return all(_canonical_config(config) in observed for config in finite_configs)

    def _next_index_and_observed(
        self, ledger: ObservationLedgerReader
    ) -> tuple[int, set[tuple[tuple[str, str, Scalar], ...]]]:
        entries = ledger.entries()
        for action, _ in entries:
            _parse_action_index(action.id)
            if action.scope is not EvaluationScope.SYSTEM:
                raise ValueError(f"ledger action must have system scope: {action.id!r}")
            try:
                self.space.encode(action.config)
            except (TypeError, ValueError) as error:
                raise ValueError(
                    f"ledger action has invalid search-space config: {action.id!r}: {error}"
                ) from error
        ids = {action.id for action, _ in entries}
        indices = [_parse_action_index(action_id) for action_id in ids]
        next_index = max(indices, default=-1) + 1
        while f"eval-{next_index:06d}" in ids:
            next_index += 1
        observed = {_canonical_config(action.config) for action, _ in entries}
        return next_index, observed

    def _action(self, index: int, config: Mapping[str, Scalar]) -> EvaluationAction:
        seed = int(np.random.SeedSequence([self.spec.seed, index]).generate_state(1)[0])
        return EvaluationAction.system(
            f"eval-{index:06d}",
            config,
            seed=seed,
            suggested_by=self.name,
        )

    def _finite_configs(self) -> tuple[dict[str, Scalar], ...] | None:
        """Enumerate only safely small finite conditional spaces in declaration order."""
        cardinality = self._finite_cardinality(_FINITE_ENUMERATION_LIMIT)
        if cardinality is None or cardinality > _FINITE_ENUMERATION_LIMIT:
            return None
        configs: list[dict[str, Scalar]] = []

        def visit(parameter_index: int, config: dict[str, Scalar]) -> bool:
            if parameter_index == len(self.space.parameters):
                configs.append(dict(config))
                return True
            parameter = self.space.parameters[parameter_index]
            if isinstance(parameter, CategoricalParameter):
                for category in parameter.categories:
                    config[parameter.name] = category
                    if not visit(parameter_index + 1, config):
                        return False
                del config[parameter.name]
                return True
            active = self.space._is_active(parameter, config)
            if not active:
                return visit(parameter_index + 1, config)
            if isinstance(parameter, ContinuousParameter):
                return False
            for value in range(parameter.lower, parameter.upper + 1):
                config[parameter.name] = value
                if not visit(parameter_index + 1, config):
                    return False
            del config[parameter.name]
            return True

        return tuple(configs) if visit(0, {}) else None

    def _finite_cardinality(self, limit: int) -> int | None:
        """Return a finite cardinality capped above ``limit``, or ``None`` for a continuum."""

        def capped_product(left: int, right: int) -> int:
            if left == 0 or right == 0:
                return 0
            if left > limit // right:
                return limit + 1
            return left * right

        def visit(parameter_index: int, config: dict[str, Scalar]) -> int | None:
            if parameter_index == len(self.space.parameters):
                return 1
            parameter = self.space.parameters[parameter_index]
            if isinstance(parameter, CategoricalParameter):
                total = 0
                for category in parameter.categories:
                    config[parameter.name] = category
                    child = visit(parameter_index + 1, config)
                    if child is None:
                        return None
                    total = min(limit + 1, total + child)
                del config[parameter.name]
                return total
            if not self.space._is_active(parameter, config):
                return visit(parameter_index + 1, config)
            if isinstance(parameter, ContinuousParameter):
                return None
            child = visit(parameter_index + 1, config)
            if child is None:
                return None
            return capped_product(parameter.upper - parameter.lower + 1, child)

        return visit(0, {})

    def _validate_n(self, n: int) -> None:
        if isinstance(n, bool) or not isinstance(n, int) or n <= 0:
            raise ValueError("n must be a positive integer")


class RandomBackend(_BaselineBackend):
    """Independent deterministic NumPy random sampling over a typed search space."""

    name = "random"

    def suggest(self, ledger: ObservationLedgerReader, n: int = 1) -> tuple[EvaluationAction, ...]:
        self._validate_n(n)
        next_index, observed = self._next_index_and_observed(ledger)
        finite_configs = self._finite_configs()
        if finite_configs is not None:
            available = [
                config for config in finite_configs if _canonical_config(config) not in observed
            ]
            if len(available) < n:
                raise SearchSpaceExhausted("finite search space cannot supply the requested batch")
            actions: list[EvaluationAction] = []
            for offset in range(n):
                index = next_index + offset
                generator = np.random.default_rng(np.random.SeedSequence([self.spec.seed, index]))
                selected = available.pop(int(generator.integers(len(available))))
                actions.append(self._action(index, selected))
            return tuple(actions)

        selected_keys = set(observed)
        actions = []
        for offset in range(n):
            index = next_index + offset
            generator = np.random.default_rng(np.random.SeedSequence([self.spec.seed, index]))
            for _ in range(_RETRY_LIMIT):
                config = self._random_config(generator)
                key = _canonical_config(config)
                if key not in selected_keys:
                    selected_keys.add(key)
                    actions.append(self._action(index, config))
                    break
            else:
                raise SearchSpaceExhausted(
                    "sampling retry limit reached without a new configuration"
                )
        return tuple(actions)

    def _random_config(self, generator: np.random.Generator) -> dict[str, Scalar]:
        config: dict[str, Scalar] = {}
        for parameter in self.space.parameters:
            if isinstance(parameter, CategoricalParameter):
                config[parameter.name] = parameter.categories[
                    int(generator.integers(0, len(parameter.categories)))
                ]
            elif self.space._is_active(parameter, config):
                if isinstance(parameter, IntegerParameter):
                    config[parameter.name] = int(
                        generator.integers(parameter.lower, parameter.upper + 1)
                    )
                elif parameter.scale == "linear":
                    config[parameter.name] = float(
                        generator.uniform(parameter.lower, parameter.upper)
                    )
                else:
                    config[parameter.name] = float(
                        math.exp(
                            generator.uniform(math.log(parameter.lower), math.log(parameter.upper))
                        )
                    )
        self.space.encode(config)
        return config


class SobolBackend(_BaselineBackend):
    """A randomized, scrambled SciPy Sobol baseline projected onto valid conditions."""

    name = "sobol"

    def identity_dict(self) -> dict[str, JSONValue]:
        """Include the bounded scan behavior in durable constructor identity."""
        identity = super().identity_dict()
        constructor = dict(identity["constructor"])
        constructor["scan_retries_per_candidate"] = _SOBOL_RETRIES_PER_CANDIDATE
        identity["constructor"] = constructor
        return identity

    def state_dict(self) -> dict[str, JSONValue]:
        """Include the bounded Sobol scan choice needed for policy replay."""
        state = super().state_dict()
        state["scan_retries_per_candidate"] = _SOBOL_RETRIES_PER_CANDIDATE
        return state

    def suggest(self, ledger: ObservationLedgerReader, n: int = 1) -> tuple[EvaluationAction, ...]:
        self._validate_n(n)
        next_index, observed = self._next_index_and_observed(ledger)
        finite_configs = self._finite_configs()
        if finite_configs is not None:
            available = [
                config for config in finite_configs if _canonical_config(config) not in observed
            ]
            if len(available) < n:
                raise SearchSpaceExhausted("finite search space cannot supply the requested batch")

        selected_keys = set(observed)
        selected_configs: list[dict[str, Scalar]] = []
        sampler = qmc.Sobol(d=self.space.encoded_dimension, scramble=True, seed=self.spec.seed)
        if next_index:
            sampler.fast_forward(next_index)
        chunk_size = _power_of_two_at_least(n)
        scan_limit = chunk_size * _SOBOL_RETRIES_PER_CANDIDATE
        scanned = 0
        while scanned < scan_limit and len(selected_configs) < n:
            for point in sampler.random(chunk_size):
                config = self._decode_projected(point)
                key = _canonical_config(config)
                if key in selected_keys:
                    continue
                selected_keys.add(key)
                selected_configs.append(config)
                if len(selected_configs) == n:
                    break
            scanned += chunk_size

        if len(selected_configs) < n and finite_configs is not None:
            for config in finite_configs:
                key = _canonical_config(config)
                if key not in selected_keys:
                    selected_keys.add(key)
                    selected_configs.append(config)
                    if len(selected_configs) == n:
                        break
        if len(selected_configs) < n:
            raise SearchSpaceExhausted("sampling retry limit reached without a new configuration")
        return tuple(
            self._action(next_index + offset, config)
            for offset, config in enumerate(selected_configs)
        )

    def _decode_projected(self, point: np.ndarray) -> dict[str, Scalar]:
        """Force conditional value/mask pairs to the manifold before decoding."""
        encoded: list[float] = []
        config: dict[str, Scalar] = {}
        point_index = 0
        for parameter in self.space.parameters:
            if isinstance(parameter, CategoricalParameter):
                normalized = float(point[point_index])
                point_index += 1
                encoded.append(normalized)
                config[parameter.name] = self.space._decode_category(parameter, normalized)
                continue
            normalized = float(point[point_index])
            point_index += 1
            active = self.space._is_active(parameter, config)
            if parameter.active_when:
                point_index += 1
                encoded.extend((normalized if active else 0.5, 1.0 if active else 0.0))
            else:
                encoded.append(normalized)
            if active:
                config[parameter.name] = self.space._denormalize(parameter, normalized)
        return self.space.decode(tuple(encoded))


def _power_of_two_at_least(value: int) -> int:
    """Return the smallest positive power-of-two Sobol block containing ``value``."""
    return 1 << (value - 1).bit_length()


def _parse_action_index(action_id: str) -> int:
    """Parse an ASCII decimal action ID and reject noncanonical zero padding."""
    match = _ACTION_ID.fullmatch(action_id)
    if match is None:
        raise ValueError(f"ledger action has noncanonical action ID: {action_id!r}")
    index = int(match.group(1))
    if f"eval-{index:06d}" != action_id:
        raise ValueError(f"ledger action has noncanonical action ID: {action_id!r}")
    return index
