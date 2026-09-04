# Item 5 Release A benchmark review brief

_Prepared: 2026-09-04_

_Initial implementation revision: `5c752c7`_

## Scope

Review the item 5 decision, implementation plan, benchmark package, tests, Pixi task, and checked
results against `docs/bayesian-optimization-plan.md`. Do not review or change earlier plan items.

## Review questions

1. Do all five evaluators, seed mappings, costs, constraints, failures, and reference objectives
   match Decision 0001?
2. Are fixed, random, Sobol, SMAC, and BoTorch compared under the declared budgets and warm starts?
3. Are optional dependencies lazy, and does the base package remain importable without them?
4. Do raw records retain every evaluation and failure with accurate timing and fallback accounting?
5. Does the gate require the exact Cartesian matrix, exact native replay, bounded fallbacks, and all
   frozen numeric criteria?
6. Can raw records reproduce every derived artifact, and does provenance identify every source and
   environment input that can affect the result?
7. Can interrupted or concurrent publication replace existing evidence or discard completed work?

## Ownership and constraints

The review is read-only. The reviewer must not edit files, commit, push, use the network, or run the
full benchmark. Report findings by severity with exact file and line references. A clean final
review must state that no implementation defect remains and list residual risks.
