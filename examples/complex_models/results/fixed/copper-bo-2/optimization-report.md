# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000052
- Configuration: {"model":"rational3","ridge":1.48751812845969e-07}
- Objective and constraint observations: {"rmse":0.19597463060268888}
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
- Manifest study hash: b5b03554feec785b7e39d47538ff2df4044fd9dc61f89a91948c630d43456d29
- Ledger hash: e93a3f0c54e510dc709ebfc2cc81235c5453126954f5b3bb1f026d47d2315c36

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
