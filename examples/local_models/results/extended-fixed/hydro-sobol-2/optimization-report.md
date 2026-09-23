# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000021
- Configuration: {"capacity":171.2779064103961,"pet":"hargreaves","recession":0.8969658822752535}
- Objective and constraint observations: {"rmse":2.4836531747465003}
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
- Manifest study hash: 32a6d69efa06f9ba925c5442fb5e17cc3da54b7db97a94cf00228a6f4b485520
- Ledger hash: ccc07a9ac661742d200522799cd5e77b2133278c60926027b4339724f7255403

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
