# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000000
- Configuration: {"source_current":0.06446459050290287}
- Objective and constraint observations: {"source_power":0.41190081812747414}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 6.0
- Evaluator seconds: 9.901623209938407
- Optimizer overhead seconds: 0.0
- Stop reason: max_cost
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: 2bdd3b3f99299d265989d196bbdbb5a82d96232e0c9889f72c22526bb727ad22
- Ledger hash: 3e47aca689baa5df1429250c32e06bd33c500c990f797ad2aa173384ea69afd5

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
