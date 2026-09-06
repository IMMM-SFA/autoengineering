# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000004
- Configuration: {"a_scale":1.17520952783525,"heat_loss":42.673377860337496,"io_scale":0.32498956034691123,"irradiance_scale":0.8522424549795687,"loss":0.6065551859792322,"rs_scale":0.803686909433495,"rsh_scale":1.0460332658848843}
- Objective and constraint observations: {"rmse":175.68712758920097}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 5.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: not_terminal
- Resume pending actions: 0

## Diagnostics

- Fallback events: []
- Warnings: []
- Manifest study hash: 09152311ca3c07909b8b2e2c1cd5c34e478aef1e40769a88ca7152034ac80dd2
- Ledger hash: 5c2f62cd06c82b2ee7cb273fc88565d9b5c97bc2430d3882ed262359debc1c22

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
