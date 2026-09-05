# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000031
- Configuration: {"alpha":0.6922077903524041,"beta":0.2342432226985693,"cmax":910.4031020596807,"kfast":0.44167027771472933,"kslow":0.11426679530826983,"pet":"hamon","pet_scale":1.0945291509851813}
- Objective and constraint observations: {"rmse":1.3656028831592404}
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
- Manifest study hash: 56e3196ed60d2cf779d295c4961ba418231ac30d74668d1d24234dee4bc93c8e
- Ledger hash: f9e8d51a588e15cfda969e3f6dc8e999579d7598675bbc2d5d9283c08ec60ea8

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
