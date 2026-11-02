# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000001
- Configuration: {"source_current":0.03456821138970554}
- Objective and constraint observations: {"source_power":0.11854625333653068}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 6.0
- Evaluator seconds: 5.300993083976209
- Optimizer overhead seconds: 0.0
- Stop reason: max_cost
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: 3bee615b0626340307b8819a02643b0c3e90c82adb767bea5e569d5f520a3a6b
- Ledger hash: f624e788b877d681cb2476e89aaf065554702d1be300e900e488d419712f92e8

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
