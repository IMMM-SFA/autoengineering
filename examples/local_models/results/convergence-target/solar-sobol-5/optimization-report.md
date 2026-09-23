# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000003
- Configuration: {"heat_loss":40.118017424829304,"loss":0.6426604761276394,"temperature":"ross"}
- Objective and constraint observations: {"rmse":176.71567679731896}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 4.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: not_terminal
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: abf777bf957e0c15a33176105b628e60680ebd2aba243bd6efc31926a6680da3
- Ledger hash: 382373166aa887f47123c5c2398e4001c335bde26823f0013fd3d86c6e116957

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
