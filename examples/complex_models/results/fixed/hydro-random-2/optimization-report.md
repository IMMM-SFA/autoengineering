# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000035
- Configuration: {"capacity":76.9445861749909,"pet":"hargreaves","recession":0.9456238243416485}
- Objective and constraint observations: {"rmse":2.4971830746336123}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 96.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: max_cost
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: 0db0394ee32cc9bf661c9fc31606f4a47e9b3e88fd9f005d553b20f9554ad426
- Ledger hash: 0618c90084f5d2fa2db694c166381a518cab4270e9afbe5498f070f0d693e779

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
