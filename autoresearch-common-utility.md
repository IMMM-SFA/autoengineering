# Item 9 common terminal utility correction

_Approved: 2026-09-04_

## Target

Test the common terminal utility accepted in Decision 0010 against every unchanged Decision 0007
criterion. Preserve every earlier Item 9 result, including adverse results and the unresolved
Decision 0009 provenance conflict.

The common utility gives system and component actions the same terminal decision horizon. The
primary metric remains the value policy minus random control median normalized regret area on each
problem. Lower is better. At least one difference must be at most `-0.005`, the other must be at
most `0.10`, and every other frozen criterion must pass.

## Fixed run contract

- Development command: `pixi run -e bayes bash autoresearch-common-utility.sh development`
- Conditional replacement command:
  `pixi run -e bayes bash autoresearch-common-utility.sh replacement`
- Environment: local isolated worktree and locked Pixi `bayes` environment
- Loop: linear
- Maximum full matrices: one development matrix and one replacement matrix
- Replacement rule: run only after every development criterion passes
- Seeds: benchmark seeds 0 through 4 and study seed `40000 + benchmark seed`
- RNG: scrambled Sobol pools and SHA256 derived NumPy and Torch seeds recorded by the backend
- Partial settings: 16 action candidates, 16 terminal decisions, 16 posterior samples, and four
  common antithetic fantasies
- Acquisition contract: `finite_pool_common_terminal_utility_v1`
- Retained settings: the Decision 0007 problems, costs, budgets, methods, thresholds, and controls

The controller publishes each standard evidence directory atomically and writes a sibling
companion manifest. It treats scientific gate failure as a completed experiment and never replaces
an existing artifact.

## Owned files

- `autoresearch-common-utility.md`
- `autoresearch-common-utility.jsonl`
- `autoresearch-common-utility.sh`
- new evidence under `benchmarks/partial_network/common-utility/`
- Item 9 documentation only after a passing replacement

Decisions 0007 through 0010, earlier evidence, benchmark problems, gate reconstruction, the
full-network backend, and both control policies are immutable.

## Retained baseline

The decision-pool development matrix at revision
`b1147bcf293af52eedbd2eeed64ae732357a7522` is the immediate adverse baseline. It passed 10 of 12
criteria and failed `controlled_informative_component` and `random_component_control`.

- Evidence: `benchmarks/partial_network/decision-pool/development/`
- Raw SHA-256: `c2c7f20cf81d59e53ef2e06633cd16c7e195ece92aa89e34971450f5ef1accfe`
- Evidence directory SHA-256:
  `e8d4b415e20838a46aa5f3111393f881d81b29ea286b4adc5cfd762f88a8bca0`
- Chain difference: `-0.0014498890245697726`
- Branch difference: `-0.00029282913842992864`
- Controlled branch selections: left 0, right 0

## Hypothesis

The previous policy compared direct system expected improvement with incremental component
information value. Scoring both scopes by the expected change in the same terminal utility should
remove that horizon mismatch. The change may let informative component actions compete with system
actions without changing costs, pools, controls, or final recommendation rules.

## Current state

- Executable implementation: complete at signed revision
  `df42706e817cb61a117e7c695d4a0119c8b1e9f3`
- Full matrices used: 0 of at most 2
- Development matrix: not started
- Replacement matrix: not authorized
- Item 9: experimental
- Item 10: blocked by Item 9
