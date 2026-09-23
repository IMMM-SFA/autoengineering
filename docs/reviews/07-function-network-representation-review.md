# Item 7 review: function-network representation

_Review date: 2026-09-04_

_Implementation revision: `63cbdca`_

_Evidence revision: `1eccf3c`_

## Scope

This review covers the immutable function-network schema, validation against `System`, system and
component evaluation, NPZ trace verification, component training-table reconstruction, the checked
example, public imports, and Release A regression evidence. It does not review a component
surrogate or acquisition policy because those begin in Item 8.

## Representation and validation

The schema records component names and entry points, local typed parameters, ports, scalar
reducers, observation scopes, expected costs, couplings, terminal outcomes, and permitted
evaluation scopes. JSON and YAML readers require exact fields, and YAML loading rejects duplicate
keys. Every nested collection is copied into a tuple or read-only mapping.

Validation requires an exact component and coupling match with `System`. It rejects duplicate
ownership, unknown or missing components, unmatched ports, cycles, incompatible declared types or
units, invalid runnable parameters, out-of-domain action values, inconsistent cost units, invalid
observation scopes, and terminal outcomes that are not observable during system evaluation. Every
coupling source port must provide at least one system-observable scalar feature so training input
reconstruction cannot omit a coupling silently.

## Evaluation and replay

`FunctionNetworkEvaluator` delegates execution and safe NPZ publication to the existing evaluator.
System actions record all declared system-observable features and terminal outcomes. Component
actions require declared scope and earlier parent artifacts, and record only that component's
observable outputs. Action parameters must match their owner, category, active state, and numeric
bounds before evaluation.

Component trace artifacts include the actual named inputs used as well as the outputs. This is
needed because explicit source arrays can override values in a parent artifact. Replay uses the
captured input arrays, not an inferred parent value. It verifies each file digest, ZIP and NPY
structure, member count, expanded size, object dtype, and array name before loading with pickle
disabled.

Fresh ledger readers produced equal immutable training tables. Each row contains local parameters,
upstream scalar features, scalar outputs, measured action cost, scope, and all current and parent
artifact hashes. Arrays remain in NPZ files and are not copied into JSONL.

## Findings corrected during review

1. Publicly exporting the evaluator initially introduced an import cycle when
   `autoengineering.research` was imported before `autoengineering.optimization`. Runner imports are
   now delayed until evaluator construction or execution, and both import orders have subprocess
   regression tests.
2. The first evaluator check accepted declared parameter names without checking category values,
   active states, or numeric bounds. The final contract validates the complete local parameter
   domain and matches choice categories to registered evaluator alternatives.
3. Component replay initially inferred coupling inputs from parent artifacts. That was wrong when a
   source array overrode a parent value. Component NPZ files now capture the actual inputs, and a
   regression test reconstructs the override rather than the older parent value.
4. A coupling could initially reference a port without a scalar feature. Validation now requires a
   system-observable scalar output for every coupling source port.

No completion defect remains after these corrections.

## Verification

The development worktree at `1eccf3c` passed:

| Check | Result |
| --- | --- |
| `pixi run lint` | Passed |
| `pixi run test` | 404 passed, 23 skipped |
| `pixi run -e bayes test-bayes` | 426 passed, 1 skipped, 5 upstream warnings |
| `pixi run -e bayes benchmark-release-a` | Passed |
| Focused function-network and research tests | 107 passed |
| Base dependency isolation | Passed in both public import orders |

The Release A matrix was rerun from clean implementation revision `63cbdca`. It completed all 750
runs and passed every frozen criterion. All 7,500 timing-excluded scientific records matched the
two preceding Item 7 reruns and the earlier Release A evidence. The report was unchanged. Commit
`1eccf3c` binds the checked raw records, summary, and gate to the final Item 7 source hash.

## Limits retained for later items

- The first representation describes one concrete runnable entry point per component. A declared
  choice may select parameter presets registered by the evaluator, but this version does not
  serialize several function implementations under one component.
- Only declared scalar reducers become surrogate features. Arrays remain durable traces and are not
  surrogate targets.
- A system action's measured cost is repeated on its component training rows as action provenance.
  Those repeated values must not be summed as component costs.
- Evaluation is sequential. The representation does not fit surrogates, propagate posterior
  samples, optimize an acquisition function, or make partial-observation decisions.

## Result

Item 7 passes its completion gate at `1eccf3c`. The function network validates, serializes,
evaluates, and replays without a surrogate backend. Identical durable observations reconstruct
identical component training tables. Item 8 can now define and preregister numerical criteria for
full-observability function-network Bayesian optimization.
