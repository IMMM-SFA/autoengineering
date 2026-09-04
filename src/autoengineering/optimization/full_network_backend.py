"""Optional full-observability Bayesian optimization over a function network."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
import hashlib
import json
import math
from types import MappingProxyType
import time
import warnings

import numpy as np

try:
    import torch
    from botorch.exceptions.warnings import NumericsWarning, OptimizationWarning
    from botorch.fit import fit_gpytorch_mll
    from botorch.models import SingleTaskGP
    from botorch.models.transforms.outcome import Standardize
    from gpytorch.mlls import ExactMarginalLogLikelihood
except ImportError as error:  # pragma: no cover - exercised in a no-extra subprocess
    raise ImportError(
        "FullNetworkBayesBackend requires the optional Bayesian dependencies; "
        "install autoengineering[bayes] or use the pixi bayes environment."
    ) from error

from autoengineering.system.graph import System

from .backend import SobolBackend, _BaselineBackend, _canonical_config
from .function_network import (
    FunctionComponentSpec,
    FunctionNetworkSpec,
    validate_local_parameter_values,
)
from .function_network_evaluator import (
    ComponentTrainingRow,
    FunctionNetworkArtifactError,
    reconstruct_component_training_tables,
)
from .ledger import ObservationLedgerReader
from .records import (
    BackendDiagnostics,
    EvaluationAction,
    EvaluationScope,
    EvaluationStatus,
    JSONValue,
    Scalar,
)
from .space import CategoricalParameter, SearchSpace
from .spec import StudySpec


_SCHEMA_VERSION = "1.0"
_MACHINE_NOISE_FLOOR = float(np.finfo(np.float64).eps)


def _read_only(values: np.ndarray) -> np.ndarray:
    result = np.asarray(values, dtype=np.float64).copy()
    result.setflags(write=False)
    return result


@dataclass(frozen=True)
class NetworkPosteriorSamples:
    """Immutable propagated component and terminal posterior samples."""

    objective: np.ndarray
    constraints: Mapping[str, np.ndarray]
    component_outputs: Mapping[str, Mapping[str, np.ndarray]]
    sample_count: int
    seed: int

    def __post_init__(self) -> None:
        if isinstance(self.sample_count, bool) or not isinstance(self.sample_count, int):
            raise TypeError("sample_count must be an integer")
        if self.sample_count <= 0:
            raise ValueError("sample_count must be positive")
        if isinstance(self.seed, bool) or not isinstance(self.seed, int):
            raise TypeError("seed must be an integer")
        objective = _read_only(self.objective)
        if objective.shape != (self.sample_count,) or not np.all(np.isfinite(objective)):
            raise ValueError("objective samples must be finite and match sample_count")
        object.__setattr__(self, "objective", objective)
        constraints = {name: _read_only(values) for name, values in self.constraints.items()}
        if any(values.shape != (self.sample_count,) for values in constraints.values()):
            raise ValueError("constraint samples must match sample_count")
        object.__setattr__(self, "constraints", MappingProxyType(constraints))
        outputs: dict[str, Mapping[str, np.ndarray]] = {}
        for component, values in self.component_outputs.items():
            outputs[component] = MappingProxyType(
                {name: _read_only(samples) for name, samples in values.items()}
            )
            if any(
                samples.shape != (self.sample_count,) for samples in outputs[component].values()
            ):
                raise ValueError("component samples must match sample_count")
        object.__setattr__(self, "component_outputs", MappingProxyType(outputs))


@dataclass(frozen=True)
class _PreparedComponent:
    spec: FunctionComponentSpec
    feature_names: tuple[str, ...]
    upstream_center: Mapping[str, float]
    upstream_scale: Mapping[str, float]
    models: Mapping[str, object]
    constants: Mapping[str, tuple[float, float]]
    fit_attempts: Mapping[str, int]
    row_count: int


class FullNetworkBayesBackend(_BaselineBackend):
    """Fit component GPs and score complete-system configurations."""

    name = "function_network_full"

    def __init__(
        self,
        spec: StudySpec,
        space: SearchSpace,
        network: FunctionNetworkSpec,
        system: System,
        *,
        min_initial: int = 4,
        candidate_pool_size: int = 64,
        posterior_samples: int = 128,
        fit_retry_limit: int = 2,
    ) -> None:
        super().__init__(spec, space)
        if not isinstance(network, FunctionNetworkSpec):
            raise TypeError("network must be a FunctionNetworkSpec")
        if not isinstance(system, System):
            raise TypeError("system must be a System")
        for name, value, minimum in (
            ("min_initial", min_initial, 2),
            ("candidate_pool_size", candidate_pool_size, 2),
            ("posterior_samples", posterior_samples, 8),
            ("fit_retry_limit", fit_retry_limit, 1),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
                raise ValueError(f"{name} must be an integer >= {minimum}")
        self._validate_backend_name()
        order = network.validate(system)
        self._validate_contract(network)
        self._validate_search_space(network)
        self.network = network
        self.system = system
        self.order = order
        self.min_initial = min_initial
        self.candidate_pool_size = candidate_pool_size
        self.posterior_sample_count = posterior_samples
        self.fit_retry_limit = fit_retry_limit
        self._last_fingerprint: str | None = None
        self._last_diagnostics: BackendDiagnostics | None = None

    def _validate_backend_name(self) -> None:
        if self.spec.backend != self.name:
            raise ValueError(f"study backend must be {self.name!r}")

    def _validate_contract(self, network: FunctionNetworkSpec) -> None:
        if (
            self.spec.objective.outcome != network.objective.outcome
            or self.spec.objective.direction != network.objective.direction
        ):
            raise ValueError("study objective must match the function network objective")
        study_constraints = tuple(
            (item.outcome, item.operator, float(item.threshold)) for item in self.spec.constraints
        )
        network_constraints = tuple(
            (item.outcome, item.operator, float(item.threshold)) for item in network.constraints
        )
        if study_constraints != network_constraints:
            raise ValueError("study constraints must match the function network constraints")
        if any(
            component.cost_unit != self.spec.budget.cost_unit for component in network.components
        ):
            raise ValueError("study and function network cost units must match")
        self._validate_observability_contract(network)

    def _validate_observability_contract(self, network: FunctionNetworkSpec) -> None:
        unavailable = [
            f"{component.component}.{output.name}"
            for component in network.components
            for output in component.scalar_outputs
            if EvaluationScope.SYSTEM not in output.observed_in
        ]
        if unavailable:
            raise ValueError(
                "full-observability backend requires every scalar output at system scope: "
                f"{unavailable}"
            )

    def _validate_search_space(self, network: FunctionNetworkSpec) -> None:
        expected = []
        for component in network.components:
            prefix = f"{component.component}."
            for parameter in component.parameters:
                data = parameter.to_dict()
                data["name"] = prefix + parameter.name
                if "active_when" in data:
                    data["active_when"] = {
                        prefix + name: values for name, values in data["active_when"].items()
                    }
                expected.append(data)
        actual = [parameter.to_dict() for parameter in self.space.parameters]
        if actual != expected:
            raise ValueError(
                "global search space must exactly match qualified function network parameters"
            )

    def suggest(self, ledger: ObservationLedgerReader, n: int = 1) -> tuple[EvaluationAction, ...]:
        """Suggest globally valid system actions from propagated expected improvement."""
        self._validate_n(n)
        previous_enabled = torch.are_deterministic_algorithms_enabled()
        previous_warn_only = torch.is_deterministic_algorithms_warn_only_enabled()
        with torch.random.fork_rng(devices=[]):
            try:
                torch.use_deterministic_algorithms(True, warn_only=True)
                return self._suggest(ledger, n)
            finally:
                torch.use_deterministic_algorithms(previous_enabled, warn_only=previous_warn_only)

    def _suggest(self, ledger: ObservationLedgerReader, n: int) -> tuple[EvaluationAction, ...]:
        started = time.perf_counter()
        entries = ledger.entries()
        self._validate_training_entries(entries)
        next_index, observed = self._next_index_and_observed(ledger)
        fingerprint = self._fingerprint(entries)
        successful = self._count_initial_observations(entries)
        if successful < self.min_initial:
            return self._sobol(
                ledger,
                n,
                fingerprint,
                started,
                ("cold_start_insufficient_system_observations",),
                successful,
            )

        tables = reconstruct_component_training_tables(self.network, self.system, ledger)
        captured: list[warnings.WarningMessage] = []
        try:
            with warnings.catch_warnings(record=True) as captured:
                warnings.simplefilter("always")
                prepared = self._fit_components(tables, fingerprint)
        except FunctionNetworkArtifactError:
            raise
        except Exception as error:
            return self._sobol(
                ledger,
                n,
                fingerprint,
                started,
                (f"component_fit_failure: {type(error).__name__}: {error}",),
                successful,
                warnings_=self._warning_text(captured),
            )
        warning_text = self._warning_text(captured)
        if self._has_fatal_warning(captured):
            return self._sobol(
                ledger,
                n,
                fingerprint,
                started,
                ("component_fit_warning_indicates_failure",),
                successful,
                warnings_=warning_text,
            )

        try:
            pool_actions = SobolBackend(self.spec, self.space).suggest(
                ledger, self.candidate_pool_size
            )
        except Exception as error:
            return self._sobol(
                ledger,
                n,
                fingerprint,
                started,
                (f"candidate_pool_failure: {type(error).__name__}: {error}",),
                successful,
                warnings_=warning_text,
            )
        recommendation = super().recommend(ledger)
        best = (
            None
            if recommendation.action_id is None
            else recommendation.outcomes[self.spec.objective.outcome]
        )
        scored = []
        try:
            for action in pool_actions:
                posterior = self._propagate(
                    prepared,
                    action.config,
                    fingerprint,
                    self.posterior_sample_count,
                )
                score = self._acquisition_value(posterior, best)
                if not math.isfinite(score):
                    raise ValueError("propagated acquisition is nonfinite")
                scored.append((score, _canonical_config(action.config), dict(action.config)))
        except Exception as error:
            return self._sobol(
                ledger,
                n,
                fingerprint,
                started,
                (f"posterior_propagation_failure: {type(error).__name__}: {error}",),
                successful,
                warnings_=warning_text,
            )
        scored.sort(key=lambda item: (-item[0], item[1]))
        selected = set(observed)
        actions = []
        for _, key, config in scored:
            if key in selected:
                continue
            selected.add(key)
            actions.append(
                replace(
                    self._action(next_index + len(actions), config),
                    suggested_by="function_network_full:bayes",
                )
            )
            if len(actions) == n:
                break
        if len(actions) != n:
            return self._sobol(
                ledger,
                n,
                fingerprint,
                started,
                ("candidate_pool_cannot_supply_requested_batch",),
                successful,
                warnings_=warning_text,
            )

        self._last_fingerprint = fingerprint
        self._last_diagnostics = BackendDiagnostics(
            backend=self.name,
            fit_state="fitted",
            warnings=tuple(warning_text),
            optimizer_seconds=time.perf_counter() - started,
            details={
                "ledger_entries": len(entries),
                "usable_system_observations": successful,
                "component_models": self._component_diagnostics(prepared),
                "candidate_pool_size": self.candidate_pool_size,
                "posterior_samples": self.posterior_sample_count,
                "acquisition": "constrained_monte_carlo_expected_improvement",
                "posterior_dependence": "independent_output_and_component_innovations",
                "deterministic_seed": self._seed(fingerprint, "suggest"),
            },
        )
        return tuple(actions)

    def posterior_samples(
        self,
        ledger: ObservationLedgerReader,
        config: Mapping[str, Scalar],
        *,
        sample_count: int | None = None,
    ) -> NetworkPosteriorSamples:
        """Fit from ``ledger`` and propagate deterministic samples for ``config``."""
        return self.posterior_samples_many(ledger, (config,), sample_count=sample_count)[0]

    def posterior_samples_many(
        self,
        ledger: ObservationLedgerReader,
        configs: tuple[Mapping[str, Scalar], ...],
        *,
        sample_count: int | None = None,
    ) -> tuple[NetworkPosteriorSamples, ...]:
        """Fit once and propagate deterministic samples for several configurations."""
        configs = tuple(configs)
        if not configs:
            raise ValueError("configs must not be empty")
        if sample_count is None:
            sample_count = self.posterior_sample_count
        if isinstance(sample_count, bool) or not isinstance(sample_count, int) or sample_count < 1:
            raise ValueError("sample_count must be a positive integer")
        for config in configs:
            self.space.encode(config)
        entries = ledger.entries()
        self._validate_training_entries(entries)
        fingerprint = self._fingerprint(entries)
        tables = reconstruct_component_training_tables(self.network, self.system, ledger)
        successful = self._count_initial_observations(entries)
        if successful < self.min_initial:
            raise ValueError(
                "posterior prediction requires the minimum successful system observations"
            )
        prepared = self._fit_components(tables, fingerprint)
        return tuple(
            self._propagate(prepared, config, fingerprint, sample_count) for config in configs
        )

    def _validate_training_entries(self, entries) -> None:
        if any(action.scope is not EvaluationScope.SYSTEM for action, _ in entries):
            raise ValueError("full-observability backend requires only system scope observations")

    def _count_initial_observations(self, entries) -> int:
        return sum(
            action.scope is EvaluationScope.SYSTEM and result.status is EvaluationStatus.SUCCESS
            for action, result in entries
        )

    def _select_component_training_rows(
        self,
        component_name: str,
        tables: Mapping[str, tuple[ComponentTrainingRow, ...]],
    ) -> tuple[ComponentTrainingRow, ...]:
        return tuple(
            row for row in tables[component_name] if row.scope is EvaluationScope.SYSTEM
        )

    def _fit_components(
        self,
        tables: Mapping[str, tuple[ComponentTrainingRow, ...]],
        fingerprint: str,
    ) -> Mapping[str, _PreparedComponent]:
        prepared: dict[str, _PreparedComponent] = {}
        for component_name in self.order:
            component = self.network.component_map[component_name]
            rows = self._select_component_training_rows(component_name, tables)
            if not rows:
                raise ValueError(f"component {component_name!r} has no successful system rows")
            feature_names = tuple(rows[0].inputs)
            if any(tuple(row.inputs) != feature_names for row in rows[1:]):
                raise ValueError(
                    f"component {component_name!r} training rows have incompatible active schemas"
                )
            upstream = tuple(
                name
                for name in feature_names
                if name not in {parameter.name for parameter in component.parameters}
            )
            center = {
                name: float(np.mean([float(row.inputs[name]) for row in rows])) for name in upstream
            }
            scale = {
                name: max(
                    float(np.std([float(row.inputs[name]) for row in rows], ddof=0)),
                    _MACHINE_NOISE_FLOOR,
                )
                for name in upstream
            }
            scale = {
                name: 1.0 if value <= _MACHINE_NOISE_FLOOR else value
                for name, value in scale.items()
            }
            models: dict[str, object] = {}
            constants: dict[str, tuple[float, float]] = {}
            fit_attempts: dict[str, int] = {}
            if not feature_names:
                for output in component.scalar_outputs:
                    values = np.asarray([row.outputs[output.name] for row in rows], dtype=float)
                    constants[output.name] = (
                        float(np.mean(values)),
                        self._constant_variance(rows, output.name, values),
                    )
            else:
                train_x = torch.tensor(
                    [
                        self._encode_training_row(component, row, feature_names, center, scale)
                        for row in rows
                    ],
                    dtype=torch.double,
                )
                for output in component.scalar_outputs:
                    train_y = torch.tensor(
                        [[row.outputs[output.name]] for row in rows], dtype=torch.double
                    )
                    train_yvar = self._training_variance(rows, output.name)
                    model, attempts = self._fit_one(
                        train_x,
                        train_y,
                        train_yvar,
                        self._seed(fingerprint, component_name, output.name, "fit"),
                    )
                    models[output.name] = model
                    fit_attempts[output.name] = attempts
            prepared[component_name] = _PreparedComponent(
                spec=component,
                feature_names=feature_names,
                upstream_center=MappingProxyType(center),
                upstream_scale=MappingProxyType(scale),
                models=MappingProxyType(models),
                constants=MappingProxyType(constants),
                fit_attempts=MappingProxyType(fit_attempts),
                row_count=len(rows),
            )
        return MappingProxyType(prepared)

    def _training_variance(
        self, rows: tuple[ComponentTrainingRow, ...], output_name: str
    ) -> object | None:
        if self.spec.noise.mode == "learned":
            return None
        floor = max(self.spec.noise.noise_floor, _MACHINE_NOISE_FLOOR)
        values = []
        for row in rows:
            if self.spec.noise.mode == "known" and output_name not in row.standard_errors:
                raise ValueError(
                    f"known noise requires standard error for {row.component}.{output_name}"
                )
            error = (
                0.0 if self.spec.noise.mode == "deterministic" else row.standard_errors[output_name]
            )
            values.append([max(float(error), floor) ** 2])
        return torch.tensor(values, dtype=torch.double)

    def _constant_variance(
        self,
        rows: tuple[ComponentTrainingRow, ...],
        output_name: str,
        values: np.ndarray,
    ) -> float:
        floor = max(self.spec.noise.noise_floor, _MACHINE_NOISE_FLOOR)
        if self.spec.noise.mode == "known":
            missing = [row for row in rows if output_name not in row.standard_errors]
            if missing:
                raise ValueError(
                    f"known noise requires standard error for {rows[0].component}.{output_name}"
                )
            return max(
                float(np.mean([row.standard_errors[output_name] ** 2 for row in rows])), floor**2
            )
        if self.spec.noise.mode == "learned" and len(values) > 1:
            return max(float(np.var(values, ddof=1)), floor**2)
        return floor**2

    def _fit_one(self, train_x, train_y, train_yvar, seed: int):
        last_error: Exception | None = None
        for attempt in range(self.fit_retry_limit):
            torch.manual_seed(seed + attempt)
            try:
                model = SingleTaskGP(
                    train_x,
                    train_y,
                    train_Yvar=train_yvar,
                    outcome_transform=Standardize(m=1),
                )
                mll = ExactMarginalLogLikelihood(model.likelihood, model)
                fit_gpytorch_mll(mll)
                model.eval()
                return model, attempt + 1
            except Exception as error:
                last_error = error
        assert last_error is not None
        raise last_error

    def _encode_training_row(
        self,
        component: FunctionComponentSpec,
        row: ComponentTrainingRow,
        feature_names: tuple[str, ...],
        center: Mapping[str, float],
        scale: Mapping[str, float],
    ) -> tuple[float, ...]:
        return tuple(
            self._encode_feature(component, name, row.inputs[name], center, scale)
            for name in feature_names
        )

    def _encode_feature(
        self,
        component: FunctionComponentSpec,
        name: str,
        value: Scalar,
        center: Mapping[str, float],
        scale: Mapping[str, float],
    ) -> float:
        parameters = {parameter.name: parameter for parameter in component.parameters}
        parameter = parameters.get(name)
        if parameter is None:
            return (float(value) - center[name]) / scale[name]
        if isinstance(parameter, CategoricalParameter):
            index = next(
                index
                for index, category in enumerate(parameter.categories)
                if type(value) is type(category) and value == category
            )
            return index / max(len(parameter.categories) - 1, 1)
        numeric = float(value)
        if parameter.scale == "log":
            numeric = math.log(numeric)
            lower = math.log(parameter.lower)
            upper = math.log(parameter.upper)
        else:
            lower = float(parameter.lower)
            upper = float(parameter.upper)
        return (numeric - lower) / (upper - lower)

    def _propagate(
        self,
        prepared: Mapping[str, _PreparedComponent],
        config: Mapping[str, Scalar],
        fingerprint: str,
        sample_count: int,
    ) -> NetworkPosteriorSamples:
        self.space.encode(config)
        propagated: dict[str, np.ndarray] = {}
        component_outputs: dict[str, Mapping[str, np.ndarray]] = {}
        seed = self._seed(fingerprint, self._config_json(config), str(sample_count), "propagate")
        for component_name in self.order:
            item = prepared[component_name]
            local = {
                parameter.name: config[f"{component_name}.{parameter.name}"]
                for parameter in item.spec.parameters
                if f"{component_name}.{parameter.name}" in config
            }
            validate_local_parameter_values(item.spec, local)
            outputs: dict[str, np.ndarray] = {}
            if item.constants:
                for output_name, (mean, variance) in item.constants.items():
                    generator = np.random.default_rng(
                        self._seed(
                            fingerprint, component_name, output_name, self._config_json(config)
                        )
                    )
                    if variance <= _MACHINE_NOISE_FLOOR**2:
                        samples = np.full(sample_count, mean, dtype=float)
                    else:
                        samples = generator.normal(mean, math.sqrt(variance), sample_count)
                    outputs[output_name] = samples
            else:
                x = self._prediction_inputs(item, local, propagated, sample_count)
                x_tensor = torch.tensor(x, dtype=torch.double)
                for output in item.spec.scalar_outputs:
                    model = item.models[output.name]
                    draw_seed = self._seed(
                        fingerprint,
                        component_name,
                        output.name,
                        self._config_json(config),
                        str(sample_count),
                    )
                    with torch.random.fork_rng(devices=[]):
                        torch.manual_seed(draw_seed)
                        with torch.no_grad():
                            posterior = model.posterior(x_tensor)
                            means = posterior.mean.squeeze(-1).detach().cpu().numpy()
                            variances = (
                                posterior.variance.squeeze(-1).clamp_min(0.0).detach().cpu().numpy()
                            )
                    generator = np.random.default_rng(draw_seed)
                    innovations = generator.standard_normal(sample_count)
                    samples = means + np.sqrt(variances) * innovations
                    outputs[output.name] = np.asarray(samples, dtype=float)
            for name, values in outputs.items():
                if values.shape != (sample_count,) or not np.all(np.isfinite(values)):
                    raise ValueError(
                        f"component {component_name!r} produced invalid posterior samples"
                    )
                propagated[f"{component_name}.{name}"] = values
            component_outputs[component_name] = MappingProxyType(outputs)
        objective_key = f"{self.network.objective.component}.{self.network.objective.scalar_output}"
        constraints = {
            item.outcome: propagated[f"{item.component}.{item.scalar_output}"]
            for item in self.network.constraints
        }
        return NetworkPosteriorSamples(
            objective=propagated[objective_key],
            constraints=constraints,
            component_outputs=component_outputs,
            sample_count=sample_count,
            seed=seed,
        )

    def _prediction_inputs(
        self,
        prepared: _PreparedComponent,
        local: Mapping[str, Scalar],
        propagated: Mapping[str, np.ndarray],
        sample_count: int,
    ) -> np.ndarray:
        columns = []
        for name in prepared.feature_names:
            if name in local:
                encoded = self._encode_feature(
                    prepared.spec,
                    name,
                    local[name],
                    prepared.upstream_center,
                    prepared.upstream_scale,
                )
                columns.append(np.full(sample_count, encoded, dtype=float))
            else:
                values = propagated.get(name)
                if values is None:
                    raise ValueError(
                        f"component {prepared.spec.component!r} lacks upstream samples {name!r}"
                    )
                columns.append(
                    (values - prepared.upstream_center[name]) / prepared.upstream_scale[name]
                )
        return np.column_stack(columns)

    def _acquisition_value(self, posterior: NetworkPosteriorSamples, best: float | None) -> float:
        feasible = np.ones(posterior.sample_count, dtype=bool)
        for constraint in self.spec.constraints:
            values = posterior.constraints[constraint.outcome]
            feasible &= (
                values >= constraint.threshold
                if constraint.operator == ">="
                else values <= constraint.threshold
            )
        sign = 1.0 if self.spec.objective.direction == "maximize" else -1.0
        objective = sign * posterior.objective
        if best is None:
            return float(np.mean(np.where(feasible, objective, 0.0)))
        improvement = np.maximum(objective - sign * best, 0.0)
        return float(np.mean(np.where(feasible, improvement, 0.0)))

    def diagnostics(self, ledger: ObservationLedgerReader) -> BackendDiagnostics:
        entries = ledger.entries()
        fingerprint = self._fingerprint(entries)
        if self._last_diagnostics is not None and self._last_fingerprint == fingerprint:
            return self._last_diagnostics
        return BackendDiagnostics(
            backend=self.name,
            fit_state="not_fit_for_ledger",
            details={"ledger_entries": len(entries), "ledger_fingerprint": fingerprint},
        )

    def recommend(self, ledger: ObservationLedgerReader):
        self._next_index_and_observed(ledger)
        return super().recommend(ledger)

    def identity_dict(self) -> dict[str, JSONValue]:
        return {
            "schema_version": _SCHEMA_VERSION,
            "name": self.name,
            "constructor": {
                "min_initial": self.min_initial,
                "candidate_pool_size": self.candidate_pool_size,
                "posterior_samples": self.posterior_sample_count,
                "fit_retry_limit": self.fit_retry_limit,
            },
            "network_sha256": hashlib.sha256(self.network.to_json().encode()).hexdigest(),
            "fallback_policy": SobolBackend(self.spec, self.space).identity_dict(),
        }

    def state_dict(self) -> dict[str, JSONValue]:
        return {
            "schema_version": _SCHEMA_VERSION,
            "name": self.name,
            "study_seed": self.spec.seed,
            "network_sha256": hashlib.sha256(self.network.to_json().encode()).hexdigest(),
            "last_ledger_fingerprint": self._last_fingerprint,
            "last_fit": (
                {} if self._last_diagnostics is None else self._last_diagnostics.to_dict()
            ),
        }

    def _sobol(
        self,
        ledger: ObservationLedgerReader,
        n: int,
        fingerprint: str,
        started: float,
        reasons: tuple[str, ...],
        usable: int,
        *,
        warnings_: tuple[str, ...] = (),
    ) -> tuple[EvaluationAction, ...]:
        actions = tuple(
            replace(action, suggested_by="function_network_full:sobol")
            for action in SobolBackend(self.spec, self.space).suggest(ledger, n)
        )
        self._last_fingerprint = fingerprint
        self._last_diagnostics = BackendDiagnostics(
            backend=self.name,
            fit_state="fallback",
            fallback_reasons=reasons,
            warnings=warnings_,
            optimizer_seconds=time.perf_counter() - started,
            details={
                "ledger_entries": len(ledger.entries()),
                "usable_system_observations": usable,
                "candidate_pool_size": self.candidate_pool_size,
                "posterior_samples": self.posterior_sample_count,
                "fallback": "scrambled_sobol",
            },
        )
        return actions

    def _component_diagnostics(
        self, prepared: Mapping[str, _PreparedComponent]
    ) -> Mapping[str, JSONValue]:
        return {
            name: {
                "row_count": item.row_count,
                "feature_order": item.feature_names,
                "output_order": tuple(output.name for output in item.spec.scalar_outputs),
                "constant_outputs": tuple(item.constants),
                "model_count": len(item.models),
                "fit_attempts": dict(item.fit_attempts),
                "upstream_center": dict(item.upstream_center),
                "upstream_scale": dict(item.upstream_scale),
            }
            for name, item in prepared.items()
        }

    @staticmethod
    def _warning_text(records: list[warnings.WarningMessage]) -> tuple[str, ...]:
        return tuple(f"{item.category.__name__}: {item.message}" for item in records)

    @staticmethod
    def _has_fatal_warning(records: list[warnings.WarningMessage]) -> bool:
        markers = ("fail", "converg", "optimiz", "numerical", "nonfinite", "nan", "invalid")
        for item in records:
            message = str(item.message).lower()
            if issubclass(item.category, OptimizationWarning):
                return True
            if "very small noise values detected" in message:
                continue
            if issubclass(item.category, (NumericsWarning, RuntimeWarning)) and any(
                marker in message for marker in markers
            ):
                return True
        return False

    @staticmethod
    def _fingerprint(entries) -> str:
        payload = [
            {"action": action.to_dict(), "result": result.to_dict()} for action, result in entries
        ]
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()

    @staticmethod
    def _config_json(config: Mapping[str, Scalar]) -> str:
        return json.dumps(dict(config), sort_keys=True, separators=(",", ":"))

    def _seed(self, *parts: str) -> int:
        digest = hashlib.sha256("\0".join((str(self.spec.seed), *parts)).encode("utf-8")).digest()
        return int.from_bytes(digest[:8], "big") % (2**31 - 1)
