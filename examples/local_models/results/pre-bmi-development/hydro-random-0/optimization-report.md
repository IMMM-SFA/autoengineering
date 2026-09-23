# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000007
- Configuration: {"capacity":159.8829458888144,"pet":"hargreaves","recession":0.7692523218244088}
- Objective and constraint observations: {"rmse":3.5643115938853236}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 12.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: max_cost
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: 557d34478ac3180d252d48e648abb902e182c3bb6553c92d562725065275ad6f
- Ledger hash: 956e92fff64ffe523fee5c130901df44692adc9bf99865c0e04f7254baa96c3c

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
