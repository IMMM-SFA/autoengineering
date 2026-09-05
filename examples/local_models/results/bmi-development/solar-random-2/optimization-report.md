# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000008
- Configuration: {"heat_loss":19.34224258994512,"loss":0.6885614575252591,"temperature":"ross"}
- Objective and constraint observations: {"rmse":176.3887911981306}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 12.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: max_cost
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: 398bf3d8a59db1718fe7c417992c67ee8c062fe41cdeebe7d407bd27cf7d3f5f
- Ledger hash: 033b58e8c475340c8127f40ca6274a1ee4534e30b506a723fbc1d5aa2cffaaaf

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
