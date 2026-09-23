# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000094
- Configuration: {"alpha":0.6783743627369404,"beta":0.8952933293767273,"cmax":558.1659844502735,"kfast":0.4979681663215161,"kslow":0.008893861827964799,"pet":"hargreaves","pet_scale":1.3433635709807277}
- Objective and constraint observations: {"rmse":1.2513580061651486}
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
- Manifest study hash: c6e70cf302bda950cdcef6671d4366fa910565432825023dfc6ac4a8ec8a2de5
- Ledger hash: a6ad2a6f16e57944cc48b2ac5f5e8c4ee1919e6509e6bd6ae6af60cb3e43293b

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
