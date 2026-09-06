# Bayesian optimization status

_Status reviewed against revision `16f730e`, 2026-09-05._

Whole-system BO is implemented and has passing Release A evidence. Full-observability
function-network BO has a passing research gate. Partial-observability BO remains experimental
after failed comparisons. The most recent common terminal utility experiment passed 11 of 12
criteria and did not justify a replacement matrix. The final research comparison remains blocked.

These results cover the BO layer. Autoengineering as a workflow is still a work in progress. The
[roadmap](roadmap.md) tracks the unified model DAG, harness, web app, examples, visualizations, and
broader model improvement methods.

## Implemented scope

| Layer | What exists | Evidence boundary |
| --- | --- | --- |
| Whole-system optimization | Strict run configuration, mixed and conditional spaces, random and Sobol policies, optional constrained BoTorch, budgets, ledger, recovery, and CLI. | Release A gate passes for the frozen benchmark. |
| Function-network representation | Immutable component functions, parameters, couplings, observations, costs, scopes, verified NPZ traces, and training-table replay. | Representation and evaluation are distinct from BO policy behavior. |
| Full-observability BO | Scalar component Gaussian processes, posterior propagation, and complete-system acquisition. | The frozen research gate passes. It remains outside the Release A CLI. |
| Partial-observability BO | System and component actions, parent artifact checks, mixed observation fits, and information-value policies. | Implemented, but comparison gates have not established the required benefit. |

The [optimization guide](optimization.md) documents interfaces and limits. The
[implementation plan](bayesian-optimization-plan.md), [reviews](reviews/), and
[decisions](decisions/) retain the development and acceptance history.

## Passing evidence

The [Release A report](../benchmarks/release_a/results/report.md) records 750 runs and 7,500
observations across five problems, five methods, and 30 seeds. Its frozen gate passes. This is
whole-system evidence, not evidence for automatic model-class selection or general forecast skill.

The [full-network report](../benchmarks/full_network/results/report.md) records 40 runs and 400
evaluations. Its comparison and reconstruction gates pass. Pooled coverage of 90 percent intervals
is 0.828125 against the frozen minimum of 0.75. The
[item 8 review](reviews/08-full-observability-function-network-bo-review.md) preserves corrections,
invalidated runs, and adverse iterations.

## Partial-observability results

The [original Item 9 report](../benchmarks/partial_network/results/report.md) failed two of twelve
criteria. Nine runs used an unaccepted exhaustion stop, and the policy missed the required gain
against the random component control. Subsequent investigations retained that result and their
own adverse evidence.

The latest [common terminal utility development report](../benchmarks/partial_network/common-utility/development/report.md)
records 40 completed runs and 11 passing criteria. The remaining failure is
`random_component_control`. The value policy minus random-control regret-area difference was
0.0007868264809469117 on the chain and approximately zero on the branch. Neither met the required
improvement of at least 0.005 on one problem.

The [experiment record](../autoresearch-common-utility.md) contains exact revisions, hashes, and
stop conditions. Under that protocol, development failure forbids a replacement matrix and ends
Item 9 algorithmic remediation. Item 10 remains blocked. The earlier Decision 0009 provenance
conflict remains unresolved. A documentation refresh changes none of these states.

## Verify existing evidence

```sh
pixi run -e bayes benchmark-release-a
pixi run -e bayes benchmark-full-network
pixi run -e bayes benchmark-partial-network
```

The first two commands verify passing checked evidence. The partial-network command reconstructs
the original failed gate and is expected to exit nonzero. It does not verify or replace the later
common utility development matrix. Use the experiment record for that matrix's provenance.

Historical software checks are recorded in the reviews. They are not fresh test results for every
later revision. Run current checks before claiming that a changed checkout passes.

## What this means for the workflow

The graph and function-network records provide part of the proposed model DAG. Runnable adapters
and evaluators provide part of the proposed harness. The workflow still needs those contracts
connected across research, execution, training, optimization, and visualization.

BO surrogates guide search. They do not provide automatic statistical, ML, or deep surrogate model
replacement. The [model improvement guide](model-improvement.md) proposes how to decide which of
those methods is worth implementing and testing.
