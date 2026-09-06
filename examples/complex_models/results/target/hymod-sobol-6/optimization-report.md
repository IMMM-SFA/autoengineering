# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000061
- Configuration: {"alpha":0.4224113333038985,"beta":2.6389784967526793,"cmax":599.1632941215194,"kfast":0.4957501575350761,"kslow":0.0012993074189879103,"pet":"hamon","pet_scale":1.0488553270697594}
- Objective and constraint observations: {"rmse":1.3171970197416365}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 200.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: max_cost
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: f7c55bc95020eac3c3f567e230009ebafae2a2ffe176364a02ba5d9b27cd1fee
- Ledger hash: 4fc6130c962ef1945e5aa0e481af21cc71b21b1eb23186203d6a3f8142bffaa1

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
