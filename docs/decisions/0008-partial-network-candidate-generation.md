# Decision 0008: partial-network candidate generation correction

_Status: Accepted before correction implementation and benchmark execution_

_Date: 2026-09-04_

_Approved implementation plan revision: `3bca01f4c4e8249cef5e7eae1306dfb3f1a2c758`_

_Retained implementation revision: `449c0bcfec5338b9a2b2c4657f66570010d3a0bb`_

## Decision

Item 9 receives one bounded candidate-generation correction. All three partial methods will use 16
complete action candidates instead of two. Sixteen matches the full-network comparator fixed in
[Decision 0007](0007-partial-network-benchmark.md). No result was inspected at another partial
candidate-pool size.

The correction retains the system-refresh reservation and common antithetic fantasy sampler from
the strongest prior implementation. It changes only
`PARTIAL_SETTINGS["candidate_pool_size"]` in the benchmark runner. It does not change the
partial-network backend or the scientific gate.

All other settings remain fixed:

- `min_initial=4`;
- `min_component_observations=3`;
- `decision_pool_size=4`;
- `posterior_samples=16`;
- `fantasy_samples=4`;
- `fit_retry_limit=2`;
- `max_component_streak=2`;
- `minimum_value_per_cost=0.0`; and
- `cost_quantile=0.9`.

The full-network method retains 16 acquisition candidates, 64 posterior samples, four shared warm
observations, and two fit attempts.

## Fixed benchmark contract

The problems, analytic objectives, feasibility conditions, methods, seeds, shared warm starts,
study seed mapping, cost budget, action limit, replay contract, regret definitions, and
recommendation rules remain those in Decision 0007. Each problem-method-seed matrix contains 40
runs. Benchmark seeds remain integers 0 through 4, study seeds remain `40000 + benchmark seed`, the
evaluator-cost budget remains eight units, and the action limit remains 12.

The development matrix must use one clean signed revision and the fixed command:

```text
pixi run -e bayes bash autoresearch-candidate-generation.sh development
```

The command must publish to an absent
`benchmarks/partial_network/candidate-generation/development/` directory. Scientific gate failure
is a completed experiment, not an execution failure. Existing evidence must not be replaced or
edited.

If and only if the development matrix passes every criterion, one replacement matrix may run from
the same source revision and settings with:

```text
pixi run -e bayes bash autoresearch-candidate-generation.sh replacement
```

The replacement command must publish to an absent
`benchmarks/partial_network/candidate-generation/replacement/` directory. No additional
candidate-pool size, seed, sampler, threshold, or policy change is authorized.

## Unchanged comparison criteria

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

The text above is copied unchanged from Decision 0007.

## Run limit and decision rule

This extension permits at most two full 40-run matrices:

1. one development matrix; and
2. one replacement matrix only after a complete development pass.

A failed development matrix ends the extension. Its evidence remains committed, Item 9 remains
experimental, and Item 10 remains blocked. A passing development matrix is necessary but does not
complete Item 9. Both matrices must pass every criterion before Item 9 can complete.

Do not use benchmark-seed preflights. Structural tests may exercise reduced fixtures or
nonbenchmark seeds when they do not reveal benchmark performance.

## Existing adverse evidence

The original result and all four remediation iterations remain immutable. The directory digest is
the SHA-256 of the sorted `shasum -a 256` lines for every regular file in that directory.

| Evidence | Raw JSONL SHA-256 | Directory SHA-256 |
| --- | --- | --- |
| `benchmarks/partial_network/results/` | `7e4deb4da6369384942ee224e6c113ea806ea2e21c4d04fd8deab6e58e0a9a9f` | `0fc37dcb4cff2d356fc73bd1fddb5a933b4ba7ebe31f443aef02727b68f71734` |
| `iteration-01` | `826612e3a64683cae5fcea8cdd1c7cce80e863c9253620da2c84558634616259` | `8a02ed9906935e1a2d441ae5b1c8977ebc072293d20330c83e4445a32a20cb51` |
| `iteration-02` | `0e4135ffef58135887df07d1e72c697ca33d81562d148dc09d8a96e255a91148` | `4318685db4783b350ef39ca3e86717d50f3c0c224aaa6da6e8a4fc152b943ba3` |
| `iteration-03` | `cbce58d2bd90a11f7714d3c7f8ce5cd43077a456524860fd6b5895200925188d` | `bdafc4f437d92847e661481230e0d192d8a3e515d7642132afa2da74121d1d23` |
| `iteration-04` | `0181885d54852b3e24632495f11a93b840fc5a8d1313a5bf6b9fe89d1f0fe39b` | `f4fdbf94ef755bbff81415e0f361633ae5b62395a36b6f6d0994c5626cdfa07e` |

Iteration 03 is the retained scientific baseline. It passes 11 of 12 criteria. Its partial and
random median regret areas are equal on both problems, so it fails only
`random_component_control`.

## Pre-change source inventory

The retained implementation has benchmark source aggregate SHA-256
`81bfd30f3f2cfd721c89b83fe78882e83f17085878777cf174e03cc85f3e5c7b` at the signed proposal
revision. The aggregate uses the path-and-content algorithm implemented by
`source_hash()` in the partial-network benchmark.

| Source | SHA-256 |
| --- | --- |
| `pixi.lock` | `2a14a7a6c4c74870ee2820028f69140151e80efb897a825c8e3359c4e2d82fd5` |
| `pixi.toml` | `580cda494db2678fa08ef08b3d383a0911f0696535e3a3b04dc25a90ad6241af` |
| `pyproject.toml` | `50367045d7d43a42adb4a2d4ca90b5c9d642ed7babe512ac6a62800c194a2ca9` |
| `src/autoengineering/benchmarks/partial_network/__init__.py` | `d9d515b2f1eda223057a4bbe9885c573de033ae63fd3d3b9b5bbb19dbc318d98` |
| `src/autoengineering/benchmarks/partial_network/__main__.py` | `7431325523fdea9e8dae0e4c6c6149dc89d6db41f00775055d558b39aeae2f98` |
| `src/autoengineering/benchmarks/partial_network/problems.py` | `a86e7e515fc6e8eec791ef46b7c5e8c813e8da90f9e1becfbf96da56ce117228` |
| `src/autoengineering/benchmarks/partial_network/runner.py` | `289f6910b5beddf97dd452afc6b85cc4053ceff4fad10bcc63c0924539d33037` |
| `src/autoengineering/benchmarks/partial_network/summary.py` | `efb059ec576d108bc940238965eb465ca79f9185ac2d603d29b70829c0e25bf9` |
| `src/autoengineering/optimization/backend.py` | `db127fa7ae4a11adb3ee0bead65df198d74a1c445c707c0f89a00642b75f6d13` |
| `src/autoengineering/optimization/controller.py` | `25f4b079cc6b52550a6d8f68c36f99dddf87b07ee1f486e0b632f8c2525de83c` |
| `src/autoengineering/optimization/full_network_backend.py` | `54a18de88064d3d28666b11d33d2d1e9814a6f215e98f963dbdf062f90279a5e` |
| `src/autoengineering/optimization/function_network.py` | `b076160c472aa6aeb9ddd33d06aa53badbf115764c27d57825463b1ca50f4376` |
| `src/autoengineering/optimization/function_network_evaluator.py` | `ca31c606c62173c96cc28ae3768a422c002c0aea6603cdeae47706ddfb4c9ef4` |
| `src/autoengineering/optimization/ledger.py` | `e137064014cc337a0643cc76b3cf7f4adc5772ca920ed5cd8c078310b3dbda63` |
| `src/autoengineering/optimization/partial_network_backend.py` | `c44fca67a208578d4d1b2b07b0a257dc142fe1f516135b639003f43bf816adab` |
| `src/autoengineering/optimization/partial_network_baselines.py` | `5080a99bf13cbaefb79a8f86fdb2a82906df2fd73bfa53d018be20ab8b867c15` |
| `src/autoengineering/optimization/records.py` | `47f92d0c169c4026f813b5a8b58522e550eb4510c43f767351b6cd1de0ed8425` |
| `src/autoengineering/optimization/space.py` | `7b8ebfb55ae072ea2e82f57a3f8ff00c6895be4bd4adc9d8bbc6ef4fc7e54652` |
| `src/autoengineering/optimization/spec.py` | `87df5c77ed379718fa547add64233c02ff9551cde21426be23c7a7a6d46a597e` |
| `src/autoengineering/research/runner.py` | `3c56db99d10bb90f5230e5c197a82721df00a4a454830755e8d9598735821fec` |

## Provenance requirements

The ordinary benchmark gate remains bound to Decision 0007 because its criteria are unchanged.
Each extension run must also record a companion manifest containing the Decision 0008 SHA-256,
the signed execution revision, the benchmark source aggregate and individual source hashes, the
environment and package versions, the fixed command, the evidence directory digest, and the raw
JSONL SHA-256. The companion manifest must be committed with the immutable evidence.

The development and replacement manifests must identify their role. A replacement manifest must
also record the passing development evidence digest and execution revision that authorized it.
