"""Common route grants and explicit mechanical ablations precede dispatch."""
from dataclasses import replace

import pytest

from autoengineering.utility.routes import (
    ScientificGrant, HostGrant, RoleAllowance, RouteRecipe, TaskRoute, role_removals, route_specs,
    paired_matrix,
)
from test_utility_contracts import H, suite


def full():
    return RouteRecipe("multi_agent", ScientificGrant((H,), H, H, H, H, H, None),
        HostGrant(H, "scripted-development", "1", H, 20),
        tuple(RoleAllowance(role, 4, H) for role in ("orchestrator", "investigator", "implementer", "reviewer")),
        {}, H, suite().budgets[0].caps)


def test_ablations_keep_checks_grants_and_remaining_call_limits():
    recipe = full()
    variants = role_removals(recipe, {role: H for role in ("investigator", "implementer", "reviewer")})
    for variant in variants:
        assert variant.scientific_grant == recipe.scientific_grant
        assert variant.limits == recipe.limits and variant.host == recipe.host
        assert variant.scientific_acceptance == "mandatory"
        assert variant.unused_role_allowance == 8
        assert all(role.maximum_calls == 4 for role in variant.roles)
        assert RouteRecipe.from_json(variant.to_json()) == variant


def test_route_grants_match_task_and_randomized_matrix_is_reproducible():
    spec = suite()
    recipe = full()
    conventional = replace(recipe, kind="conventional", host=None, roles=())
    rows = (TaskRoute("task", "conventional", conventional), TaskRoute("task", "multi", recipe))
    routes = route_specs(spec.tasks, rows)
    cells = paired_matrix(spec.tasks, routes, spec.budgets, repetitions=10, seed=17, scenarios={"task": H})
    assert cells == paired_matrix(spec.tasks, routes, spec.budgets, repetitions=10, seed=17, scenarios={"task": H})
    assert len(cells) == 20
    assert len({c.route_id for c in cells[::2]}) == 2
    for i in range(0, 20, 2):
        assert cells[i].seed == cells[i+1].seed
        assert cells[i].pair_key == cells[i+1].pair_key
    assert replace(spec, routes=routes, cells=cells).cells == cells


def test_unequal_information_or_reallocated_aggregate_limits_reject():
    spec = suite()
    recipe = full()
    altered = replace(recipe, scientific_grant=replace(recipe.scientific_grant,
                                                       research_corpus_digest="2" * 64))
    with pytest.raises(ValueError, match="unequal scientific"):
        route_specs(spec.tasks, (TaskRoute("task", "a", recipe), TaskRoute("task", "b", altered)))
    altered = replace(recipe, limits=(replace(recipe.limits[0], limit=101), *recipe.limits[1:]))
    with pytest.raises(ValueError, match="aggregate allowances"):
        route_specs(spec.tasks, (TaskRoute("task", "a", recipe), TaskRoute("task", "b", altered)))


def test_omitted_role_requires_frozen_replacement():
    with pytest.raises(ValueError, match="mechanical replacements"):
        replace(full(), kind="no_reviewer", roles=full().roles[:-1])


def test_primary_and_ablation_recipes_form_one_paired_matrix():
    from autoengineering.utility.routes import single_agent_recipe, conventional_recipe
    spec = suite()
    recipe = full()
    variants = (conventional_recipe(recipe, numerical_recipe_digest=H),
                single_agent_recipe(recipe, prompt_digest=H, maximum_calls=16), recipe,
                *role_removals(recipe, {role: H for role in ("investigator", "implementer", "reviewer")}))
    rows = tuple(TaskRoute("task", r.kind, r) for r in variants)
    routes = route_specs(spec.tasks, rows)
    cells = paired_matrix(spec.tasks, routes, spec.budgets, repetitions=10, seed=17,
                          scenarios={"task": H})
    assert len(cells) == 60
    assert len({r.grants_digest for r in routes}) == 1
    assert len(replace(spec, routes=routes, cells=cells).child_batches()) == 2
    with pytest.raises(ValueError, match="aggregate host"):
        single_agent_recipe(recipe, prompt_digest=H, maximum_calls=21)


def test_matrix_cannot_omit_task_route_or_use_changed_host():
    spec = suite()
    recipe = full()
    altered = replace(recipe, host=replace(recipe.host, model="different-model"))
    with pytest.raises(ValueError, match="share host"):
        route_specs(spec.tasks, (TaskRoute("task", "a", recipe), TaskRoute("task", "b", altered)))
    with pytest.raises(ValueError, match="every task"):
        paired_matrix(spec.tasks, spec.routes, spec.budgets, repetitions=2, seed=17, scenarios={})


def test_route_plan_roundtrip_binds_order_seed_and_prompts():
    from autoengineering.utility.routes import RoutePlan
    plan = RoutePlan("utility-routes-v1", (TaskRoute("task", "multi", full()),), 10, 17, {"task": H})
    assert RoutePlan.from_json(plan.to_json()) == plan
    assert replace(plan, matrix_seed=18).digest != plan.digest
    changed = replace(full(), roles=(replace(full().roles[0], prompt_digest="2" * 64), *full().roles[1:]))
    assert replace(plan, task_routes=(TaskRoute("task", "multi", changed),)).digest != plan.digest
    routes, cells = plan.expand(suite().tasks, suite().budgets)
    assert len(routes) == 1 and len(cells) == 10
