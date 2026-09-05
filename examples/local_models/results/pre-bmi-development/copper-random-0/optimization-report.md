# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000000
- Configuration: {"model":"rational3","ridge":7.735831408549065e-07}
- Objective and constraint observations: {"rmse":0.19629171006005017}
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
- Manifest study hash: 3a3d17005aaa026b62653964c92b55804191aeead8129eb2e915b99abad85ebb
- Ledger hash: ed0a4d7624b64a0c864baf734dfc97e7ac6909f596d478c6bd851034ed2d83b1

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
