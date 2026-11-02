# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000000
- Configuration: {"x_0":425454.5505110463,"x_1":425850.9975430798,"x_2":424212.5639511142,"x_3":424096.8670999361,"y_0":6150562.162934162,"y_1":6150100.036469616,"y_2":6150769.381878659,"y_3":6150339.425178535}
- Objective and constraint observations: {"annual_energy":37.14054878357185}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 1.0
- Evaluator seconds: 2.075369874946773
- Optimizer overhead seconds: 0.0
- Stop reason: max_cost
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: 85bec2f997940e6a6b3e2eb0f0a32d4adcdfeee1421895f05b490b809d48ca03
- Ledger hash: 88307435cc76ad354631ef3b41cb98b8ae715222f78a38f84d657d16c8e80b7b

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
