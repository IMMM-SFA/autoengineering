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

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: 778cd7724ada1edda36b5b78e0df9f89bb595b4a781ebef54eda7ade4aff1342
- Ledger hash: 7e1e9fcd550c30d1b4de2eb702d35134d844564cff28eac63c939e69a582c677

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
