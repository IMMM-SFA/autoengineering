# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000073
- Configuration: {"model":"rational3","ridge":1.7819233092875907e-07}
- Objective and constraint observations: {"rmse":0.1959765784379049}
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
- Manifest study hash: 1b54c201938cf11a20b7190b3ffbe6a34f693004714494ef5f5c749c1566a139
- Ledger hash: a73dad6127afd9631d6b3d9bbea08ce1c98a369154c050fb5a40698183c4abb1

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
