# Optimization study

## Recommendation

- Feasible: True
- Action: eval-002661
- Configuration: {"alpha":0.3206909159198403,"beta":0.37590057365596297,"cmax":406.8079116122632,"kfast":0.49661318585276604,"kslow":0.0013997054050883374,"pet":"hamon","pet_scale":0.5351597853004932}
- Objective and constraint observations: {"rmse":1.1989601714710547}
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
- Manifest study hash: e59c339c16dc34595675307ce9d9be20ed64b160587cae16479f7799e9c87e6c
- Ledger hash: aeda835ac5d7e3e8cd599b89df33b633c0d15fce7226d848e6bbec1c18278992

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
