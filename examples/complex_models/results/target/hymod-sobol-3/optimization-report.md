# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000026
- Configuration: {"alpha":0.5511494384147226,"beta":2.5743022326380016,"cmax":921.4797294166628,"kfast":0.47366453856229784,"kslow":0.0014331440056223766,"pet":"hamon","pet_scale":1.2651138082146645}
- Objective and constraint observations: {"rmse":1.3003874125223467}
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
- Manifest study hash: edbdb7c782d2b429db8013fdf83e2d7dcf3759719ef858d815fa46def3f1f6a0
- Ledger hash: 51c9c63a59855d9372609e4fc827e4c23ec4b6e2c09300343037e1bfe329d412

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
