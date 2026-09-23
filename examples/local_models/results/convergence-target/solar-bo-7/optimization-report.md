# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000003
- Configuration: {"heat_loss":23.65127205848694,"loss":0.6594991609454155,"temperature":"ross"}
- Objective and constraint observations: {"rmse":176.8924972331747}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 4.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: not_terminal
- Resume pending actions: 0

## Diagnostics

- Fallback events: []
- Warnings: []
- Manifest study hash: 5dacae100ce1d18a0cd7fa489f10e3c1c17cf0ea26e94381cceba6243f3fe17f
- Ledger hash: 64a4417fa8d15d0dbceb35f5aecd43f3c2e1ed2ee6d4d9650c78e987eab8b206

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
