# Optimization study

## Recommendation

- Feasible: True
- Action: eval-002544
- Configuration: {"alpha":0.5881827755954547,"beta":0.48907784890751854,"cmax":443.40640764291567,"kfast":0.4909240257090652,"kslow":0.0017367221739119408,"pet":"hamon","pet_scale":1.2878918458741233}
- Objective and constraint observations: {"rmse":1.1958123894572963}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 10000.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: max_cost
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: 35c5e2a2104fc0bc269b9c5732888a50358eb14fda899361ef71d12500eef4ce
- Ledger hash: 7be1e36b45f212d01f1f3b23bf155509de3fe4e99af1be1100937e8b6a234ea9

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
