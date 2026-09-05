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

- Full matrices used: 0 of at most 2
- Development matrix: pending
- Replacement matrix: not authorized unless development passes
- Item 9: experimental
- Item 10: blocked by Item 9

