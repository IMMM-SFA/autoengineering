# Decision 0010: common terminal utility for partial-network actions

_Status: Accepted before implementation and benchmark execution_

_Date: 2026-09-04_

_Approved implementation plan revision: `e830da85f2f23344eb9596a74adc66ba50f45da9`_

## Decision

Item 9 receives one final algorithmic correction. The partial value policy will score system and
component observations against the same terminal decision utility. This replaces the asymmetric
comparison of direct system expected improvement with incremental component information value.

For data `D`, let `s` equal `1` for maximization and `-1` for minimization. Define

```text
b(D) = best observed feasible value of s * objective

I_D(x) = E[max(s * objective(x) - b(D), 0) * 1(feasible(x)) | D]

U(D) = b(D) + max_x I_D(x)

KG(a) = E_z[U(D union {(a, z)}) | D, a] - U(D)

score(a) = max(KG(a), 0) / predicted_cost(a)
```

Every affordable system and component action uses this definition. A component fantasy conditions
only the selected component's observable scalar outputs and cannot change `b(D)`. A system fantasy
conditions every scalar component output observed at system scope. A feasible system fantasy may
update `b(D)` inside `U`; an infeasible fantasy may not. Fitted hyperparameters remain fixed during
fantasy conditioning.

The terminal decision pool remains finite. Final recommendations remain successful observed system
results. No fantasy, surrogate mean, or component result may become a terminal incumbent or
recommendation.

The backend identity and durable state will include a stable acquisition contract named
`finite_pool_common_terminal_utility_v1`. State created under the earlier asymmetric score is
incompatible and must not resume under the corrected policy.

## Fixed benchmark contract

The problems, analytic objectives, feasibility conditions, methods, seeds, shared warm starts,
study seed mapping, cost budget, action limit, replay contract, regret definitions, and
recommendation rules remain those in [Decision 0007](0007-partial-network-benchmark.md). The matrix
contains 40 problem-method-seed runs. Benchmark seeds remain integers 0 through 4, study seeds
remain `40000 + benchmark seed`, the evaluator-cost budget remains eight units, and the action
limit remains 12.

All three partial methods retain `min_initial=4`, `min_component_observations=3`,
`candidate_pool_size=16`, `decision_pool_size=16`, `posterior_samples=16`, `fantasy_samples=4`, two
fit attempts, a maximum component streak of two, cost quantile 0.9, zero value threshold, and the
system-refresh reservation. The full-network comparator retains 16 acquisition candidates, 64
posterior samples, four shared warm observations, and two fit attempts. Both mixed-scope controls
retain their existing behavior.

The development matrix must use one clean signed revision and the fixed command:

```text
pixi run -e bayes bash autoresearch-common-utility.sh development
```

The command must publish atomically to an absent
`benchmarks/partial_network/common-utility/development/` directory and write a sibling companion
manifest. Scientific gate failure is a completed experiment. Existing evidence must not be
replaced or edited.

If and only if the development matrix passes every criterion, one replacement matrix may run from
the same source and settings with:

```text
pixi run -e bayes bash autoresearch-common-utility.sh replacement
```

No other acquisition utility, pool size, sampler, threshold, seed, problem, cost, or budget may be
tested on the benchmark seeds.

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

The limits test whether partial observations retain useful decision quality under equal evaluator
cost. They do not require dominance over the full-network method. A null or adverse result keeps
the partial backend experimental and stops Item 10.

The text above is copied unchanged from Decision 0007.

## Run limit and decision rule

This correction permits at most two full 40-run matrices:

1. one development matrix; and
2. one replacement matrix only after a complete development pass.

A failed development matrix ends Item 9 algorithmic remediation. Its evidence remains committed,
Item 9 remains experimental, and Item 10 remains blocked. A passing development matrix is
necessary but does not complete Item 9. Both matrices must pass every criterion before Item 9 can
complete.

No benchmark-seed performance preflight is permitted. Structural tests may use analytic fixtures
or nonbenchmark seeds when they do not reveal benchmark performance.

## Existing evidence and provenance conflict

The original result, four bounded iterations, candidate-generation matrix, and decision-pool
matrix remain immutable. A standard evidence directory digest is the SHA-256 of the sorted
`shasum -a 256` lines for every regular file, with repository-relative paths.

| Evidence | Raw JSONL SHA-256 | Directory SHA-256 |
| --- | --- | --- |
| `benchmarks/partial_network/results/` | `7e4deb4da6369384942ee224e6c113ea806ea2e21c4d04fd8deab6e58e0a9a9f` | `0fc37dcb4cff2d356fc73bd1fddb5a933b4ba7ebe31f443aef02727b68f71734` |
| `iteration-01` | `826612e3a64683cae5fcea8cdd1c7cce80e863c9253620da2c84558634616259` | `8a02ed9906935e1a2d441ae5b1c8977ebc072293d20330c83e4445a32a20cb51` |
| `iteration-02` | `0e4135ffef58135887df07d1e72c697ca33d81562d148dc09d8a96e255a91148` | `4318685db4783b350ef39ca3e86717d50f3c0c224aaa6da6e8a4fc152b943ba3` |
| `iteration-03` | `cbce58d2bd90a11f7714d3c7f8ce5cd43077a456524860fd6b5895200925188d` | `bdafc4f437d92847e661481230e0d192d8a3e515d7642132afa2da74121d1d23` |
| `iteration-04` | `0181885d54852b3e24632495f11a93b840fc5a8d1313a5bf6b9fe89d1f0fe39b` | `f4fdbf94ef755bbff81415e0f361633ae5b62395a36b6f6d0994c5626cdfa07e` |
| `candidate-generation/development` | `198dafa67de72e8936d1d47a13b5dab7735e30d242693aa2855a15ce426d359a` | `0331414f043e17b27543faf8ca343e185ead066a4f4edccd4df4ce91363937e6` |
| `decision-pool/development` | `c2c7f20cf81d59e53ef2e06633cd16c7e195ece92aa89e34971450f5ef1accfe` | `e8d4b415e20838a46aa5f3111393f881d81b29ea286b4adc5cfd762f88a8bca0` |

The candidate-generation companion manifest has SHA-256
`17bf8719bca3b72597252d02b830be88d37e04f7b19f38871a01b9553ce2707b`. The decision-pool companion
manifest has SHA-256 `654014f5ef5b21985805c2a48706ed787bf033536f786f94d421beb399250a8b`.

Decision 0009 records
`9bbc9e00fefab89581323c8fd37c71d700682f11716e580d7dc27654e6457fa6` as the complete
candidate-generation root digest. This value cannot be reconstructed using the declared
sorted-file algorithm. Git reports no candidate-generation path change after evidence commit
`f14066d`. The standard development digest and companion manifest hash above match their committed
bytes. The reproducible complete candidate-generation root digest is
`32168e168b3b3c941ec19f560c3b9d3bf0b26ecb57c90ed751ce64ce69ce740c`. The unreproduced Decision
0009 value remains recorded as a provenance conflict rather than being repaired or omitted.

The reproducible complete decision-pool root digest is
`026821a38b82838d530c8006a0abe83f909a094e75de7d28ec11304e144c7df0`.

Decisions 0007 through 0009 have SHA-256 values
`b6e408302a4a9ab7f03f468152eb4ba3720f831e00723c1d62995ef551fbd86f`,
`c0afe0891704189a44624021b52ff8fe37396b84659661073baa9d005be21b7c`, and
`8313b0839af9cd392bc2fe793e533e93c177891cf170fd553e05b7954d4ef468`, respectively.

## Pre-change source inventory

The approved implementation-plan revision has benchmark source aggregate SHA-256
`3bace879fc84c9c35b5f10b444722399ca7ed66b41f3350fa792e1712c603330`. The aggregate uses the
path-and-content algorithm implemented by `source_hash()` in the partial-network benchmark.

| Source | SHA-256 |
| --- | --- |
| `pixi.lock` | `2a14a7a6c4c74870ee2820028f69140151e80efb897a825c8e3359c4e2d82fd5` |
| `pixi.toml` | `580cda494db2678fa08ef08b3d383a0911f0696535e3a3b04dc25a90ad6241af` |
| `pyproject.toml` | `50367045d7d43a42adb4a2d4ca90b5c9d642ed7babe512ac6a62800c194a2ca9` |
| `src/autoengineering/benchmarks/partial_network/__init__.py` | `d9d515b2f1eda223057a4bbe9885c573de033ae63fd3d3b9b5bbb19dbc318d98` |
| `src/autoengineering/benchmarks/partial_network/__main__.py` | `7431325523fdea9e8dae0e4c6c6149dc89d6db41f00775055d558b39aeae2f98` |
| `src/autoengineering/benchmarks/partial_network/problems.py` | `a86e7e515fc6e8eec791ef46b7c5e8c813e8da90f9e1becfbf96da56ce117228` |
| `src/autoengineering/benchmarks/partial_network/runner.py` | `45035273fc1b1970c45129be538c84bda651661464129a394a15be82089bd6b6` |
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

Each correction run must record a companion manifest containing Decision 0010's SHA-256, the signed
execution revision, the benchmark source aggregate and individual source hashes, environment and
package versions, fixed command, evidence directory digest, raw JSONL SHA-256, and role. A
replacement manifest must also bind the passing development evidence digest and execution
revision.
