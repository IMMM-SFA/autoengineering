# Item 9 decision-pool extension

_Approved: 2026-09-04_

## Target

Pass every unchanged criterion in Decision 0007 using the single terminal decision-pool correction
accepted in Decision 0009. Preserve the original result and every earlier remediation matrix.

The primary metric is the value-of-information policy minus random-control median normalized
regret area on each problem. Lower is better. At least one difference must be at most `-0.005`, and
the other must be at most `0.10`. Every other frozen criterion must also pass.

## Fixed run contract

- Development command: `pixi run -e bayes bash autoresearch-decision-pool.sh development`
- Conditional replacement command:
  `pixi run -e bayes bash autoresearch-decision-pool.sh replacement`
- Environment: local isolated worktree and locked Pixi `bayes` environment
- Loop: linear
- Maximum full matrices: one development matrix and one replacement matrix
- Replacement rule: run only after every development criterion passes
- Seeds: benchmark seeds 0 through 4 and study seed `40000 + benchmark seed`
- RNG: scrambled Sobol pools and SHA256-derived NumPy and Torch seeds recorded by the backend
- Candidate resolution: 16 action-pool points for all three partial methods
- Decision correction: 16 terminal decision-pool points for all three partial methods
- Retained settings: 16 posterior samples, four common antithetic fantasies, and the Decision 0007
  budgets, policies, and thresholds

The controller publishes each standard evidence directory atomically and writes a sibling
companion manifest. It treats scientific gate failure as a completed experiment and never replaces
an existing artifact.

## Owned files

- `autoresearch-decision-pool.md`
- `autoresearch-decision-pool.jsonl`
- `autoresearch-decision-pool.sh`
- new evidence under `benchmarks/partial_network/decision-pool/`
- Item 9 documentation only after a passing replacement

Decisions 0007 through 0009 and all existing evidence are immutable.

## Baseline

The candidate-generation development matrix at revision
`280d18d37404b545c41c7fcd78ea3f544ca183ee` is the retained baseline. It passes 10 of 12
criteria. The value policy chooses no component actions and does not reach the required regret-area
improvement over random.

- Evidence: `benchmarks/partial_network/candidate-generation/development/`
- Raw SHA-256: `198dafa67de72e8936d1d47a13b5dab7735e30d242693aa2855a15ce426d359a`
- Chain difference: `-0.0014498890245697449`
- Branch difference: `-0.00029282913842992864`
- Controlled branch selections: left 0, right 0

## Hypothesis

The value policy compares direct system improvement over 16 action configurations with component
information value over only four terminal decision configurations. Expanding the terminal decision
pool to 16 should reduce this finite-pool resolution mismatch while retaining the estimator,
candidate set, costs, seeds, and selection rule.

## Current state

- Full matrices used: 1 of at most 2
- Development matrix: complete, adverse
- Replacement matrix: not authorized because development failed
- Item 9: experimental
- Item 10: blocked by Item 9

## Development result

The development matrix completed all 40 runs at signed revision
`b1147bcf293af52eedbd2eeed64ae732357a7522`. It passed 10 of 12 frozen criteria.
The failed criteria were `controlled_informative_component` and `random_component_control`.

Expanding the terminal decision pool did not cause the value policy to select either controlled
branch component. The value policy minus random-control regret-area differences were
`-0.0014498890245697726` for the chain and `-0.00029282913842992864` for the branch. Neither met
the required `-0.005` improvement. The differences are numerically unchanged from the retained
candidate-generation baseline at the reported precision.

- Evidence: `benchmarks/partial_network/decision-pool/development/`
- Companion manifest: `benchmarks/partial_network/decision-pool/development-manifest.json`
- Raw SHA-256: `c2c7f20cf81d59e53ef2e06633cd16c7e195ece92aa89e34971450f5ef1accfe`
- Evidence directory SHA-256: `e8d4b415e20838a46aa5f3111393f881d81b29ea286b4adc5cfd762f88a8bca0`
- Candidate-pool diagnostic entries: 80 at size 16
- Decision-pool diagnostic entries: 80 at size 16
- Controlled branch selections: left 0, right 0

The raw records reconstruct the same failed gate with status 1. The approved stop rule therefore
forbids the replacement matrix and any further Item 9 experiment. Item 10 remains blocked.
