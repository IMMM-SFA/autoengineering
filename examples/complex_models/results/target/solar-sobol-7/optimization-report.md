# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000003
- Configuration: {"heat_loss":23.65127205848694,"loss":0.6594991609454155,"temperature":"ross"}
- Objective and constraint observations: {"rmse":176.8924972331747}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 4.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: not_terminal
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: 8fb3832c756d67742192ce14fc2bf22562aa0d33f83753a4254c9c92fc8fb9ae
- Ledger hash: 3f181fcdf235388bc557db8878dab8a7c35fcce22711867d68e83c71481243da

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
