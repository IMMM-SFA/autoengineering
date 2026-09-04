# Item 9 candidate-generation extension

_Approved: 2026-09-04_

## Target

Pass every unchanged criterion in Decision 0007 using the single candidate-generation correction
accepted in Decision 0008. Preserve the original result and all four prior remediation matrices.

The primary metric is the value-of-information policy minus random-control median normalized
regret area on each problem. Lower is better. At least one difference must be at most `-0.005`, and
the other must be at most `0.10`. Every other frozen criterion must also pass.

## Fixed run contract

- Development command: `pixi run -e bayes bash autoresearch-candidate-generation.sh development`
- Conditional replacement command:
  `pixi run -e bayes bash autoresearch-candidate-generation.sh replacement`
- Environment: local isolated worktree and locked Pixi `bayes` environment
- Loop: linear
- Maximum full matrices: one development matrix and one replacement matrix
- Replacement rule: run only after every development criterion passes
- Seeds: benchmark seeds 0 through 4 and study seed `40000 + benchmark seed`
- RNG: scrambled Sobol pools and SHA256-derived NumPy and Torch seeds recorded by the backend
- Candidate correction: 16 action-pool points for all three partial methods
- Retained settings: four decision points, 16 posterior samples, four common antithetic fantasies,
  and the Decision 0007 budgets, policies, and thresholds

The controller publishes each standard evidence directory atomically and writes a sibling
companion manifest. It treats scientific gate failure as a completed experiment and never replaces
an existing artifact.

## Owned files

- `autoresearch-candidate-generation.md`
- `autoresearch-candidate-generation.jsonl`
- `autoresearch-candidate-generation.sh`
- new evidence under `benchmarks/partial_network/candidate-generation/`
- Item 9 documentation only after a passing replacement

Decision 0007, the original result, and all existing remediation iterations are immutable.

## Baseline

Iteration 03 at revision `5c88a1e08742065913262bf51117ef150b5555a5` is the retained baseline. It
passes 11 of 12 criteria. The partial and random-control median regret areas are equal on both
problems, so `random_component_control` fails.

- Evidence: `benchmarks/partial_network/iterations/item9-remediation/iteration-03/`
- Raw SHA-256: `cbce58d2bd90a11f7714d3c7f8ce5cd43077a456524860fd6b5895200925188d`
- Chain difference: `0.0`
- Branch difference: approximately `0.0`
- Controlled branch selections: left 2, right 0

## Hypothesis

The two-point partial action pool provides inadequate candidate coverage. Expanding it to the
full-network comparator's fixed 16 points should expose complete actions and component probes that
improve the observed terminal incumbent under the unchanged cost budget. Applying the same pool to
all partial controls preserves action availability across the comparison.

## Current state

- Full matrices used: 1
- Development matrix: complete with an adverse result
- Replacement matrix: not authorized because development failed
- Extension: stopped by the Decision 0008 decision rule
- Item 9: experimental
- Item 10: blocked by Item 9

## Development outcome

The 40-run development matrix fails `controlled_informative_component` and
`random_component_control`. The other 10 criteria pass. All runs complete, all raw records
reconstruct, replay is deterministic, every lineage and cost check passes, all 40 recommendations
reference observed complete-system results, and no value-policy fit or scoring fallback occurs.

The value policy selects no component action on either problem. On `informative_branch`, this gives
zero controlled `left` selections and zero `right` selections, so the required `left > right`
comparison fails.

The value policy improves median regret area over the random control by `0.0014498890245697449` on
`informative_chain` and `0.00029282913842992864` on `informative_branch`. Neither reaches the frozen
`0.005` improvement. Candidate coverage therefore does not support the preregistered hypothesis.

- Evidence: `benchmarks/partial_network/candidate-generation/development/`
- Companion manifest: `benchmarks/partial_network/candidate-generation/development-manifest.json`
- Signed execution revision: `280d18d37404b545c41c7fcd78ea3f544ca183ee`
- Source SHA-256: `dba69119ec36a50422c443d11e8ec498327e455d86056c4f062d13de8fff6146`
- Raw SHA-256: `198dafa67de72e8936d1d47a13b5dab7735e30d242693aa2855a15ce426d359a`
- Evidence directory SHA-256: `0331414f043e17b27543faf8ca343e185ead066a4f4edccd4df4ce91363937e6`

Decision 0008 forbids the replacement matrix after this result. Item 9 remains experimental, and
Item 10 does not begin.
