# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000008
- Configuration: {"heat_loss":19.34224258994512,"loss":0.6885614575252591,"temperature":"ross"}
- Objective and constraint observations: {"rmse":176.3887911981306}
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
- Manifest study hash: de3ca0d55aaff1d043043213789eddab6ab84a9604232d16972e9ae808c7e2a7
- Ledger hash: cea4725103155ba60a750f425c3ff36b9b1e5acab795a32141a3227592895fdb

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
