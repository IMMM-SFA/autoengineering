# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000066
- Configuration: {"model":"rational3","ridge":1.4534515005981296e-07}
- Objective and constraint observations: {"rmse":0.19597453888695862}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 96.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: max_cost
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: cd5bd3bce82d1bb0e4724c5118be952554ff694ffb64b7cd56f42094fe3ea484
- Ledger hash: b002bb4f63d55b45c0dbd92d5ec195b564b2ab72657703abe32459dd84d8762b

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
