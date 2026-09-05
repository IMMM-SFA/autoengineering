# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000006
- Configuration: {"heat_loss":19.828992363062167,"loss":0.6495652887781519,"temperature":"ambient"}
- Objective and constraint observations: {"rmse":175.0775624702757}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 24.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: max_cost
- Resume pending actions: 0

## Diagnostics

- Fallback events: []
- Warnings: []
- Manifest study hash: 974e93e092f6c693f1d2c29eefaec219ed98b39e05a2036cc0d624c553f40f46
- Ledger hash: 5c82898b61eb2e2547319941aa5f3fb7973d7ec9bdafe990ff12ce8a0aa70b28

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
