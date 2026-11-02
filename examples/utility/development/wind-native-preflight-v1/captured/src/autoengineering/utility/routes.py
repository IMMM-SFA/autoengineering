"""Shared-pool route recipes, explicit ablations and reproducible paired order."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from typing import Literal

import numpy as np

from autoengineering.campaign.serialization import Record, digest
from .contracts import ComparisonCell, ResourceCap, RouteSpec, identifier, sha256

ROLES = ("orchestrator", "investigator", "implementer", "reviewer")


@dataclass(frozen=True)
class ScientificGrant(Record):
    candidates: tuple[str, ...]
    partition_digest: str
    search_bounds_digest: str
    acceptance_digest: str
    research_corpus_digest: str
    hardware_digest: str
    training_profile_digest: str | None

    def _validate(self):
        if not self.candidates or len(set(self.candidates)) != len(self.candidates):
            raise ValueError("scientific grant needs an ordered unique candidate pool")
        for value in (*self.candidates, self.partition_digest, self.search_bounds_digest,
                      self.acceptance_digest, self.research_corpus_digest, self.hardware_digest):
            sha256(value)
        if self.training_profile_digest is not None:
            sha256(self.training_profile_digest)


@dataclass(frozen=True)
class HostGrant(Record):
    host_profile_digest: str
    model: str
    version: str
    permissions_digest: str
    aggregate_host_invocations: int

    def _validate(self):
        sha256(self.host_profile_digest)
        sha256(self.permissions_digest)
        if self.aggregate_host_invocations < 1:
            raise ValueError("agent route needs an explicit positive host-call allowance")


@dataclass(frozen=True)
class RoleAllowance(Record):
    role: Literal["orchestrator", "investigator", "implementer", "reviewer", "single_agent"]
    maximum_calls: int
    prompt_digest: str

    def _validate(self):
        sha256(self.prompt_digest)
        if self.maximum_calls < 1:
            raise ValueError("active role needs a positive declared call cap")


@dataclass(frozen=True)
class RouteRecipe(Record):
    kind: Literal["baseline", "conventional", "single_agent", "multi_agent",
                  "no_investigator", "no_implementer", "no_reviewer", "expert"]
    scientific_grant: ScientificGrant
    host: HostGrant | None
    roles: tuple[RoleAllowance, ...]
    replacements: Mapping[str, str]
    numerical_recipe_digest: str
    limits: tuple[ResourceCap, ...]
    scientific_acceptance: Literal["mandatory"] = "mandatory"

    def _validate(self):
        sha256(self.numerical_recipe_digest)
        role_names = tuple(r.role for r in self.roles)
        if len(set(role_names)) != len(role_names):
            raise ValueError("duplicate active role")
        expected = (() if self.kind in ("baseline", "conventional", "expert") else
                    ("single_agent",) if self.kind == "single_agent" else
                    tuple(role for role in ROLES if self.kind != "no_" + role))
        if role_names != expected:
            raise ValueError("active roles differ from the frozen route recipe")
        omitted = (self.kind.removeprefix("no_"),) if self.kind.startswith("no_") else ()
        if set(self.replacements) != set(omitted):
            raise ValueError("omitted roles require exactly their mechanical replacements")
        for value in self.replacements.values():
            sha256(value)
        if bool(self.roles) != (self.host is not None):
            raise ValueError("only agent routes may bind a host")
        if self.host and sum(r.maximum_calls for r in self.roles) > self.host.aggregate_host_invocations:
            raise ValueError("role calls exceed aggregate host allowance")
        if not self.limits or len({c.name for c in self.limits}) != len(self.limits):
            raise ValueError("route limits must be nonempty and unique")

    @property
    def unused_role_allowance(self):
        return (self.host.aggregate_host_invocations - sum(r.maximum_calls for r in self.roles)
                if self.host else 0)


def role_removals(full: RouteRecipe, replacements: Mapping[str, str]) -> tuple[RouteRecipe, ...]:
    """Remove one role without reallocating its allowance to the remaining roles."""
    if full.kind != "multi_agent" or set(replacements) != {"investigator", "implementer", "reviewer"}:
        raise ValueError("role removal needs a full route and three frozen mechanical replacements")
    return tuple(replace(full, kind="no_" + omitted,
                         roles=tuple(r for r in full.roles if r.role != omitted),
                         replacements={omitted: replacements[omitted]})
                 for omitted in ("investigator", "implementer", "reviewer"))


@dataclass(frozen=True)
class TaskRoute(Record):
    task_id: str
    route_id: str
    recipe: RouteRecipe

    def _validate(self):
        identifier(self.task_id)
        identifier(self.route_id)


def route_specs(tasks, task_routes: tuple[TaskRoute, ...]) -> tuple[RouteSpec, ...]:
    """Bind per-task recipes into suite-level route identities and common grants."""
    keys = [(r.task_id, r.route_id) for r in task_routes]
    if not keys or len(set(keys)) != len(keys):
        raise ValueError("task routes must be unique")
    task_map = {t.task_id: t for t in tasks}
    route_ids = tuple(dict.fromkeys(r.route_id for r in task_routes))
    if set(keys) != {(task, route) for task in task_map for route in route_ids}:
        raise ValueError("route plan must cover the complete task/route cross product")
    for task_id, task in task_map.items():
        recipes = [r.recipe for r in task_routes if r.task_id == task_id]
        if len({r.scientific_grant.digest for r in recipes}) != 1:
            raise ValueError("routes receive unequal scientific information")
        grant = recipes[0].scientific_grant
        if grant.candidates != task.candidate_digests or grant.partition_digest != task.partition_digest:
            raise ValueError("scientific grant differs from frozen task")
        adaptive = [r for r in recipes if r.kind not in ("baseline", "expert")]
        if len({digest([c.to_dict() for c in r.limits]) for r in adaptive}) > 1:
            raise ValueError("adaptive routes must share aggregate allowances")
        hosts = [r.host for r in recipes if r.host is not None]
        if len({h.digest for h in hosts}) > 1:
            raise ValueError("agent routes must share host, model, permissions and aggregate limits")
    grants_digest = digest({task: next(r.recipe.scientific_grant.digest for r in task_routes
                                      if r.task_id == task) for task in task_map})
    result = []
    for route in route_ids:
        members = [r for r in task_routes if r.route_id == route]
        if len({r.recipe.kind for r in members}) != 1:
            raise ValueError("route kind differs between tasks")
        result.append(RouteSpec(route, members[0].recipe.kind,
                                digest({r.task_id: r.recipe.digest for r in members}), grants_digest))
    return tuple(result)


def paired_matrix(tasks, routes, budgets, *, repetitions, seed, scenarios):
    """Persist randomized order and a common seed inside every repetition block."""
    if type(repetitions) is not int or repetitions < 1 or type(seed) is not int or not 0 <= seed < 2**63:
        raise ValueError("matrix requires explicit positive repetitions and a nonnegative seed")
    if set(scenarios) != {t.task_id for t in tasks}:
        raise ValueError("every task requires a pinned scenario identity")
    cells = []
    for task_index, task in enumerate(tasks):
        sha256(scenarios[task.task_id])
        for regime_index, budget in enumerate(budgets):
            for repetition in range(repetitions):
                rng = np.random.default_rng(np.random.SeedSequence([seed, task_index, regime_index, repetition]))
                paired_seed = int(rng.integers(0, 2**63-1))
                order = rng.permutation(len(routes))
                cells.extend(ComparisonCell(task.task_id, routes[int(i)].route_id, budget.regime,
                                            repetition, paired_seed, scenarios[task.task_id]) for i in order)
    return tuple(cells)


def single_agent_recipe(full: RouteRecipe, *, prompt_digest: str, maximum_calls: int) -> RouteRecipe:
    """Freeze one persona under the same information and aggregate host allowance."""
    if full.kind != "multi_agent":
        raise ValueError("single-agent construction requires the full shared-pool recipe")
    return replace(full, kind="single_agent", roles=(RoleAllowance("single_agent", maximum_calls,
                                                                  prompt_digest),), replacements={})


def conventional_recipe(full: RouteRecipe, *, numerical_recipe_digest: str) -> RouteRecipe:
    """Preserve scientific choices and numeric allowances while removing agent calls."""
    if full.kind != "multi_agent":
        raise ValueError("conventional construction requires the full shared-pool recipe")
    return replace(full, kind="conventional", host=None, roles=(), replacements={},
                   numerical_recipe_digest=numerical_recipe_digest)


@dataclass(frozen=True)
class RoutePlan(Record):
    schema: Literal["utility-routes-v1"]
    task_routes: tuple[TaskRoute, ...]
    repetitions: int
    matrix_seed: int
    scenario_digests: Mapping[str, str]

    def _validate(self):
        keys = [(r.task_id, r.route_id) for r in self.task_routes]
        if not keys or len(set(keys)) != len(keys):
            raise ValueError("route plan needs unique task/route assignments")
        if self.repetitions < 1 or not 0 <= self.matrix_seed < 2**63:
            raise ValueError("route plan needs positive repetitions and a valid seed")
        if set(self.scenario_digests) != {r.task_id for r in self.task_routes}:
            raise ValueError("route plan scenarios must cover exactly its tasks")
        for value in self.scenario_digests.values():
            sha256(value)

    def expand(self, tasks, budgets):
        routes = route_specs(tasks, self.task_routes)
        cells = paired_matrix(tasks, routes, budgets, repetitions=self.repetitions,
                              seed=self.matrix_seed, scenarios=self.scenario_digests)
        return routes, cells
