# Campaign agent-contract-fixture

Synthetic scalar orchestration fixture

Scientific specification: `60f579e436679dfe8a773036c64856961a8b532d740df5b74cfeeffaf0a7e09e`

Outcome: `accepted_candidate`.
Confirmation: `confirmation_not_attempted`.

Physical attempts: 2. Confirmed: 2. Unresolved: 0.
Reserved or consumed capacity: 2/64.
Measured cost: 2. Cost uncertainty: False.
Charged active time: 2.87178 seconds.

## Evaluations

| Evaluation | Split | Execution | RMSE | Checks |
| --- | --- | --- | --- | --- |
| evaluation-attempt-000001-comparison | comparison | success | 1.0 | finite: pass |
| evaluation-attempt-000002-comparison | comparison | success | 0.0 | finite: pass |

## Decisions

- Comparator `evaluation-attempt-000001-comparison`: `accepted_candidate`. Selection: `evaluation-attempt-000002-comparison`.
  - Applied frozen eligibility and ranking rules
- Comparator `evaluation-attempt-000001-comparison`: `accepted_candidate`. Selection: `evaluation-attempt-000002-comparison`.
  - Applied frozen eligibility and ranking rules

## Admission

- `response-linear-v2`: admitted.

[Immutable evaluation and check records](../../artifacts/7817e364b517763a81b788969b38f62dcd80c78a7a4146a8ff4f981d22263db5/state.json).


## Immutable output evidence

- [evaluation-attempt-000001-comparison: output](../../artifacts/880293e562978f9bf21af6a684b55cf7e78c28aea2149d790bdb338c21bd74c8/outputs.npz), SHA-256 `880293e562978f9bf21af6a684b55cf7e78c28aea2149d790bdb338c21bd74c8`.
- [evaluation-attempt-000002-comparison: output](../../artifacts/c10da64ff241a5ec33d59fdd984dcd231f7e17a1ff00a32f56a0e7e3d40a3bcc/outputs.npz), SHA-256 `c10da64ff241a5ec33d59fdd984dcd231f7e17a1ff00a32f56a0e7e3d40a3bcc`.

## Limits

This experimental local workflow evaluates supplied trusted implementations. Process separation provides lifecycle control and is not a security sandbox. Token ceilings, production agent roles, new host integrations, automatic model training, and general scientific improvement remain deferred.

Exposed development data do not establish independent confirmation. Unknown costs and unavailable checks remain explicit. This report requires no private observation reads or network access.
