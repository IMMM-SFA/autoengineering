# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000010
- Configuration: {"capacity":177.72500167844498,"pet":"hamon","recession":0.9392582745335362}
- Objective and constraint observations: {"rmse":2.3938113231570806}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 60.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: max_cost
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: c04e34891c73beea0df3e06d526d906ab852ad4f97767b4df534ff8d6aa9ab87
- Ledger hash: 57f3c6ea4dcd846d88764a19898f18a431cf5df88068a6eaf6984c5293a95474

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
