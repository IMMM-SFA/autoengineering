# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000061
- Configuration: {"alpha":0.3507965015030398,"beta":0.45642731155638777,"cmax":931.7544124394874,"kfast":0.5053542683828116,"kslow":0.08284274750660481,"pet":"hamon","pet_scale":1.0247121000972252}
- Objective and constraint observations: {"rmse":1.423232259285698}
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
- Manifest study hash: 30038dc83f3fffa119de9d41499d17dadfc9e9cd737eeb8a2825e38da82c7790
- Ledger hash: 4fa460139e576a2d37a1cdd65e6e5ec06a2f515c4883c41f840b400744a4f200

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
