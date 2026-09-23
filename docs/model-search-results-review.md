# Model search results review

## Summary Assessment

The report supports its main distinction: reaching a development target, improving test prediction and reducing computational cost are different outcomes. No critical or major issue was found in this bounded review. The adopted pilot heuristic is consistently identified as provisional guidance, with the requested research TODO preserved.

## Strengths

- Capped studies, individual seeds and paired checkpoints remain visible.
- Validation selection and test prediction are separated. The exposed solar temporal holdout is not presented as blind external validation.
- Timing medians are not stacked, and cached versus uncached bookkeeping and concurrent-test limitations are stated.
- Wind nonconvergence and HOPP infeasibility remain explicit. The SOC screening tolerance is distinguished from the nominal operating limit.
- The 32-call pilot has an affordability exception and no claim of empirical validation. Recovery instructions prohibit policy/budget mutation and invented pilot handoffs.

## Critical Issues

None established.

## Major Issues

None established. The five problems do not validate a general method-selection rule, but the report and workflow documents already state that limitation.

## Minor Issues

1. `reports/model-search-results/scripts/build_report.py`, target-calls caption: change "dashed line" to "dotted line" to match both renderers.
2. `reports/model-search-results/report.qmd`, Reading the figures: qualify the method-color statement because runtime colors encode time components rather than search methods. Both encodings are understandable with their legends.
3. Before reusing the report builder on another matrix, assert that every non-hit stop reason is `evaluation_cap`. Its call formatting and summary currently classify all non-hits as capped. That matches the present 11 records and is not an error in this report.

## Reproducibility and Verification

Independent CSV checks passed for 75 target rows, 360 checkpoint rows, 120 timing rows and five model-cost rows against the saved source records. The report's provenance totals match 45 fixed studies, 75 target studies, 24972 retained calls, 64 target hits and 11 caps. Retrospective projection and exclusion of later observations are explicit.

The inspected build code checks recorded audit hashes, ledger hashes and 88 Markdown rows before generating seven figures. The documented sequence runs canonical evidence verification before the figure build. The first rendered HTML contains the expected summary and resolved citations.

No models, optimizers or full audit were rerun during this review. Final browser, responsive layout, dark mode, print selection, self-containment and post-edit render checks remain with the parent. This review does not certify those pending checks.

## Inline Annotations

- The working approach: retain the statement that pilot size and switching thresholds remain research questions.
- Target attainment figure: censoring markers are appropriate. Correct the line-style wording only.
- Validation/test figure: seed curves and checkpoint pairing support the interpretation. Do not add uncertainty claims from the four checkpoints.
- Runtime figure: the separate medians and unequal stopping-horizon warning are necessary and should remain.
- Complexity figure: nominal dimensions and measured cost are correctly treated as different quantities, not a learned difficulty score.
- Hybrid figure: retaining the rejected CBC bar and separate nominal/screen lines prevents a misleading revenue ranking.
- Choosing a search method: fresh initialization costs and immutable recovery identity make the provisional heuristic operationally honest.

## Recommendation

Accept the scientific content and workflow guidance, subject to the parent's final rendering and verification checks. Resolve the two small wording issues if convenient. No new experiments or revised scientific claims are required by this review.

## Sources

- [Review evidence notes](.drafts/model-search-results-review-evidence.md), including inspected paths and independent CSV checks.
- [Figure report source](../reports/model-search-results/report.qmd), [build script](../reports/model-search-results/scripts/build_report.py), and [provenance](../reports/model-search-results/provenance.json).
- [Audited source report](../examples/complex_models/results/RESULTS.md) and its fixed/target-2000 source matrices.
- [Optimization guidance](optimization.md#choosing-a-search-method), [concept](../concept.md), and [agent instructions](../.claude/agents/auto-engineer.md).
- [Saved background note](../background_research/pilot-based-selection.md) and [BibTeX](../reports/model-search-results/references.bib).
- [Frazier (2018), A Tutorial on Bayesian Optimization](https://arxiv.org/abs/1807.02811): supports the expensive-objective motivation.
- [Bergstra and Bengio (2012), Random Search for Hyper-Parameter Optimization](https://www.jmlr.org/papers/v13/bergstra12a.html): supports random-search baselines and the distinction between nominal and influential parameters.
