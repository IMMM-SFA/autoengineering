"""Optional BoTorch policy for complete-system constrained optimization.

This module deliberately owns the optional import boundary: importing the
base :mod:`autoengineering.optimization` package never imports Torch. Inputs
from ``SearchSpace`` already live in the unit cube, so no input normalization
is applied; outcome standardization is performed independently per model.
"""

from __future__ import annotations

from dataclasses import replace
from itertools import product
import hashlib
import json
import math
import time
import warnings

import numpy as np

try:
    import torch
    from botorch.acquisition import qLogNoisyExpectedImprovement
    from botorch.acquisition.objective import GenericMCObjective
    from botorch.fit import fit_gpytorch_mll
    from botorch.models import ModelListGP, SingleTaskGP
    from botorch.models.transforms.outcome import Standardize
    from botorch.optim import optimize_acqf_mixed
    from gpytorch.mlls import SumMarginalLogLikelihood
except ImportError as error:  # pragma: no cover - exercised in a no-extra subprocess
    raise ImportError(
        "SystemBayesBackend requires the optional Bayesian dependencies; "
        "install autoengineering[bayes] or use the pixi bayes environment."
    ) from error

from .backend import SobolBackend, _BaselineBackend, _canonical_config
from .ledger import ObservationLedger
from .records import (
    BackendDiagnostics,
    EvaluationAction,
    EvaluationScope,
    EvaluationStatus,
    JSONValue,
)
from .space import CategoricalParameter, ContinuousParameter, IntegerParameter, SearchSpace
from .spec import StudySpec


_SCHEMA_VERSION = "1.0"
_MACHINE_NOISE_FLOOR = float(np.finfo(np.float64).eps)


class SystemBayesBackend(_BaselineBackend):
    """Fresh, deterministic BoTorch fits over completed system evaluations.

    Batch suggestions are greedy without pending fantasies.  A candidate that
    duplicates an earlier member of the batch is retried a bounded number of
    times and then supplied by the deterministic Sobol policy.
    """

    name = "system"

    def __init__(
        self,
        spec: StudySpec,
        space: SearchSpace,
        *,
        min_initial: int = 6,
        num_restarts: int = 8,
        raw_samples: int = 128,
        max_categorical_assignments: int = 128,
        candidate_retry_limit: int = 3,
    ) -> None:
        super().__init__(spec, space)
        for name, value, minimum in (
            ("min_initial", min_initial, 1),
            ("num_restarts", num_restarts, 1),
            ("raw_samples", raw_samples, 2),
            ("max_categorical_assignments", max_categorical_assignments, 1),
            ("candidate_retry_limit", candidate_retry_limit, 1),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
                raise ValueError(f"{name} must be an integer >= {minimum}")
        self.min_initial = min_initial
        self.num_restarts = num_restarts
        self.raw_samples = raw_samples
        self.max_categorical_assignments = max_categorical_assignments
        self.candidate_retry_limit = candidate_retry_limit
        self._last_fingerprint: str | None = None
        self._last_count = 0
        self._last_diagnostics: BackendDiagnostics | None = None

    def suggest(self, ledger: ObservationLedger, n: int = 1) -> tuple[EvaluationAction, ...]:
        """Suggest ``n`` valid points, falling back to replayable Sobol when needed."""
        self._validate_n(n)
        started = time.perf_counter()
        entries = ledger.entries()
        # Reuse baseline validation exactly, including canonical action IDs and configs.
        next_index, observed = self._next_index_and_observed(ledger)
        fingerprint = self._fingerprint(entries)
        prepared, excluded, noise_gap = self._observations(entries)
        seed = self.spec.seed + len(entries)
        torch.manual_seed(seed)
        torch.use_deterministic_algorithms(True, warn_only=True)
        fallback: list[str] = []
        warning_text: list[str] = []

        if noise_gap:
            fallback.append("known_noise_missing_standard_error")
            return self._sobol(
                ledger,
                n,
                fallback,
                fingerprint,
                len(entries),
                excluded,
                seed,
                started,
                warning_text,
            )
        if len(prepared[0]) < self.min_initial:
            fallback.append("cold_start_insufficient_usable_observations")
            return self._sobol(
                ledger,
                n,
                fallback,
                fingerprint,
                len(entries),
                excluded,
                seed,
                started,
                warning_text,
            )
        assignments = self._fixed_assignments()
        if len(assignments) > self.max_categorical_assignments:
            fallback.append("categorical_assignment_limit")
            return self._sobol(
                ledger,
                n,
                fallback,
                fingerprint,
                len(entries),
                excluded,
                seed,
                started,
                warning_text,
            )

        try:
            with warnings.catch_warnings(record=True) as captured:
                warnings.simplefilter("always")
                model, outcome_order, fit_details = self._fit(*prepared)
                warning_text.extend(str(item.message) for item in captured)
        except Exception as error:  # fitting and numerical routines must never leak stale state
            fallback.append(f"fit_failure: {type(error).__name__}: {error}")
            return self._sobol(
                ledger,
                n,
                fallback,
                fingerprint,
                len(entries),
                excluded,
                seed,
                started,
                warning_text,
            )
        selected = set(observed)
        actions: list[EvaluationAction] = []
        for offset in range(n):
            invalid_reason = ""
            for attempt in range(self.candidate_retry_limit):
                try:
                    candidate = self._candidate(
                        model,
                        prepared[0],
                        outcome_order,
                        assignments,
                        seed + offset * self.candidate_retry_limit + attempt,
                    )
                    config = self._decode_candidate(candidate)
                    key = _canonical_config(config)
                    if key in selected:
                        raise ValueError("candidate_duplicate")
                    selected.add(key)
                    actions.append(
                        replace(
                            self._action(next_index + offset, config), suggested_by="system:bayes"
                        )
                    )
                    break
                except Exception as error:
                    invalid_reason = f"{type(error).__name__}: {error}"
            else:
                fallback.append(
                    f"candidate_invalidation_after_{self.candidate_retry_limit}_retries: {invalid_reason}"
                )
                return self._sobol(
                    ledger,
                    n,
                    fallback,
                    fingerprint,
                    len(entries),
                    excluded,
                    seed,
                    started,
                    warning_text,
                )

        details: dict[str, JSONValue] = {
            "ledger_entries": len(entries),
            "usable_observations": len(prepared[0]),
            "excluded": excluded,
            "outcome_order": outcome_order,
            "dtype": "torch.float64",
            "deterministic_seed": seed,
            "noise_mode": self.spec.noise.mode,
            "acquisition": "qLogNoisyExpectedImprovement",
            "mixed_assignments": len(assignments),
            **fit_details,
        }
        self._remember(
            fingerprint,
            len(entries),
            BackendDiagnostics(
                backend=self.name,
                fit_state="fitted",
                fallback_reasons=tuple(fallback),
                warnings=tuple(warning_text),
                optimizer_seconds=time.perf_counter() - started,
                details=details,
            ),
        )
        return tuple(actions)

    def diagnostics(self, ledger: ObservationLedger) -> BackendDiagnostics:
        """Return fit information only if it belongs to this precise ledger snapshot."""
        entries = ledger.entries()
        fingerprint = self._fingerprint(entries)
        if self._last_diagnostics is not None and fingerprint == self._last_fingerprint:
            return self._last_diagnostics
        return BackendDiagnostics(
            backend=self.name,
            fit_state="not_fit_for_ledger",
            details={"ledger_entries": len(entries), "ledger_fingerprint": fingerprint},
        )

    def recommend(self, ledger: ObservationLedger):
        """Validate the replay boundary before ranking observed feasible points."""
        self._next_index_and_observed(ledger)
        return super().recommend(ledger)

    def state_dict(self) -> dict[str, JSONValue]:
        """Return stable JSON state; models are intentionally replayed from the ledger."""
        diagnostics = self._last_diagnostics
        return {
            "schema_version": _SCHEMA_VERSION,
            "name": self.name,
            "study_seed": self.spec.seed,
            "encoded_dimension": self.space.encoded_dimension,
            "constructor": {
                "min_initial": self.min_initial,
                "num_restarts": self.num_restarts,
                "raw_samples": self.raw_samples,
                "max_categorical_assignments": self.max_categorical_assignments,
                "candidate_retry_limit": self.candidate_retry_limit,
            },
            "last_ledger_fingerprint": self._last_fingerprint,
            "last_ledger_count": self._last_count,
            "last_fit": {} if diagnostics is None else diagnostics.to_dict(),
        }

    def _observations(self, entries):
        required = (self.spec.objective.outcome,) + tuple(
            item.outcome for item in self.spec.constraints
        )
        # Duplicate outcome names would otherwise cause an ambiguous ModelList output index.
        required = tuple(dict.fromkeys(required))
        excluded = {"non_success": 0, "incomplete_success": 0, "scientific_infeasible": 0}
        rows: list[tuple[tuple[float, ...], tuple[float, ...], tuple[float, ...] | None]] = []
        known_gap = False
        for action, result in entries:
            if action.scope is not EvaluationScope.SYSTEM:
                raise ValueError(f"ledger action must have system scope: {action.id!r}")
            if result.status is EvaluationStatus.SCIENTIFIC_INFEASIBLE:
                excluded["scientific_infeasible"] += 1
                continue
            if result.status is not EvaluationStatus.SUCCESS:
                excluded["non_success"] += 1
                continue
            if any(name not in result.outcomes for name in required):
                excluded["incomplete_success"] += 1
                continue
            errors = None
            if self.spec.noise.mode == "known":
                if any(name not in result.standard_errors for name in required):
                    known_gap = True
                    excluded["incomplete_success"] += 1
                    continue
                errors = tuple(float(result.standard_errors[name]) for name in required)
            rows.append(
                (
                    self.space.encode(action.config),
                    tuple(result.outcomes[name] for name in required),
                    errors,
                )
            )
        # Aggregate exact replicas: means are stable and known errors combine as independent SEs.
        grouped: dict[
            tuple[float, ...], list[tuple[tuple[float, ...], tuple[float, ...] | None]]
        ] = {}
        for x, y, errors in rows:
            grouped.setdefault(x, []).append((y, errors))
        x_rows, y_rows, var_rows = [], [], []
        floor = max(self.spec.noise.noise_floor, _MACHINE_NOISE_FLOOR)
        for x in sorted(grouped):
            group = grouped[x]
            y_rows.append(
                tuple(
                    float(np.mean([row[0][index] for row in group]))
                    for index in range(len(required))
                )
            )
            x_rows.append(x)
            if self.spec.noise.mode == "deterministic":
                var_rows.append(tuple(floor**2 for _ in required))
            elif self.spec.noise.mode == "known":
                var_rows.append(
                    tuple(
                        max(math.sqrt(sum(row[1][index] ** 2 for row in group)) / len(group), floor)
                        ** 2
                        for index in range(len(required))
                    )
                )
        x_tensor = torch.tensor(x_rows, dtype=torch.double)
        y_tensor = torch.tensor(y_rows, dtype=torch.double)
        var_tensor = (
            None
            if self.spec.noise.mode == "learned"
            else torch.tensor(var_rows, dtype=torch.double)
        )
        return (x_tensor, y_tensor, var_tensor, required), excluded, known_gap

    def _fit(self, train_x, train_y, train_yvar, outcome_order):
        models = []
        for index in range(train_y.shape[-1]):
            yvar = None if train_yvar is None else train_yvar[:, index : index + 1]
            models.append(
                SingleTaskGP(
                    train_x,
                    train_y[:, index : index + 1],
                    train_Yvar=yvar,
                    outcome_transform=Standardize(m=1),
                )
            )
        model = ModelListGP(*models)
        mll = SumMarginalLogLikelihood(model.likelihood, model)
        fit_gpytorch_mll(mll)
        model.eval()
        details: dict[str, JSONValue] = {
            "fit_objective": self._finite(
                float(mll(model(*model.train_inputs), model.train_targets))
            ),
            "models": tuple(self._model_summary(item) for item in models),
        }
        return model, outcome_order, details

    def _candidate(self, model, train_x, outcome_order, assignments, seed):
        torch.manual_seed(seed)
        objective_index = outcome_order.index(self.spec.objective.outcome)
        sign = 1.0 if self.spec.objective.direction == "maximize" else -1.0
        objective = GenericMCObjective(lambda samples, X=None: sign * samples[..., objective_index])
        constraints = []
        for constraint in self.spec.constraints:
            index = outcome_order.index(constraint.outcome)
            if constraint.operator == ">=":
                constraints.append(
                    lambda samples, index=index, threshold=constraint.threshold: (
                        threshold - samples[..., index]
                    )
                )
            else:
                constraints.append(
                    lambda samples, index=index, threshold=constraint.threshold: (
                        samples[..., index] - threshold
                    )
                )
        acq = qLogNoisyExpectedImprovement(
            model=model,
            X_baseline=train_x,
            objective=objective,
            constraints=constraints or None,
            prune_baseline=False,
        )
        bounds = torch.stack(
            (
                torch.zeros(self.space.encoded_dimension, dtype=torch.double),
                torch.ones(self.space.encoded_dimension, dtype=torch.double),
            )
        )
        candidate, _ = optimize_acqf_mixed(
            acq_function=acq,
            bounds=bounds,
            q=1,
            num_restarts=self.num_restarts,
            raw_samples=self.raw_samples,
            fixed_features_list=assignments,
            options={"batch_limit": 5, "maxiter": 100},
        )
        if not torch.isfinite(candidate).all():
            raise ValueError("nonfinite_candidate")
        return candidate.detach().reshape(-1).to(dtype=torch.double)

    def _fixed_assignments(self) -> list[dict[int, float]]:
        categorical = [
            (index, parameter)
            for index, parameter in self._parameter_positions()
            if isinstance(parameter, CategoricalParameter)
        ]
        choices = [parameter.categories for _, parameter in categorical]
        assignments = []
        for values in product(*choices) if choices else [()]:
            config = {
                parameter.name: value
                for (_, parameter), value in zip(categorical, values, strict=True)
            }
            fixed: dict[int, float] = {}
            for position, parameter in self._parameter_positions():
                if isinstance(parameter, CategoricalParameter):
                    index = next(
                        index
                        for index, category in enumerate(parameter.categories)
                        if type(category) is type(config[parameter.name])
                        and category == config[parameter.name]
                    )
                    fixed[position] = index / max(len(parameter.categories) - 1, 1)
                elif parameter.active_when:
                    active = self.space._is_active(parameter, config)
                    fixed[position + 1] = 1.0 if active else 0.0
                    if not active:
                        fixed[position] = 0.5
            assignments.append(fixed)
        return assignments

    def _parameter_positions(self):
        position = 0
        for parameter in self.space.parameters:
            yield position, parameter
            position += (
                2
                if isinstance(parameter, (ContinuousParameter, IntegerParameter))
                and parameter.active_when
                else 1
            )

    def _decode_candidate(self, candidate) -> dict[str, object]:
        values = candidate.clamp(0.0, 1.0).tolist()
        config: dict[str, object] = {}
        for position, parameter in self._parameter_positions():
            if isinstance(parameter, CategoricalParameter):
                config[parameter.name] = self.space._decode_category(
                    parameter, float(values[position])
                )
                continue
            active = self.space._is_active(parameter, config)
            if parameter.active_when:
                values[position + 1] = 1.0 if active else 0.0
                if not active:
                    values[position] = 0.5
                    continue
            if active:
                config[parameter.name] = self.space._denormalize(parameter, float(values[position]))
        # This final round trip is the authoritative validation and integer projection.
        return self.space.decode(tuple(float(item) for item in values))

    def _sobol(self, ledger, n, reasons, fingerprint, count, excluded, seed, started, warning_text):
        actions = SobolBackend(self.spec, self.space).suggest(ledger, n)
        actions = tuple(replace(action, suggested_by="system:sobol") for action in actions)
        self._remember(
            fingerprint,
            count,
            BackendDiagnostics(
                backend=self.name,
                fit_state="fallback",
                fallback_reasons=tuple(reasons),
                warnings=tuple(warning_text),
                optimizer_seconds=time.perf_counter() - started,
                details={
                    "ledger_entries": count,
                    "usable_observations": 0,
                    "excluded": excluded,
                    "deterministic_seed": seed,
                    "noise_mode": self.spec.noise.mode,
                    "acquisition": "qLogNoisyExpectedImprovement",
                },
            ),
        )
        return actions

    def _model_summary(self, model) -> dict[str, JSONValue]:
        parameters = {
            name: self._finite(float(value.detach().reshape(-1)[0]))
            for name, value in model.named_parameters()
            if value.numel() > 0
        }
        train_x = model.train_inputs[0]
        try:
            covariance = model.covar_module(train_x).evaluate().detach()
            condition = self._finite(float(torch.linalg.cond(covariance)))
        except Exception:
            condition = "nonfinite"
        return {"parameters": parameters, "condition_number": condition}

    @staticmethod
    def _finite(value: float) -> JSONValue:
        return value if math.isfinite(value) else "nonfinite"

    @staticmethod
    def _fingerprint(entries) -> str:
        payload = [
            {"action": action.to_dict(), "result": result.to_dict()} for action, result in entries
        ]
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()

    def _remember(self, fingerprint, count, diagnostics):
        self._last_fingerprint = fingerprint
        self._last_count = count
        self._last_diagnostics = diagnostics
