# Decision 0007: partial-observability function-network benchmark

_Status: Accepted before benchmark execution_

_Date: 2026-09-04_

_Core implementation revision: `55717867c405dd72c153ab76427b4ce64537fbec`_

## Decision

Item 9 uses the problems, seeds, budgets, policies, and acceptance criteria below. They are frozen
before the first full comparison. Failed runs and unfavorable results will remain in the evidence.
Numeric limits will not change after comparison records exist.

All objectives are maximized and have an analytic optimum of 1. Normalized regret is
`min(1, max(0, 1 - best feasible observed system objective))`. Regret remains 1 until the first
feasible system result. Regret area integrates the incumbent regret over measured evaluator cost
and divides by the run budget. Component results never update the incumbent.

## Problems

The benchmark uses two deterministic, acyclic scalar-output function networks. Every numeric
parameter has the closed interval `[0, 1]`. Tunable components also have the single categorical
choice `base` so the declared alternative contract remains exercised.

1. `informative_chain` connects a constant source to `upstream`, then connects `upstream` to
   `terminal`. The upstream output is `signal = sin(pi * x)`. The terminal output is
   `utility = 1 - (signal - 0.8)^2 - 0.2 * (y - 0.3)^2`. Feasibility requires `signal >= 0.4`.
   The upstream component costs 0.2 and the terminal component costs 0.8 evaluation units. The
   exact optima use `y = 0.3` and either solution of `sin(pi * x) = 0.8`.
2. `informative_branch` connects a constant source independently to `left` and `right`, then
   connects both branches to `terminal`. The branch outputs are `left = x` and `right = y`. The
   terminal output is
   `utility = 1 - (left - 0.65)^2 - 0.02 * (right - 0.5)^2 - 0.2 * (z - 0.25)^2`.
   Feasibility requires `left + 0.1 * right >= 0.65`. The exact feasible optimum is 1 at
   `(x, y, z) = (0.65, 0.5, 0.25)`. The left and right components cost 0.15 each and the terminal
   component costs 0.70 evaluation units. The left branch is the controlled informative branch;
   the right branch is the controlled low-value branch.

Every complete system evaluation costs exactly the sum of its component costs, which is one
evaluation unit. Component actions use one trace from an earlier successful complete system
evaluation. Direct component-to-component artifact chaining is not permitted.

## Methods, seeds, and budgets

The comparison includes:

1. `function_network_full`, the Item 8 system-only function-network backend;
2. `function_network_partial`, the one-step value-of-information policy;
3. `function_network_partial_random`, the deterministic random mixed-scope control; and
4. `function_network_partial_cheapest_informative`, the propagated variance-reduction control.

Benchmark seeds are the integers 0 through 4. The study seed is `40,000 + benchmark seed`. Each
problem and seed uses the same first four complete configurations and observations for every
method. Warm configurations come from one seeded scrambled Sobol sequence and are recorded with
the neutral label `shared_warm_start`.

Every run has an eight-unit evaluator-cost budget and a hard limit of 12 actions. The full-network
method uses `min_initial=4`, 16 acquisition candidates, 64 posterior samples, and two fit attempts.
All partial methods use `min_initial=4`, `min_component_observations=3`, two action-pool points,
four decision-pool points, 16 posterior samples, four fantasies, two fit attempts, a maximum
component streak of two, a cost quantile of 0.9, and a zero threshold for value divided by cost.

Every post-warm suggestion is replayed from a fresh backend and evaluator view against the same
ledger before evaluation. Replay equality excludes optimizer and evaluator timing but includes
scope, component, local configuration, parent IDs, action seed, selection label, outcomes, status,
cost, artifact IDs, and artifact digests.

The matrix contains 40 runs. Evaluation counts may differ because the policies spend the same cost
budget through actions with different costs. The evidence must state exact system and component
counts rather than forcing an equal evaluation count.

## One-step value calculation

The partial policy uses the finite-pool one-step knowledge-gradient definition frozen in the Item 9
implementation plan. It holds fitted hyperparameters fixed, conditions only the selected
component's observable Gaussian-process outputs, and uses exact Gaussian conditioning. The outer
expectation uses four deterministic fantasies. The inner constrained improvement uses 16
deterministic posterior samples over the same four complete decision configurations for every
fantasy.

The method follows the one-step knowledge-gradient utility of Frazier, Powell, and Dayanik (2008),
<https://doi.org/10.1137/070693424>. Applying it to component observations and using these finite
Monte Carlo pools are repository-specific choices.

## Frozen comparison criteria

The gate passes only when every condition below passes separately.

1. All 40 runs reach a declared budget, action-limit, or marginal-value stop without an invalid
   transition, lineage error, nonfinite value, or measured-cost overrun.
2. Raw actions, results, costs, incumbent histories, normalized regrets, regret areas, component
   counts, parent relationships, trace digests, and summaries reconstruct exactly.
3. Every post-warm action and result replay byte identically from fresh policy and evaluator
   instances after timing fields are removed.
4. Every component parent is an artifact from an earlier successful system action and contains all
   direct upstream ports required by that component. No component artifact is used as a parent.
5. Every run includes at least one post-warm complete system evaluation and ends with a feasible
   recommendation that references an observed complete system result.
6. On `informative_branch`, the value-of-information policy selects `left` more often than `right`
   across the five seeds. This count excludes warm and system-refresh actions.
7. The pooled median final normalized regret for the value-of-information policy is no more than
   0.15 above the system-only method. On either problem it is no more than 0.25 above the
   system-only method.
8. The pooled median normalized regret area per evaluator cost for the value-of-information policy
   is no more than 0.15 above the system-only method.
9. The value-of-information median regret area is at least 0.005 lower than the random mixed-scope
   control on at least one problem and no more than 0.10 higher on the other problem.
10. Every recorded conservative action-cost estimate is at least the realized cost. Any exceedance
    fails this criterion and remains in the evidence.
11. Fit or scoring fallbacks affect at most 10 percent of value-of-information post-warm decisions
    and at most 20 percent on either problem. Planned warm starts and the two-action system refresh
    rule are not fallbacks.
12. Component-only observations contain no terminal objective or constraint outcome names. Every
    terminal recommendation and incumbent update comes only from a successful complete system
    result.

The limits test whether partial observations retain useful decision quality under equal evaluator
cost. They do not require dominance over the full-network method. A null or adverse result keeps
the partial backend experimental and stops Item 10.

## Evidence and provenance

The benchmark will publish canonical raw JSONL records, run summaries, component-selection
summaries, value and cost diagnostics, `gate.json`, and a concise report under
`benchmarks/partial_network/results/`. Derived files must reconstruct from raw records without
modifying them. Trace files may remain outside the published result only when their verified IDs
and SHA-256 digests remain in raw evidence. Publication must be atomic to an absent directory.

Execution requires a clean signed Git revision. The execution manifest will bind this decision
hash, all benchmark source hashes added after this decision, the signed execution revision, lock
files, Python and package versions, and platform information.

The core aggregate source hash at the revision above is
`dfb503f26143c764774615b743197913abc88e199c66968c9c7a1ff3d22e1282`. It is the SHA-256 of the
ordered `shasum -a 256` lines listed below.

| Source | SHA-256 |
| --- | --- |
| `pixi.lock` | `2a14a7a6c4c74870ee2820028f69140151e80efb897a825c8e3359c4e2d82fd5` |
| `pixi.toml` | `3f4b1488f360aced5f79e3f38305ac05eed4ac6ed6eef5ffc384915a0e570868` |
| `pyproject.toml` | `50367045d7d43a42adb4a2d4ca90b5c9d642ed7babe512ac6a62800c194a2ca9` |
| `src/autoengineering/optimization/backend.py` | `db127fa7ae4a11adb3ee0bead65df198d74a1c445c707c0f89a00642b75f6d13` |
| `src/autoengineering/optimization/controller.py` | `f5a8cf2b543ce527e19093e12ce439fd0e3464ae8ffcdb53898e4dfa61a97da7` |
| `src/autoengineering/optimization/full_network_backend.py` | `54a18de88064d3d28666b11d33d2d1e9814a6f215e98f963dbdf062f90279a5e` |
| `src/autoengineering/optimization/function_network.py` | `b076160c472aa6aeb9ddd33d06aa53badbf115764c27d57825463b1ca50f4376` |
| `src/autoengineering/optimization/function_network_evaluator.py` | `ca31c606c62173c96cc28ae3768a422c002c0aea6603cdeae47706ddfb4c9ef4` |
| `src/autoengineering/optimization/ledger.py` | `e137064014cc337a0643cc76b3cf7f4adc5772ca920ed5cd8c078310b3dbda63` |
| `src/autoengineering/optimization/partial_network_backend.py` | `6a30e8ada24e820bbf23a2f944303a8aaa302d4edcef503a9c4b25ba4f3f9d62` |
| `src/autoengineering/optimization/partial_network_baselines.py` | `5080a99bf13cbaefb79a8f86fdb2a82906df2fd73bfa53d018be20ab8b867c15` |
| `src/autoengineering/optimization/records.py` | `47f92d0c169c4026f813b5a8b58522e550eb4510c43f767351b6cd1de0ed8425` |
| `src/autoengineering/optimization/space.py` | `7b8ebfb55ae072ea2e82f57a3f8ff00c6895be4bd4adc9d8bbc6ef4fc7e54652` |
| `src/autoengineering/optimization/spec.py` | `87df5c77ed379718fa547add64233c02ff9551cde21426be23c7a7a6d46a597e` |
| `src/autoengineering/research/runner.py` | `3c56db99d10bb90f5230e5c197a82721df00a4a454830755e8d9598735821fec` |
| `tests/test_function_network.py` | `7057f3f58968d4ba1db090022d5287878825a0538e611b313d3de6aa7fe96f3c` |
| `tests/test_full_network_backend.py` | `a762f13c11d7fdc4a80278688bab81c26a3afb6a74f8c54e37926fcc72fce84a` |
| `tests/test_optimization_recovery.py` | `03e2c89a36230f6f0e2c10d32be9e12627c19e8a64f94bfff4290338a4fa6aaf` |
| `tests/test_optimization_system.py` | `e2244c482e98fc815722766ee0d49e00487962e09c0801ab75d8b63f65ef369d` |
| `tests/test_partial_network_backend.py` | `2648888ec7bd3b9974e7483d6b590e42bbdda86b9b01883de89764293ba94a37` |
