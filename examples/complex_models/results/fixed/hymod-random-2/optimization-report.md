# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000043
- Configuration: {"alpha":0.8784331555183132,"beta":1.216863957861532,"cmax":891.9475821365678,"kfast":0.41795988053056465,"kslow":0.024374425420917396,"pet":"hamon","pet_scale":1.4086350939302585}
- Objective and constraint observations: {"rmse":1.4582123271456102}
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
- Manifest study hash: 9df5d3c16814c4c2191f4d12b6f45f69f1b9211fddd6f4f3987f30c1449a0fd8
- Ledger hash: aa1d58341d9d9ae2dd0327ede3d6f6677a48c7761209dc727153fa3b2a7ee368

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
