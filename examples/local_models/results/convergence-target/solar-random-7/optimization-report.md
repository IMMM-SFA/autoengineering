# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000001
- Configuration: {"heat_loss":20.036725994295793,"loss":0.6850939799837074,"temperature":"ross"}
- Objective and constraint observations: {"rmse":176.34383678929535}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 2.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: not_terminal
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: 7cd542348d446d53ec88f9268d2086e56424b421940a28304013749cfd0ee6d1
- Ledger hash: b701214434af545f8c8d0966793c4a0d755e348c2fdc5d6d16bf3b85259706f1

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
