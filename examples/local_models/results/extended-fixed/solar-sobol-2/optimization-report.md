# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000019
- Configuration: {"heat_loss":57.52073303796351,"loss":0.6393077123444527,"temperature":"ambient"}
- Objective and constraint observations: {"rmse":175.25841792389534}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 24.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: max_cost
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: ee4630a675994400cad6b9339da02b15a7a238bba682760cde04ac855e944f2e
- Ledger hash: 7e1610015a5e103448f5f9cc64d3b0663b2ea06f097135fbd28f1e732d036407

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
