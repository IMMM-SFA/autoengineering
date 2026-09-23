# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000009
- Configuration: {"model":"rational3","ridge":1.6822844249512906e-07}
- Objective and constraint observations: {"rmse":0.19597569307340712}
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
- Manifest study hash: e4534f768d0089996acad7fc19e61ced9e478f86547a6c4b7f3c324de8b69053
- Ledger hash: a98aded8d31453b826f1a523578f0c652c7c963f96f6e0707e7230acde0217a0

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
