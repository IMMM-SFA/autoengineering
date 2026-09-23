# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000084
- Configuration: {"alpha":0.7568869875705275,"beta":0.5917721342619573,"cmax":625.615147118107,"kfast":0.4477976750442988,"kslow":0.0019277403223551455,"pet":"hargreaves","pet_scale":1.0662999830562456}
- Objective and constraint observations: {"rmse":1.2750264367884654}
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
- Manifest study hash: 3b61b593904531828400fa9676f7d1e601332c2dd9f3820b38870ed9b48b8cc7
- Ledger hash: 064ccdcea96865fd2bba45cf2fa3ef4b88dd597e7bdf830bc24c56ae94494a27

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
