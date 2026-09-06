# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000024
- Configuration: {"alpha":0.5845430463980732,"beta":0.18253006777647876,"cmax":426.41237191941406,"kfast":0.5342472806401298,"kslow":0.0012549590635535493,"pet":"hamon","pet_scale":1.2331645782164007}
- Objective and constraint observations: {"rmse":1.3155449303835993}
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
- Manifest study hash: b1ecb5269a519a9feb2d6d569c4e9c87a652f3125cb34af427cfb229741c098e
- Ledger hash: b0b647d3c5a1bf4ce4dab9365c7c0bcde105a7f521bfc971db74c38bdb4f1d53

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
