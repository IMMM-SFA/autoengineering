# Optimization study

## Recommendation

- Feasible: True
- Action: eval-001561
- Configuration: {"alpha":0.4786145178601145,"beta":1.0721720028668642,"cmax":496.05926681946545,"kfast":0.4698157012462616,"kslow":0.0011369883238145123,"pet":"hamon","pet_scale":1.3158739833161235}
- Objective and constraint observations: {"rmse":1.2428524475972256}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 2000.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: max_cost
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: 6c55f28dc81b9fd18ec86bb85ca62dd334ed1b7670740721659ea3a82c4a5734
- Ledger hash: 6314416d38818b0237786de193bea05609c139369225d6b81b52743d38be2cbd

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
