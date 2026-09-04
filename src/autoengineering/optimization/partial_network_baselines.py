"""Benchmark-only mixed-scope policies for partial function networks."""

from __future__ import annotations

from dataclasses import replace
from types import MappingProxyType
import time
import warnings

import numpy as np
import torch

from .backend import SearchSpaceExhausted, _parse_action_index
from .full_network_backend import _PreparedComponent
from .function_network_evaluator import reconstruct_component_training_tables
from .ledger import ObservationLedgerReader
from .partial_network_backend import PartialActionCandidate, PartialNetworkBayesBackend
from .records import BackendDiagnostics, EvaluationScope, JSONValue


class RandomPartialNetworkBackend(PartialNetworkBayesBackend):
    """Select uniformly from the same affordable mixed-scope candidate pool."""

    name = "function_network_partial_random"

    def _validate_backend_name(self) -> None:
        if self.spec.backend != "function_network_partial":
            raise ValueError("random partial baseline requires the partial study backend")

    def _suggest(self, ledger: ObservationLedgerReader, n: int = 1):
        if n != 1:
            raise ValueError("partial function-network optimization is sequential")
        started = time.perf_counter()
        entries = ledger.entries()
        self.validate_entries(entries)
        fingerprint = self._fingerprint(entries)
        pools = self._candidate_pools(ledger)
        next_index = max((_parse_action_index(action.id) for action, _ in entries), default=-1) + 1
        if self._count_initial_observations(entries) < self.min_initial:
            return self._warm_system_action(
                pools,
                next_index,
                fingerprint,
                started,
                entries,
                "random_baseline_system_warm_start",
            )
        if not self.recommend(ledger).feasible:
            return self._warm_system_action(
                pools,
                next_index,
                fingerprint,
                started,
                entries,
                "random_baseline_no_feasible_system_incumbent",
            )
        force_system = self._component_streak(entries) >= self.max_component_streak
        candidates = pools.system if force_system else (*pools.system, *pools.component)
        if not candidates:
            raise SearchSpaceExhausted("random partial baseline has no affordable action")
        ordered = tuple(sorted(candidates, key=lambda item: item.key))
        generator = np.random.default_rng(self._seed(fingerprint, "random-partial-baseline"))
        selected = ordered[int(generator.integers(0, len(ordered)))]
        self._last_fingerprint = fingerprint
        self._last_diagnostics = BackendDiagnostics(
            backend=self.name,
            fit_state="stateless_baseline",
            fallback_reasons=("benchmark random mixed-scope policy",),
            optimizer_seconds=time.perf_counter() - started,
            details={
                "ledger_entries": len(entries),
                "candidate_count": len(ordered),
                "forced_system_refresh": force_system,
                "selected_scope": selected.scope.value,
                "selected_component": selected.component,
                "estimated_cost": selected.estimated_cost,
                "seed": self._seed(fingerprint, "random-partial-baseline"),
            },
        )
        return (self._action_from_candidate(selected, next_index, "random"),)

    def identity_dict(self) -> dict[str, JSONValue]:
        identity = super().identity_dict()
        identity["name"] = self.name
        identity["candidate_policy"] = {
            "component_parents": "earlier_successful_system_artifacts",
            "component_chaining": False,
            "score": "deterministic_uniform_random",
        }
        return identity


class CheapestInformativePartialNetworkBackend(PartialNetworkBayesBackend):
    """Rank component observations by propagated variance reduction per cost."""

    name = "function_network_partial_cheapest_informative"

    def _validate_backend_name(self) -> None:
        if self.spec.backend != "function_network_partial":
            raise ValueError("informative partial baseline requires the partial study backend")

    def _suggest(self, ledger: ObservationLedgerReader, n: int = 1):
        if n != 1:
            raise ValueError("partial function-network optimization is sequential")
        started = time.perf_counter()
        entries = ledger.entries()
        self.validate_entries(entries)
        fingerprint = self._fingerprint(entries)
        pools = self._candidate_pools(ledger)
        next_index = max((_parse_action_index(action.id) for action, _ in entries), default=-1) + 1
        if self._count_initial_observations(entries) < self.min_initial:
            return self._warm_system_action(
                pools,
                next_index,
                fingerprint,
                started,
                entries,
                "informative_baseline_system_warm_start",
            )
        if not self.recommend(ledger).feasible:
            return self._warm_system_action(
                pools,
                next_index,
                fingerprint,
                started,
                entries,
                "informative_baseline_no_feasible_system_incumbent",
            )
        if self._component_streak(entries) >= self.max_component_streak or not pools.component:
            return self._warm_system_action(
                pools,
                next_index,
                fingerprint,
                started,
                entries,
                "informative_baseline_system_refresh",
            )

        tables = reconstruct_component_training_tables(self.network, self.system, ledger)
        deficient = self._deficient_components(tables)
        if deficient:
            candidates = tuple(
                candidate for candidate in pools.component if candidate.component in deficient
            )
            if not candidates:
                return self._warm_system_action(
                    pools,
                    next_index,
                    fingerprint,
                    started,
                    entries,
                    "informative_baseline_models_not_ready",
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
        except Exception as error:
            return self._warm_system_action(
                pools,
                next_index,
                fingerprint,
                started,
                entries,
                f"informative_baseline_fit_failure: {type(error).__name__}: {error}",
            )
        scores = tuple(
            self._variance_score(ledger, candidate, pools.decisions, prepared, fingerprint)
            for candidate in pools.component
        )
        selected, value, score = min(
            scores,
            key=lambda item: (-item[2], item[0].estimated_cost, item[0].key),
        )
        self._last_fingerprint = fingerprint
        self._last_diagnostics = BackendDiagnostics(
            backend=self.name,
            fit_state="fitted_baseline",
            warnings=self._warning_text(captured),
            optimizer_seconds=time.perf_counter() - started,
            details={
                "ledger_entries": len(entries),
                "candidate_count": len(scores),
                "decision_pool_size": len(pools.decisions),
                "selected_scope": selected.scope.value,
                "selected_component": selected.component,
                "estimated_cost": selected.estimated_cost,
                "propagated_variance_reduction": value,
                "variance_reduction_per_cost": score,
                "candidate_scores": tuple(
                    {
                        "component": candidate.component,
                        "parent_artifact_id": candidate.parent_artifact_id,
                        "config": dict(candidate.config),
                        "estimated_cost": candidate.estimated_cost,
                        "propagated_variance_reduction": reduction,
                        "variance_reduction_per_cost": candidate_score,
                    }
                    for candidate, reduction, candidate_score in scores
                ),
            },
        )
        return (self._action_from_candidate(selected, next_index, "cheapest_informative"),)

    def _variance_score(
        self,
        ledger: ObservationLedgerReader,
        candidate: PartialActionCandidate,
        decisions,
        prepared,
        fingerprint,
    ) -> tuple[PartialActionCandidate, float, float]:
        component_name = candidate.component or ""
        item = prepared[component_name]
        x = self._component_candidate_input(ledger, candidate, item)
        conditioned_item = self._condition_at_posterior_mean(item, x)
        conditioned = dict(prepared)
        conditioned[component_name] = conditioned_item
        conditioned = MappingProxyType(conditioned)
        reductions = []
        for config in decisions:
            before = self._propagate(
                prepared, config, fingerprint, self.posterior_sample_count
            )
            after = self._propagate(
                conditioned, config, fingerprint, self.posterior_sample_count
            )
            before_variance = float(np.var(before.objective, ddof=1)) + sum(
                float(np.var(values, ddof=1)) for values in before.constraints.values()
            )
            after_variance = float(np.var(after.objective, ddof=1)) + sum(
                float(np.var(values, ddof=1)) for values in after.constraints.values()
            )
            reductions.append(max(before_variance - after_variance, 0.0))
        value = float(np.mean(reductions))
        return candidate, value, value / candidate.estimated_cost

    def _condition_at_posterior_mean(
        self, item: _PreparedComponent, x
    ) -> _PreparedComponent:
        observable = tuple(
            output.name
            for output in item.spec.scalar_outputs
            if EvaluationScope.COMPONENT in output.observed_in
        )
        models = dict(item.models)
        noise = max(self.spec.noise.noise_floor, np.finfo(np.float64).eps) ** 2
        for output_name in observable:
            model = item.models[output_name]
            with torch.no_grad():
                y = model.posterior(x).mean.detach()
            conditioned = model.condition_on_observations(
                X=x,
                Y=y,
                noise=torch.full_like(y, noise),
            )
            conditioned.eval()
            models[output_name] = conditioned
        return replace(item, models=MappingProxyType(models))

    def identity_dict(self) -> dict[str, JSONValue]:
        identity = super().identity_dict()
        identity["name"] = self.name
        identity["candidate_policy"] = {
            "component_parents": "earlier_successful_system_artifacts",
            "component_chaining": False,
            "score": "propagated_terminal_variance_reduction_per_cost",
        }
        return identity
