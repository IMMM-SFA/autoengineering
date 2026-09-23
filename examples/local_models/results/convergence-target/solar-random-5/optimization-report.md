# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000010
- Configuration: {"heat_loss":58.01165594986735,"loss":0.6797804110318388,"temperature":"ambient"}
- Objective and constraint observations: {"rmse":176.71562050793068}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 11.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: not_terminal
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: ea17affe0c41633f2de2289ad5265377daa305b0153e7a4ea97691e0aed6f7a3
- Ledger hash: 6d0d1892f552b558c9dbda8fd85f0aa14d808538a728b201234651f9d8652334

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
