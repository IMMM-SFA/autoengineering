# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000000
- Configuration: {"model":"rational3","ridge":9.730441723600648e-07}
- Objective and constraint observations: {"rmse":0.19646264559703372}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 1.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: not_terminal
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: 3435456a100b1e30100cfc38763e4392580115a96c627959161258f17d862e9e
- Ledger hash: f37d2c8a7fe03b006e37c5b7fdebde31ddf82c36282569f2e910f900b44ad16e

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
