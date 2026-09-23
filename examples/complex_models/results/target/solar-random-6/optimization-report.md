# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000002
- Configuration: {"heat_loss":19.160690071275805,"loss":0.699674258292322,"temperature":"ross"}
- Objective and constraint observations: {"rmse":176.5593466847721}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 3.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: not_terminal
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: 45e15b3508af348e016f69dc68935b610ea5a3ca4e0d984976c1cb2fd6f74bf0
- Ledger hash: e06596f951d3121d7a852d3504e5f566f1f4f2795b37569771fa28be46a62aeb

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
