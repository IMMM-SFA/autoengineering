# Latest BO results review

## Summary Assessment

The September 5 common-terminal-utility development run is a valid adverse result.
It completed 40 runs and passed 11 of 12 frozen criteria, but did not establish an
advantage over random component selection. Item 9 remains experimental and Item 10
remains blocked. Decision 0010 prohibits a replacement matrix after this failure.

## Strengths

All six evidence file hashes match the companion manifest. Fresh verification
reconstructed all derived artifacts from raw records and reproduced the failed
gate without an integrity error. All runs completed, with no recorded fit or
scoring fallbacks. Recorded replay, lineage, observed recommendations, conservative
costs, and terminal-observation separation satisfy their criteria.

The common utility now permits component actions to compete: six were selected on
the chain and five on the branch. This addresses the earlier zero-selection result.

## Critical Issues

The required performance improvement is absent. The metric is the difference
between method medians of normalized regret area, value policy minus random.
Lower is better. At least one problem must reach -0.005.

| Problem | Value policy median | Random median | Difference |
| --- | ---: | ---: | ---: |
| informative_chain | 0.144653 | 0.143866 | +0.000787 |
| informative_branch | 0.279599 | 0.279599 | approximately 0 |

Neither passes. Eleven passing criteria cannot compensate for this required
criterion. The evidence supports retaining the experimental status, not promotion.
The prior decision-pool differences were -0.001450 and -0.000293. Gaining the
selection criterion therefore did not improve the primary comparison.

## Major Issues

1. The controlled-selection pass is narrow: two left selections versus one right
   selection across five seeds. This meets the frozen count rule but does not
   establish reliable identification of informative components.
2. Optimizer overhead is substantial without measured regret-area benefit. Median
   recorded overhead is 44.792 seconds on the chain and 130.278 seconds on the
   branch, versus 0.049 and 0.094 seconds for random selection. Full-network
   overhead is 0.202 and 0.315 seconds. The frozen budget measures evaluator cost,
   so these timings limit practical interpretation without changing the gate.
   These are accumulated suggestion times, not end-to-end runtimes.
3. The two synthetic problems and five seeds support a bounded development result.
   Repeated remediation uses these same benchmark seeds. There is no independent
   validation matrix for this correction and no basis for broader generalization.

## Minor Issues

The generated report lists criteria and component counts but omits the method
median table above and overhead comparison. Those numbers make the failed
scientific criterion easier to interpret. Any supplementary presentation should
preserve the frozen evidence files.

The earlier Decision 0009 candidate-generation root-digest conflict remains
unresolved as explicitly recorded in Decision 0010. It is not a newly observed
integrity failure in the current common-utility evidence.

## Reproducibility and Verification

Execution revision: `8ba5dcbf110c9a60fc486f912c95efeee7c03dee`.
Evidence reviewed at revision `16f730e` in the implementation worktree.

Fresh command:

```text
pixi run -e bayes python -m autoengineering.benchmarks.partial_network --output benchmarks/partial_network/common-utility/development
```

Exit 1 reports scientific FAIL after successful source/decision hash checks and
byte-identical reconstruction. Six companion-manifest file hashes also matched.
CSV medians were independently recomputed. No optimization experiment or fresh
action replay was run. Replay consistency is recorded execution evidence, checked
by reconstruction, rather than a fresh replay claim. Wall-clock timings were not
replicated. External novelty and literature claims were not assessed.
An independent reviewer checked the interpretation and CSV arithmetic and agreed
with the stop decision. Its qualifications on timing scope and the earlier
control comparison are incorporated above.

## Inline Annotations

- `autoresearch-common-utility.md`, Development outcome: the adverse outcome and
  stop decision agree with reconstructed evidence.
- `development/report.md`, Criteria: `controlled_informative_component` passes
  exactly as specified, with only three relevant branch selections.
- `development/report.md`, Evidence: pooled partial-minus-full final regret
  +0.004781 and regret area +0.009991 meet tolerance limits. These are small
  degradations, not evidence of superiority.
- `development/gate.json`, `random_component_control`: branch floating-point
  difference -5.55e-17 should be described as a tie, not an improvement.

## Recommendation

Accept and preserve this as the final adverse Item 9 remediation result under
Decision 0010. Do not launch the conditional replacement matrix. Keep Item 10
blocked. Further research would require a new, explicitly approved protocol and
independent evaluation design.

Earlier reports show the whole-system Release A gate passing across 750 runs and
the full-observability network matching gate passing across 40 runs. Those reports
were inspected for context, not freshly audited. The latest failure concerns the
added value of partial component evaluations and does not reverse those earlier
gates.

## Sources

- [Frozen benchmark](decisions/0007-partial-network-benchmark.md)
- [Common utility and stopping rule](decisions/0010-partial-network-common-utility.md)
- [Run record](../autoresearch-common-utility.md)
- [Current evidence](../benchmarks/partial_network/common-utility/development/report.md)
- [Current manifest](../benchmarks/partial_network/common-utility/development-manifest.json)
- [Full-network context](../benchmarks/full_network/results/report.md)
- [Release A context](../benchmarks/release_a/results/report.md)
- [Review evidence and inspected implementation paths](.drafts/latest-bo-results-review-evidence.md)
