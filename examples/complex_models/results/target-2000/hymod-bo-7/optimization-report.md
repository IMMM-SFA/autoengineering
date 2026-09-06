# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000312
- Configuration: {"alpha":0.3840666723408239,"beta":0.1,"cmax":188.57332692897447,"kfast":0.48707671420875054,"kslow":0.001432016306478415,"pet":"hamon","pet_scale":1.195522357039701}
- Objective and constraint observations: {"rmse":1.132346243963679}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 313.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: not_terminal
- Resume pending actions: 0

## Diagnostics

- Fallback events: []
- Warnings: []
- Manifest study hash: dcd8035b288a9343f4920768b926483274c112f13d05be66bc04300a0fafc821
- Ledger hash: 577714bd8c3bc34d2b526c4ff3668b195bdf20ffa3803539c3bf775d282ab6f6

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
