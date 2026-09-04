# Decision 0003: full-observability function-network benchmark

_Status: Accepted before benchmark execution_

_Date: 2026-09-04_

_Implementation revision: `532ccb46103866bac7382a30451c65f9ee9d2acb`_

## Decision

Item 8 uses the problems, seeds, budgets, calibration checks, and comparison criteria below. They
are frozen before the first full benchmark run. Failed runs and unfavorable results will remain in
the evidence. Numeric limits will not change after results exist.

All objectives are maximized. Normalized regret is
`min(1, max(0, (1 - best feasible objective) / 1))`. Regret is 1 until the first feasible result.
Regret area integrates the incumbent regret over the ten unit-cost evaluations and divides by 10.

## Problems

The benchmark uses two deterministic scalar-output function networks. Every tunable numeric
parameter has the closed interval `[0, 1]`. Every tunable component also has the single categorical
choice `base`, which exercises the declared alternative contract without changing the function.

1. `smooth_chain` connects a constant source to `warp`, then connects `warp` to `terminal`.
   `warp` emits `sin(pi * x)`. `terminal` emits
   `utility = 1 - (warp - 0.7)^2 - (y - 0.3)^2`. The exact optimum is 1. The component costs are
   0.45 and 0.55 evaluation units.
2. `constrained_branch` connects a constant source to `left` and `right`, then connects both
   branches to `terminal`. The branches emit `left = x` and `right = y^2`. The terminal outputs are
   `utility = 1 - (left - 0.7)^2 - (right - 0.25)^2` and `balance = left + right`. Feasibility
   requires `balance >= 0.8`. The exact feasible optimum is 1 at `x = 0.7` and `y = 0.5`. Component
   costs are 0.3, 0.3, and 0.4 evaluation units.

Each complete system evaluation costs exactly one evaluation unit. Each run has a budget and hard
limit of ten complete system evaluations. Invalid configurations, non-system actions, trace
verification errors, and budget overruns fail the run.

## Methods and seeds

The benchmark compares `SystemBayesBackend` with `FullNetworkBayesBackend`. Benchmark seeds are the
integers 0 through 9. The study seed is `10,000 + benchmark seed`.

Both methods receive the same first four configurations and observations from the seeded scrambled
Sobol sequence. They then make six sequential suggestions. `SystemBayesBackend` uses its existing
defaults with `min_initial=4`. `FullNetworkBayesBackend` uses `min_initial=4`, 64 acquisition
candidates, 128 posterior samples, and two bounded fit attempts. Every suggestion is replayed from
a fresh backend against the same ledger before evaluation. Timing is excluded from replay equality.

The full matrix contains 40 runs, 400 complete system evaluations, and 240 post-warm acquisition
records.

## Calibration

For each problem and seed, the full-network backend fits to the four shared warm observations and
predicts 16 deterministic held-out Sobol configurations with 256 posterior samples. This produces
320 held-out objective records and 160 constraint probability records.

The gate requires finite predictive moments, nonnegative variance, pooled 90 percent objective
interval coverage from 0.75 through 1.00, and pooled constraint-probability Brier score at most
0.20. These checks are separate and none substitutes for another.

The affine unit fixture uses 65,536 samples. Terminal mean absolute error must be at most 0.02,
terminal variance absolute error at most 0.03, and terminal constraint probability absolute error
at most 0.02. Repeated samples from fresh instances must be byte identical.

## Comparison criteria

The gate passes only when all conditions hold:

1. All 40 runs complete with exactly 400 evaluation and 240 acquisition records.
2. All configurations, outcomes, costs, incumbents, regrets, trace digests, indices, and shared warm
   starts reconstruct from raw evidence without error.
3. Every action has system scope, remains within budget, and replays from a fresh backend.
4. The calibration criteria above pass.
5. The pooled full-network median final regret is no more than 0.05 above the whole-system median.
6. On each problem, the full-network median final regret is no more than 0.10 above the
   whole-system median.
7. The pooled full-network median regret area is no more than 0.05 above the whole-system median.
8. Unresolved full-network fallbacks affect at most 5 percent of the 120 post-warm suggestions and
   at most 15 percent on either problem.

These limits test matching performance. They do not require the network method to dominate. A null
or adverse result remains reportable evidence and keeps the backend experimental.

## Evidence and provenance

The benchmark writes canonical `raw-records.jsonl`, `run-summary.csv`, `calibration.json`,
`gate.json`, and `report.md` files. Derived files reconstruct from the raw evaluation, acquisition,
and calibration records. Trace files remain temporary, but their verified SHA-256 digests are
retained in raw records. Publication is atomic to an absent output directory. Verification never
changes existing evidence.

Execution requires a clean Git checkout and records the signed Git revision, this decision hash,
source hash, platform, Python version, lock files, and package versions. The aggregate source hash
at the implementation revision is
`835808eabad46d0e5f1f1c5dbf737d16c501ebc5cf8ec0179dee574e0ddab001`.

The exact source file hashes are:

| Source | SHA-256 |
| --- | --- |
| `pixi.lock` | `2a14a7a6c4c74870ee2820028f69140151e80efb897a825c8e3359c4e2d82fd5` |
| `pixi.toml` | `3f4b1488f360aced5f79e3f38305ac05eed4ac6ed6eef5ffc384915a0e570868` |
| `pyproject.toml` | `50367045d7d43a42adb4a2d4ca90b5c9d642ed7babe512ac6a62800c194a2ca9` |
| `src/autoengineering/benchmarks/full_network/__init__.py` | `6c00c1757a15bd7faf1e01bd5740a0a47274c27df32312301aca7165843a8b4c` |
| `src/autoengineering/benchmarks/full_network/__main__.py` | `1545af837e7e9f95a3c673f67a7b163e1fc092e462ed671cd25443f1bebe5849` |
| `src/autoengineering/benchmarks/full_network/problems.py` | `75096a0e87774fa6c6ce3a1c88e33ad164b0101d640400ef8146c87a7545a9b3` |
| `src/autoengineering/benchmarks/full_network/runner.py` | `92e287727594dca1447d73aefe8d32e153540f4033a3241b6c7fd3c5a14b2d3d` |
| `src/autoengineering/benchmarks/full_network/summary.py` | `32056a29d91eaa6b2d4c4788c2111bf60cadc4905d4d31eb052804d318ad0144` |
| `src/autoengineering/optimization/backend.py` | `50ef7eed714678b6b5b9cde4e8aa47d2d28de45bd3d8e64944e8ca1a41e1a7a9` |
| `src/autoengineering/optimization/full_network_backend.py` | `534af0a576a4c4052859d6cfc8a3b061e897b9a21b15f615d3accd57238415b5` |
| `src/autoengineering/optimization/function_network.py` | `b076160c472aa6aeb9ddd33d06aa53badbf115764c27d57825463b1ca50f4376` |
| `src/autoengineering/optimization/function_network_evaluator.py` | `9ffbc1b4d35d39c55982c2cd91034223aeb7852030bb891b4ab11a05085bec15` |
| `src/autoengineering/optimization/ledger.py` | `e137064014cc337a0643cc76b3cf7f4adc5772ca920ed5cd8c078310b3dbda63` |
| `src/autoengineering/optimization/records.py` | `47f92d0c169c4026f813b5a8b58522e550eb4510c43f767351b6cd1de0ed8425` |
| `src/autoengineering/optimization/space.py` | `7b8ebfb55ae072ea2e82f57a3f8ff00c6895be4bd4adc9d8bbc6ef4fc7e54652` |
| `src/autoengineering/optimization/spec.py` | `87df5c77ed379718fa547add64233c02ff9551cde21426be23c7a7a6d46a597e` |
| `src/autoengineering/optimization/system_backend.py` | `d24a83776010691d425b9aabfd6b3abf03e44423396796ea434c45a75624d0cf` |
| `src/autoengineering/research/runner.py` | `3c56db99d10bb90f5230e5c197a82721df00a4a454830755e8d9598735821fec` |
