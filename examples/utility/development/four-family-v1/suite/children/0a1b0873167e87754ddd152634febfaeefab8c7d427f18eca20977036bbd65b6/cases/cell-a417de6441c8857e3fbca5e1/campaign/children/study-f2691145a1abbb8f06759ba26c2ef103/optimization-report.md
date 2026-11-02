# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000006
- Configuration: {"capacity":43.613477163016796,"recession":0.8035028984770178}
- Objective and constraint observations: {"bias":-0.34490222963472106,"correlation":0.772516084089378,"kge":0.6800056933458613,"nse":0.5747637373758041,"relative_bias":-0.18825494578343832,"rmse":2.1283521975115756}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 16.0
- Evaluator seconds: 18.26709191687405
- Optimizer overhead seconds: 0.0
- Stop reason: max_cost
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: ee60983e0ea7d116e1fe72c599cbf6178cdffc0700a02d9ba588f1561c7f3ad0
- Ledger hash: 7a63e257000cfefca7a5ff55a6a5e6bfd63bb195d52ddbcace677dc3e4e15ca8

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
