# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000087
- Configuration: {"heat_loss":20.96628459200288,"loss":0.6493498255301604,"temperature":"ambient"}
- Objective and constraint observations: {"rmse":175.07750630516097}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 96.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: max_cost
- Resume pending actions: 0

## Diagnostics

- Fallback events: []
- Warnings: []
- Manifest study hash: cba1f2bd736bad652476540a16b21d99c552305656fd422e5359747d7cd89f50
- Ledger hash: 80d6e00073eda23c56e4291bdd0ba69dd15854016f6da2e83eb596f1070ec404

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
