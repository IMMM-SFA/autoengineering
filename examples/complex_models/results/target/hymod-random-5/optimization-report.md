# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000066
- Configuration: {"alpha":0.3758419678901642,"beta":0.825107084621523,"cmax":456.55122396334997,"kfast":0.4514804240605411,"kslow":0.008691988042093387,"pet":"hargreaves","pet_scale":1.087483990841083}
- Objective and constraint observations: {"rmse":1.3847820869966863}
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
- Manifest study hash: 6bd6811df3036e99519388176d2909e2468200878d23646464139c697da646df
- Ledger hash: 9b0eaeb229b6a011f6dd2aff2f301d81248ca8a59cc538b2eb70c7dbe266d395

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
