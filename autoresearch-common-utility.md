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
- Full matrices used: 1 of at most 2
- Development matrix: complete, adverse
- Replacement matrix: forbidden because development failed
- Item 9: experimental
- Item 10: blocked by Item 9

## Development outcome

_Completed: 2026-09-05_

The development matrix completed all 40 runs at signed revision
`8ba5dcbf110c9a60fc486f912c95efeee7c03dee`. It passed 11 of 12 frozen criteria. The
`random_component_control` criterion failed.

The common utility changed mixed-scope selection. The value policy selected six component actions
on `informative_chain` and five on `informative_branch`. On the controlled branch comparison it
selected `left` twice and `right` once, so `controlled_informative_component` passed. All 40 runs
completed without an error, all raw records reconstructed, replay was deterministic, lineage and
terminal separation checks covered 90 component actions, all recommendations referenced observed
system results, conservative costs passed, and no fit or scoring fallback occurred.

The value policy minus random control regret-area difference was
`0.0007868264809469117` on `informative_chain` and approximately zero
(`-5.551115123125783e-17`) on `informative_branch`. Neither reached the required `-0.005`
improvement. Decision 0010 therefore forbids a replacement matrix and ends Item 9 algorithmic
remediation. Item 10 remains blocked.

- Evidence: `benchmarks/partial_network/common-utility/development/`
- Companion manifest: `benchmarks/partial_network/common-utility/development-manifest.json`
- Raw SHA-256: `ae2a3cf986e807ead80fd60dc13401131b04d80f89937d4a8449e1c211a59cb5`
- Evidence directory SHA-256:
  `91307b916ddc6a3d6220b09cf4cd0dd1f6bb3f211cff66f3a8a77d4d7d49d585`
- Companion manifest SHA-256:
  `ee52a9dfd3c959f9df95b6720585d6181902231d54f6e2748462da008244d4f7`
- Source SHA-256: `1a537f7a845eaace0c4dc4a04c23cb4dd5710a2bebc78a1dbf1f42ea4e1050d1`
