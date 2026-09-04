"""Cost-aware partial-observability optimization over a function network."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
import math
from pathlib import Path
from types import MappingProxyType
import time
import warnings

import numpy as np
from scipy.stats import qmc
import torch

from autoengineering.system.graph import System

from .backend import (
    MarginalValueExhausted,
    SearchSpaceExhausted,
    SobolBackend,
    _BaselineBackend,
    _canonical_config,
    _parse_action_index,
)
from .full_network_backend import FullNetworkBayesBackend, _PreparedComponent
from .function_network import (
    FunctionComponentSpec,
    FunctionNetworkSpec,
    reduce_scalar,
    scalar_observation_name,
    validate_local_parameter_values,
)
from .function_network_evaluator import (
    ComponentTrainingRow,
    FunctionNetworkArtifactError,
    read_verified_npz,
    reconstruct_component_training_tables,
)
from .ledger import ObservationLedgerReader
from .records import (
    BackendDiagnostics,
    EvaluationAction,
    EvaluationResult,
    EvaluationScope,
    EvaluationStatus,
    JSONValue,
    Scalar,
)
from .space import SearchSpace
from .spec import StudySpec


@dataclass(frozen=True)
class PartialActionCandidate:
    """One replayable action candidate with a conservative cost estimate."""

    scope: EvaluationScope
    config: Mapping[str, Scalar]
    estimated_cost: float
    component: str | None = None
    parent_artifact_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "scope", EvaluationScope(self.scope))
        object.__setattr__(self, "config", MappingProxyType(dict(self.config)))
        if self.scope is EvaluationScope.SYSTEM:
            if self.component is not None or self.parent_artifact_id is not None:
                raise ValueError("system candidates cannot name a component or parent")
        elif not self.component:
            raise ValueError("component candidates must name a component")
        if (
            isinstance(self.estimated_cost, bool)
            or not isinstance(self.estimated_cost, (int, float))
            or not math.isfinite(self.estimated_cost)
            or self.estimated_cost < 0
        ):
            raise ValueError("candidate estimated_cost must be finite and nonnegative")
        object.__setattr__(self, "estimated_cost", float(self.estimated_cost))

    @property
    def key(self) -> tuple[object, ...]:
        return (
            self.scope.value,
            self.component or "",
            self.parent_artifact_id or "",
            _canonical_config(self.config),
        )


@dataclass(frozen=True)
class PartialCandidatePools:
    """Deterministic complete-decision and affordable action pools."""

    decisions: tuple[Mapping[str, Scalar], ...]
    system: tuple[PartialActionCandidate, ...]
    component: tuple[PartialActionCandidate, ...]


@dataclass(frozen=True)
class _ScoredCandidate:
    candidate: PartialActionCandidate
    value: float
    raw_value: float
    mcse: float
    score: float
    seeds: tuple[int, ...]


class PartialNetworkBayesBackend(FullNetworkBayesBackend):
    """Fit mixed-scope component GPs and choose system or component actions."""

    name = "function_network_partial"

    def __init__(
        self,
        spec: StudySpec,
        space: SearchSpace,
        network: FunctionNetworkSpec,
        system: System,
        *,
        min_initial: int = 4,
        min_component_observations: int = 3,
        candidate_pool_size: int = 64,
        decision_pool_size: int = 32,
        posterior_samples: int = 128,
        fantasy_samples: int = 16,
        fit_retry_limit: int = 2,
        max_component_streak: int = 3,
        minimum_value_per_cost: float = 0.0,
        cost_quantile: float = 0.9,
    ) -> None:
        for name, value, minimum in (
            ("min_component_observations", min_component_observations, 2),
            ("decision_pool_size", decision_pool_size, 2),
            ("fantasy_samples", fantasy_samples, 2),
            ("max_component_streak", max_component_streak, 1),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
                raise ValueError(f"{name} must be an integer >= {minimum}")
        if (
            isinstance(minimum_value_per_cost, bool)
            or not isinstance(minimum_value_per_cost, (int, float))
            or not math.isfinite(minimum_value_per_cost)
            or minimum_value_per_cost < 0
        ):
            raise ValueError("minimum_value_per_cost must be finite and nonnegative")
        if (
            isinstance(cost_quantile, bool)
            or not isinstance(cost_quantile, (int, float))
            or not math.isfinite(cost_quantile)
            or not 0 < cost_quantile <= 1
        ):
            raise ValueError("cost_quantile must be in (0, 1]")
        self.min_component_observations = min_component_observations
        self.decision_pool_size = decision_pool_size
        self.fantasy_sample_count = fantasy_samples
        self.max_component_streak = max_component_streak
        self.minimum_value_per_cost = float(minimum_value_per_cost)
        self.cost_quantile = float(cost_quantile)
        super().__init__(
            spec,
            space,
            network,
            system,
            min_initial=min_initial,
            candidate_pool_size=candidate_pool_size,
            posterior_samples=posterior_samples,
            fit_retry_limit=fit_retry_limit,
        )

    def _validate_observability_contract(self, network: FunctionNetworkSpec) -> None:
        if EvaluationScope.COMPONENT not in network.evaluation_scopes:
            raise ValueError("partial backend requires component scope in the function network")
        eligible = set(self._eligible_component_names(network))
        missing = []
        for component in network.components:
            for output in component.scalar_outputs:
                if EvaluationScope.SYSTEM in output.observed_in:
                    continue
                if (
                    component.component not in eligible
                    or EvaluationScope.COMPONENT not in output.observed_in
                ):
                    missing.append(f"{component.component}.{output.name}")
        if missing:
            raise ValueError(f"partial backend has unobservable scalar outputs: {missing}")
        terminal = (network.objective, *network.constraints)
        hidden_terminal = [
            item.outcome
            for item in terminal
            if EvaluationScope.SYSTEM
            not in next(
                output.observed_in
                for output in network.component_map[item.component].scalar_outputs
                if output.name == item.scalar_output
            )
        ]
        if hidden_terminal:
            raise ValueError(
                f"partial backend requires terminal outcomes at system scope: {hidden_terminal}"
            )
        nonpositive = [
            name
            for name in eligible
            if network.component_map[name].expected_cost <= 0
        ]
        if nonpositive or sum(component.expected_cost for component in network.components) <= 0:
            raise ValueError(
                "partial backend requires positive declared costs for system and eligible "
                f"component actions: {nonpositive}"
            )

    @staticmethod
    def _eligible_component_names(network: FunctionNetworkSpec) -> tuple[str, ...]:
        incoming = {coupling.target_component for coupling in network.couplings}
        return tuple(
            component.component
            for component in network.components
            if component.component in incoming
            and EvaluationScope.COMPONENT in component.evaluation_scopes
            and any(
                EvaluationScope.COMPONENT in output.observed_in
                for output in component.scalar_outputs
            )
        )

    def _validate_training_entries(self, entries) -> None:
        self.validate_entries(tuple(entries))

    def _select_component_training_rows(
        self,
        component_name: str,
        tables: Mapping[str, tuple[ComponentTrainingRow, ...]],
    ) -> tuple[ComponentTrainingRow, ...]:
        return self._aggregate_duplicate_rows(tables[component_name])

    def _validate_output_training_rows(
        self,
        component: FunctionComponentSpec,
        output_name: str,
        rows: tuple[ComponentTrainingRow, ...],
    ) -> None:
        if component.parameters or component.inputs:
            if len(rows) < self.min_component_observations:
                raise ValueError(
                    f"component {component.component!r} output {output_name!r} requires "
                    f"{self.min_component_observations} distinct observations"
                )

    @staticmethod
    def _aggregate_duplicate_rows(
        rows: tuple[ComponentTrainingRow, ...],
    ) -> tuple[ComponentTrainingRow, ...]:
        groups: dict[tuple[tuple[str, str, Scalar], ...], list[ComponentTrainingRow]] = {}
        for row in rows:
            groups.setdefault(_canonical_config(row.inputs), []).append(row)
        aggregated = []
        for members in groups.values():
            first = members[0]
            output_names = tuple(
                dict.fromkeys(name for row in members for name in row.outputs)
            )
            outputs = {
                name: float(np.mean([row.outputs[name] for row in members if name in row.outputs]))
                for name in output_names
            }
            standard_errors = {}
            for name in output_names:
                errors = [
                    row.standard_errors[name]
                    for row in members
                    if name in row.standard_errors
                ]
                observed = sum(name in row.outputs for row in members)
                if errors and len(errors) == observed:
                    standard_errors[name] = math.sqrt(sum(value**2 for value in errors)) / observed
            artifact_ids = tuple(
                dict.fromkeys(artifact_id for row in members for artifact_id in row.artifact_ids)
            )
            hashes = {
                artifact_id: row.artifact_sha256[artifact_id]
                for row in members
                for artifact_id in row.artifact_ids
            }
            aggregated.append(
                replace(
                    first,
                    outputs=outputs,
                    standard_errors=standard_errors,
                    artifact_ids=artifact_ids,
                    artifact_sha256=hashes,
                    cost=float(np.mean([row.cost for row in members])),
                )
            )
        return tuple(aggregated)

    def validate_entries(
        self, entries: tuple[tuple[EvaluationAction, EvaluationResult], ...]
    ) -> None:
        artifacts: dict[str, tuple[EvaluationAction, EvaluationResult, str, str]] = {}
        previous_index = -1
        for action, result in entries:
            index = _parse_action_index(action.id)
            if index <= previous_index:
                raise ValueError("mixed-scope action IDs must increase in ledger order")
            previous_index = index
            if action.id != result.action_id:
                raise ValueError("ledger action and result IDs must match")
            self._validate_scoped_action(action, artifacts)
            for artifact_id, path in result.artifacts.items():
                if artifact_id in artifacts:
                    raise FunctionNetworkArtifactError(f"duplicate artifact ID: {artifact_id!r}")
                artifacts[artifact_id] = (
                    action,
                    result,
                    path,
                    result.artifact_sha256[artifact_id],
                )

    def validate_action(
        self,
        action: EvaluationAction,
        entries: tuple[tuple[EvaluationAction, EvaluationResult], ...],
    ) -> None:
        self.validate_entries(entries)
        artifacts = self._artifact_records(entries)
        self._validate_scoped_action(action, artifacts)
        next_index = max((_parse_action_index(item.id) for item, _ in entries), default=-1) + 1
        if _parse_action_index(action.id) != next_index:
            raise ValueError("proposed action ID must be the next mixed-scope sequence ID")

    def _validate_scoped_action(self, action, artifacts) -> None:
        if action.scope is EvaluationScope.SYSTEM:
            if action.parent_artifact_ids:
                raise ValueError("system actions must not declare parent artifacts")
            self.space.encode(action.config)
            return
        component = self.network.component_map.get(action.component or "")
        if component is None:
            raise ValueError(f"unknown component action: {action.component!r}")
        if component.component not in self._eligible_component_names(self.network):
            raise ValueError(f"component {component.component!r} is not eligible for partial action")
        prefix = f"{component.component}."
        if any(not name.startswith(prefix) for name in action.config):
            raise ValueError("component action contains a foreign qualified parameter")
        local = {name.removeprefix(prefix): value for name, value in action.config.items()}
        validate_local_parameter_values(component, local)
        if len(action.parent_artifact_ids) != 1:
            raise ValueError("component action requires exactly one parent system artifact")
        parent_id = action.parent_artifact_ids[0]
        record = artifacts.get(parent_id)
        if record is None:
            raise FunctionNetworkArtifactError(
                f"parent artifact {parent_id!r} is unknown or from the future"
            )
        parent_action, parent_result, path, digest = record
        if (
            parent_action.scope is not EvaluationScope.SYSTEM
            or parent_result.status is not EvaluationStatus.SUCCESS
        ):
            raise FunctionNetworkArtifactError(
                f"parent artifact {parent_id!r} is not from an earlier successful system action"
            )
        self._validate_parent_inputs(component.component, Path(path), digest, base=None)

    @staticmethod
    def _artifact_records(entries):
        records = {}
        for action, result in entries:
            for artifact_id, path in result.artifacts.items():
                records[artifact_id] = (
                    action,
                    result,
                    path,
                    result.artifact_sha256[artifact_id],
                )
        return records

    def _validate_parent_inputs(
        self,
        component_name: str,
        path: Path,
        digest: str,
        *,
        base: Path | None,
    ) -> None:
        if not path.is_absolute():
            if base is None:
                raise FunctionNetworkArtifactError(
                    "relative parent artifacts require a ledger directory"
                )
            path = base / path
        arrays = read_verified_npz(path, digest)
        required = {
            f"{coupling.source_component}.{coupling.source_port}"
            for coupling in self.network.couplings
            if coupling.target_component == component_name
        }
        missing = sorted(required - set(arrays))
        if missing:
            raise FunctionNetworkArtifactError(
                f"parent artifact lacks direct upstream ports for {component_name!r}: {missing}"
            )

    def estimated_action_cost(
        self,
        action: EvaluationAction,
        entries: tuple[tuple[EvaluationAction, EvaluationResult], ...],
    ) -> float:
        if action.scope is EvaluationScope.SYSTEM:
            declared = sum(component.expected_cost for component in self.network.components)
            observed = [
                result.cost
                for prior, result in entries
                if prior.scope is EvaluationScope.SYSTEM
                and result.status is EvaluationStatus.SUCCESS
                and result.cost > 0
            ]
        else:
            component = self.network.component_map.get(action.component or "")
            if component is None:
                raise ValueError(f"unknown component action: {action.component!r}")
            declared = component.expected_cost
            observed = [
                result.cost
                for prior, result in entries
                if prior.scope is EvaluationScope.COMPONENT
                and prior.component == component.component
                and result.status is EvaluationStatus.SUCCESS
                and result.cost > 0
            ]
        empirical = (
            0.0
            if not observed
            else float(np.quantile(observed, self.cost_quantile, method="linear"))
        )
        return max(float(declared), empirical)

    def minimum_action_cost(
        self, entries: tuple[tuple[EvaluationAction, EvaluationResult], ...]
    ) -> float:
        system = EvaluationAction.system("eval-000000", {})
        costs = [self.estimated_action_cost(system, entries)]
        if any(
            action.scope is EvaluationScope.SYSTEM
            and result.status is EvaluationStatus.SUCCESS
            and result.artifacts
            for action, result in entries
        ):
            for component_name in self._eligible_component_names(self.network):
                action = EvaluationAction.component(
                    "eval-000000", component_name, {}, parent_artifact_ids=("placeholder",)
                )
                costs.append(self.estimated_action_cost(action, entries))
        return min(costs)

    def recommend(self, ledger: ObservationLedgerReader):
        self.validate_entries(ledger.entries())
        return _BaselineBackend.recommend(self, ledger)

    def _suggest(
        self, ledger: ObservationLedgerReader, n: int
    ) -> tuple[EvaluationAction, ...]:
        if n != 1:
            raise ValueError("partial function-network optimization is sequential")
        started = time.perf_counter()
        entries = ledger.entries()
        self.validate_entries(entries)
        fingerprint = self._fingerprint(entries)
        pools = self._candidate_pools(ledger)
        next_index = max((_parse_action_index(action.id) for action, _ in entries), default=-1) + 1
        successful_system = self._count_initial_observations(entries)
        if successful_system < self.min_initial:
            return self._warm_system_action(
                pools,
                next_index,
                fingerprint,
                started,
                entries,
                "cold_start_insufficient_system_observations",
            )

        tables = reconstruct_component_training_tables(self.network, self.system, ledger)
        deficient = self._deficient_components(tables)
        if deficient:
            candidates = tuple(
                candidate
                for candidate in pools.component
                if candidate.component in deficient
            )
            if not candidates:
                return self._warm_system_action(
                    pools,
                    next_index,
                    fingerprint,
                    started,
                    entries,
                    "component_models_not_ready_and_no_component_action",
                )
            selected = min(candidates, key=lambda item: (item.estimated_cost, item.key))
            return self._warm_component_action(
                selected,
                next_index,
                fingerprint,
                started,
                entries,
                deficient,
            )

        captured: list[warnings.WarningMessage] = []
        try:
            with warnings.catch_warnings(record=True) as captured:
                warnings.simplefilter("always")
                prepared = self._fit_components(tables, fingerprint)
        except FunctionNetworkArtifactError:
            raise
        except Exception as error:
            return self._warm_system_action(
                pools,
                next_index,
                fingerprint,
                started,
                entries,
                f"component_fit_failure: {type(error).__name__}: {error}",
            )
        warning_text = self._warning_text(captured)
        if self._has_fatal_warning(captured):
            return self._warm_system_action(
                pools,
                next_index,
                fingerprint,
                started,
                entries,
                "component_fit_warning_indicates_failure",
                warnings_=warning_text,
            )

        recommendation = self.recommend(ledger)
        if not recommendation.feasible:
            return self._warm_system_action(
                pools,
                next_index,
                fingerprint,
                started,
                entries,
                "no_observed_feasible_system_incumbent",
                warnings_=warning_text,
            )
        best = recommendation.outcomes[self.spec.objective.outcome]
        force_system = self._component_streak(entries) >= self.max_component_streak
        try:
            scored = self._score_candidates(
                ledger,
                pools,
                prepared,
                fingerprint,
                best,
                include_components=not force_system,
            )
        except FunctionNetworkArtifactError:
            raise
        except Exception as error:
            return self._warm_system_action(
                pools,
                next_index,
                fingerprint,
                started,
                entries,
                f"value_scoring_failure: {type(error).__name__}: {error}",
                warnings_=warning_text,
            )
        if not scored:
            raise SearchSpaceExhausted("no affordable partial-network action remains")
        maximum_bound = max(item.score + 1.96 * item.mcse / item.candidate.estimated_cost for item in scored)
        self._last_fingerprint = fingerprint
        self._last_diagnostics = BackendDiagnostics(
            backend=self.name,
            fit_state="fitted",
            warnings=warning_text,
            optimizer_seconds=time.perf_counter() - started,
            details={
                "ledger_entries": len(entries),
                "usable_system_observations": successful_system,
                "component_models": self._component_diagnostics(prepared),
                "candidate_pool_size": self.candidate_pool_size,
                "decision_pool_size": len(pools.decisions),
                "posterior_samples": self.posterior_sample_count,
                "fantasy_samples": self.fantasy_sample_count,
                "minimum_value_per_cost": self.minimum_value_per_cost,
                "maximum_value_per_cost_bound": maximum_bound,
                "forced_system_refresh": force_system,
                "component_streak": self._component_streak(entries),
                "acquisition": "finite_pool_one_step_value_of_information_per_cost",
                "candidate_scores": tuple(self._score_details(item) for item in scored),
            },
        )
        if maximum_bound <= self.minimum_value_per_cost:
            raise MarginalValueExhausted(
                "every affordable action has value per cost below the configured threshold"
            )
        selected = min(scored, key=lambda item: (-item.score, item.candidate.key))
        return (self._action_from_candidate(selected.candidate, next_index, "value"),)

    def _score_candidates(
        self,
        ledger: ObservationLedgerReader,
        pools: PartialCandidatePools,
        prepared: Mapping[str, _PreparedComponent],
        fingerprint: str,
        best: float,
        *,
        include_components: bool,
    ) -> tuple[_ScoredCandidate, ...]:
        baseline_values = [
            self._acquisition_stats(
                self._propagate(
                    prepared,
                    config,
                    fingerprint,
                    self.posterior_sample_count,
                ),
                best,
            )[0]
            for config in pools.decisions
        ]
        baseline_value = max(baseline_values)
        scored = []
        for candidate in pools.system:
            posterior = self._propagate(
                prepared,
                candidate.config,
                fingerprint,
                self.posterior_sample_count,
            )
            value, mcse = self._acquisition_stats(posterior, best)
            scored.append(
                _ScoredCandidate(
                    candidate,
                    value,
                    value,
                    mcse,
                    value / candidate.estimated_cost,
                    (posterior.seed,),
                )
            )
        if include_components:
            for candidate in pools.component:
                scored.append(
                    self._component_value(
                        ledger,
                        candidate,
                        pools.decisions,
                        prepared,
                        fingerprint,
                        best,
                        baseline_value,
                    )
                )
        return tuple(
            item
            for item in scored
            if math.isfinite(item.score)
            and item.candidate.estimated_cost > 0
            and item.value >= 0
            and item.mcse >= 0
        )

    def _component_value(
        self,
        ledger: ObservationLedgerReader,
        candidate: PartialActionCandidate,
        decisions: tuple[Mapping[str, Scalar], ...],
        prepared: Mapping[str, _PreparedComponent],
        fingerprint: str,
        best: float,
        baseline_value: float,
    ) -> _ScoredCandidate:
        item = prepared[candidate.component or ""]
        x = self._component_candidate_input(ledger, candidate, item)
        conditioned, fantasy_seeds = self._conditioned_fantasies(
            prepared,
            candidate.component or "",
            x,
            fingerprint,
            candidate,
        )
        differences = []
        propagation_seeds = []
        for fantasy_prepared in conditioned:
            fantasy_values = []
            for config in decisions:
                posterior = self._propagate(
                    fantasy_prepared,
                    config,
                    fingerprint,
                    self.posterior_sample_count,
                )
                propagation_seeds.append(posterior.seed)
                fantasy_values.append(self._acquisition_stats(posterior, best)[0])
            value = max(fantasy_values)
            differences.append(value - baseline_value)
        raw = float(np.mean(differences))
        mcse = (
            0.0
            if len(differences) == 1
            else float(np.std(differences, ddof=1) / math.sqrt(len(differences)))
        )
        value = max(raw, 0.0)
        return _ScoredCandidate(
            candidate,
            value,
            raw,
            mcse,
            value / candidate.estimated_cost,
            (*fantasy_seeds, *propagation_seeds),
        )

    def _component_candidate_input(
        self,
        ledger: ObservationLedgerReader,
        candidate: PartialActionCandidate,
        prepared: _PreparedComponent,
    ):
        records = self._artifact_records(ledger.entries())
        record = records[candidate.parent_artifact_id]
        path = Path(record[2])
        if not path.is_absolute():
            ledger_path = getattr(ledger, "path", None)
            if ledger_path is None:
                raise FunctionNetworkArtifactError(
                    "relative parent artifacts require a ledger directory"
                )
            path = Path(ledger_path).parent / path
        arrays = read_verified_npz(path, record[3])
        local = {
            name.removeprefix(f"{prepared.spec.component}."): value
            for name, value in candidate.config.items()
        }
        upstream = {}
        for coupling in self.network.couplings:
            if coupling.target_component != prepared.spec.component:
                continue
            source = self.network.component_map[coupling.source_component]
            for output in source.scalar_outputs:
                if output.port != coupling.source_port:
                    continue
                key = f"{source.component}.{output.port}"
                upstream[scalar_observation_name(source.component, output.name)] = reduce_scalar(
                    arrays[key], output.reducer
                )
        values = {**upstream, **local}
        encoded = [
            self._encode_feature(
                prepared.spec,
                name,
                values[name],
                prepared.upstream_center,
                prepared.upstream_scale,
            )
            for name in prepared.feature_names
        ]
        return torch.tensor([encoded], dtype=torch.double)

    def _conditioned_fantasies(
        self,
        prepared: Mapping[str, _PreparedComponent],
        component_name: str,
        x,
        fingerprint: str,
        candidate: PartialActionCandidate,
    ) -> tuple[tuple[Mapping[str, _PreparedComponent], ...], tuple[int, ...]]:
        item = prepared[component_name]
        observable = tuple(
            output.name
            for output in item.spec.scalar_outputs
            if EvaluationScope.COMPONENT in output.observed_in
        )
        draws = {}
        seeds = []
        for output_name in observable:
            model = item.models.get(output_name)
            if model is None:
                raise ValueError(
                    f"component fantasy requires a fitted model for {component_name}.{output_name}"
                )
            seed = self._seed(
                fingerprint,
                "fantasy",
                component_name,
                output_name,
                str(candidate.key),
            )
            seeds.append(seed)
            with torch.no_grad():
                posterior = model.posterior(x)
                mean = float(posterior.mean.squeeze())
                variance = float(posterior.variance.squeeze().clamp_min(0.0))
            generator = np.random.default_rng(seed)
            draws[output_name] = mean + math.sqrt(variance) * generator.standard_normal(
                self.fantasy_sample_count
            )
        fantasies = []
        noise = max(self.spec.noise.noise_floor, np.finfo(np.float64).eps) ** 2
        for index in range(self.fantasy_sample_count):
            models = dict(item.models)
            for output_name in observable:
                y = torch.tensor([[draws[output_name][index]]], dtype=torch.double)
                models[output_name] = item.models[output_name].condition_on_observations(
                    X=x,
                    Y=y,
                    noise=torch.full_like(y, noise),
                )
                models[output_name].eval()
            conditioned_item = replace(item, models=MappingProxyType(models))
            fantasy = dict(prepared)
            fantasy[component_name] = conditioned_item
            fantasies.append(MappingProxyType(fantasy))
        return tuple(fantasies), tuple(seeds)

    def _acquisition_stats(self, posterior, best: float) -> tuple[float, float]:
        feasible = np.ones(posterior.sample_count, dtype=bool)
        for constraint in self.spec.constraints:
            values = posterior.constraints[constraint.outcome]
            feasible &= (
                values >= constraint.threshold
                if constraint.operator == ">="
                else values <= constraint.threshold
            )
        sign = 1.0 if self.spec.objective.direction == "maximize" else -1.0
        improvement = np.maximum(sign * (posterior.objective - best), 0.0)
        values = np.where(feasible, improvement, 0.0)
        mean = float(np.mean(values))
        mcse = (
            0.0
            if posterior.sample_count == 1
            else float(np.std(values, ddof=1) / math.sqrt(posterior.sample_count))
        )
        return mean, mcse

    def _deficient_components(self, tables) -> tuple[str, ...]:
        deficient = []
        for component_name in self.order:
            component = self.network.component_map[component_name]
            rows = self._aggregate_duplicate_rows(tables[component_name])
            required = 1 if not component.parameters and not component.inputs else self.min_component_observations
            if any(
                sum(output.name in row.outputs for row in rows) < required
                for output in component.scalar_outputs
            ):
                deficient.append(component_name)
        return tuple(deficient)

    @staticmethod
    def _component_streak(entries) -> int:
        streak = 0
        for action, _ in reversed(entries):
            if action.scope is not EvaluationScope.COMPONENT:
                break
            streak += 1
        return streak

    def _warm_system_action(
        self,
        pools,
        next_index,
        fingerprint,
        started,
        entries,
        reason,
        *,
        warnings_=(),
    ):
        if not pools.system:
            raise SearchSpaceExhausted("no affordable complete-system warm action remains")
        selected = pools.system[0]
        self._set_warm_diagnostics(
            fingerprint, started, entries, reason, selected, warnings_
        )
        return (self._action_from_candidate(selected, next_index, "system_warm_start"),)

    def _warm_component_action(
        self,
        selected,
        next_index,
        fingerprint,
        started,
        entries,
        deficient,
    ):
        self._set_warm_diagnostics(
            fingerprint,
            started,
            entries,
            f"component_warm_start: {','.join(deficient)}",
            selected,
            (),
        )
        return (self._action_from_candidate(selected, next_index, "component_warm_start"),)

    def _set_warm_diagnostics(
        self, fingerprint, started, entries, reason, selected, warning_text
    ) -> None:
        self._last_fingerprint = fingerprint
        self._last_diagnostics = BackendDiagnostics(
            backend=self.name,
            fit_state="warm_start",
            fallback_reasons=(reason,),
            warnings=tuple(warning_text),
            optimizer_seconds=time.perf_counter() - started,
            details={
                "ledger_entries": len(entries),
                "selected_scope": selected.scope.value,
                "selected_component": selected.component,
                "estimated_cost": selected.estimated_cost,
                "fallback": "deterministic_partial_warm_start",
            },
        )

    def _action_from_candidate(
        self, candidate: PartialActionCandidate, index: int, label: str
    ) -> EvaluationAction:
        seed = int(np.random.SeedSequence([self.spec.seed, index]).generate_state(1)[0])
        suggested_by = f"{self.name}:{label}"
        if candidate.scope is EvaluationScope.SYSTEM:
            return EvaluationAction.system(
                f"eval-{index:06d}", candidate.config, seed=seed, suggested_by=suggested_by
            )
        return EvaluationAction.component(
            f"eval-{index:06d}",
            candidate.component or "",
            candidate.config,
            parent_artifact_ids=(candidate.parent_artifact_id or "",),
            seed=seed,
            suggested_by=suggested_by,
        )

    @staticmethod
    def _score_details(item: _ScoredCandidate) -> Mapping[str, JSONValue]:
        return {
            "scope": item.candidate.scope.value,
            "component": item.candidate.component,
            "parent_artifact_id": item.candidate.parent_artifact_id,
            "config": dict(item.candidate.config),
            "estimated_cost": item.candidate.estimated_cost,
            "estimated_value": item.value,
            "raw_value_difference": item.raw_value,
            "monte_carlo_standard_error": item.mcse,
            "value_per_cost": item.score,
            "seeds": item.seeds,
        }

    def finite_space_exhausted(self, ledger: ObservationLedgerReader) -> bool:
        pools = self._candidate_pools(ledger)
        return not pools.system and not pools.component

    def identity_dict(self) -> dict[str, JSONValue]:
        identity = super().identity_dict()
        constructor = dict(identity["constructor"])
        constructor.update(
            {
                "min_component_observations": self.min_component_observations,
                "decision_pool_size": self.decision_pool_size,
                "fantasy_samples": self.fantasy_sample_count,
                "max_component_streak": self.max_component_streak,
                "minimum_value_per_cost": self.minimum_value_per_cost,
                "cost_quantile": self.cost_quantile,
            }
        )
        identity["constructor"] = constructor
        identity["candidate_policy"] = {
            "component_parents": "earlier_successful_system_artifacts",
            "component_chaining": False,
            "score": "finite_pool_one_step_value_of_information_per_cost",
        }
        return identity

    def state_dict(self) -> dict[str, JSONValue]:
        state = super().state_dict()
        state["partial_policy"] = {
            "min_component_observations": self.min_component_observations,
            "decision_pool_size": self.decision_pool_size,
            "fantasy_samples": self.fantasy_sample_count,
            "max_component_streak": self.max_component_streak,
            "minimum_value_per_cost": self.minimum_value_per_cost,
            "cost_quantile": self.cost_quantile,
        }
        return state

    def _candidate_pools(self, ledger: ObservationLedgerReader) -> PartialCandidatePools:
        entries = ledger.entries()
        self.validate_entries(entries)
        fingerprint = self._fingerprint(entries)
        action_configs = self._sobol_configs(
            self.candidate_pool_size, fingerprint, "action-pool"
        )
        decisions = self._sobol_configs(
            self.decision_pool_size, fingerprint, "decision-pool"
        )
        spent = sum(result.cost for _, result in entries)
        remaining = self.spec.budget.max_cost - spent
        observed_system = {
            _canonical_config(action.config)
            for action, _ in entries
            if action.scope is EvaluationScope.SYSTEM
        }
        system_cost = self.estimated_action_cost(
            EvaluationAction.system("eval-000000", {}), entries
        )
        system_candidates = tuple(
            PartialActionCandidate(EvaluationScope.SYSTEM, config, system_cost)
            for config in action_configs
            if _canonical_config(config) not in observed_system and system_cost <= remaining
        )
        parents = self._eligible_parent_artifacts(ledger, entries)
        observed_component = {
            (
                action.component,
                action.parent_artifact_ids[0] if action.parent_artifact_ids else "",
                _canonical_config(action.config),
            )
            for action, _ in entries
            if action.scope is EvaluationScope.COMPONENT
        }
        component_candidates = []
        for component_name in self._eligible_component_names(self.network):
            component = self.network.component_map[component_name]
            cost = self.estimated_action_cost(
                EvaluationAction.component("eval-000000", component_name, {}), entries
            )
            if cost > remaining:
                continue
            for config in action_configs:
                local = self._project_local_config(component, config)
                local_key = _canonical_config(local)
                for parent_id, compatible in parents.items():
                    if component_name not in compatible:
                        continue
                    if (component_name, parent_id, local_key) in observed_component:
                        continue
                    component_candidates.append(
                        PartialActionCandidate(
                            EvaluationScope.COMPONENT,
                            local,
                            cost,
                            component=component_name,
                            parent_artifact_id=parent_id,
                        )
                    )
        return PartialCandidatePools(
            decisions=tuple(MappingProxyType(dict(config)) for config in decisions),
            system=system_candidates,
            component=tuple(component_candidates),
        )

    def _eligible_parent_artifacts(self, ledger, entries):
        base = None
        ledger_path = getattr(ledger, "path", None)
        if ledger_path is not None:
            base = Path(ledger_path).parent
        eligible = {}
        for action, result in entries:
            if action.scope is not EvaluationScope.SYSTEM or result.status is not EvaluationStatus.SUCCESS:
                continue
            for artifact_id, value in result.artifacts.items():
                path = Path(value)
                compatible = []
                for component_name in self._eligible_component_names(self.network):
                    try:
                        self._validate_parent_inputs(
                            component_name,
                            path,
                            result.artifact_sha256[artifact_id],
                            base=base,
                        )
                    except FunctionNetworkArtifactError as error:
                        if "lacks direct upstream ports" not in str(error):
                            raise
                    else:
                        compatible.append(component_name)
                eligible[artifact_id] = tuple(compatible)
        return MappingProxyType(eligible)

    @staticmethod
    def _project_local_config(
        component: FunctionComponentSpec, config: Mapping[str, Scalar]
    ) -> Mapping[str, Scalar]:
        prefix = f"{component.component}."
        local = {
            name: value for name, value in config.items() if name.startswith(prefix)
        }
        validate_local_parameter_values(
            component,
            {name.removeprefix(prefix): value for name, value in local.items()},
        )
        return MappingProxyType(local)

    def _sobol_configs(
        self, count: int, fingerprint: str, label: str
    ) -> tuple[Mapping[str, Scalar], ...]:
        decoder = SobolBackend(self.spec, self.space)
        sampler = qmc.Sobol(
            d=self.space.encoded_dimension,
            scramble=True,
            seed=self._seed(fingerprint, label),
        )
        draw_count = 1 << max(1, (count * 8 - 1).bit_length())
        configs = []
        seen = set()
        for point in sampler.random_base2(int(math.log2(draw_count))):
            config = decoder._decode_projected(point)
            key = _canonical_config(config)
            if key in seen:
                continue
            seen.add(key)
            configs.append(MappingProxyType(config))
            if len(configs) == count:
                break
        if not configs:
            raise ValueError("Sobol candidate pool produced no valid configurations")
        return tuple(configs)
