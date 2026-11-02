# Campaign utility-exposed-solar

Previously exposed OEDI power reconstruction

Scientific specification: `f5f3bdeced73c2bc9f70520aeb599c836a1820a9f240ba4d02aac756ea0f074f`

Outcome: `accepted_candidate`.
Confirmation: `confirmation_not_attempted`.

Physical attempts: 15. Confirmed: 15. Unresolved: 0.
Reserved or consumed capacity: 15/18.
Measured cost: 15. Cost uncertainty: False.
Charged active time: 24.357 seconds.

## Evaluations

| Evaluation | Split | Execution | RMSE | Checks |
| --- | --- | --- | --- | --- |
| evaluation-attempt-000001-comparison | comparison | success | 142.99363734651664 | finite: pass, solar_physical: pass |
| evaluation-attempt-000002-comparison | comparison | success | 139.8092156459915 | finite: pass, solar_physical: pass |
| evaluation-attempt-000003-fitting | fitting | success | 138.5395705820532 | finite: pass, solar_physical: pass |
| evaluation-attempt-000004-fitting | fitting | success | 139.38717464421438 | finite: pass, solar_physical: pass |
| evaluation-attempt-000005-fitting | fitting | success | 144.48237907146532 | finite: pass, solar_physical: pass |
| evaluation-attempt-000006-fitting | fitting | success | 140.4981216428561 | finite: pass, solar_physical: pass |
| evaluation-attempt-000007-fitting | fitting | success | 141.5623938237173 | finite: pass, solar_physical: pass |
| evaluation-attempt-000008-fitting | fitting | success | 141.23776144107748 | finite: pass, solar_physical: pass |
| evaluation-attempt-000009-fitting | fitting | success | 139.28007529884877 | finite: pass, solar_physical: pass |
| evaluation-attempt-000010-fitting | fitting | success | 149.7397464337728 | finite: pass, solar_physical: pass |
| evaluation-attempt-000011-fitting | fitting | success | 141.75664777600943 | finite: pass, solar_physical: pass |
| evaluation-attempt-000012-fitting | fitting | success | 143.79193581516523 | finite: pass, solar_physical: pass |
| evaluation-attempt-000013-fitting | fitting | success | 138.92269834748714 | finite: pass, solar_physical: pass |
| evaluation-attempt-000014-fitting | fitting | success | 138.98531977147968 | finite: pass, solar_physical: pass |
| evaluation-attempt-000015-comparison | comparison | success | 149.05726492493972 | finite: pass, solar_physical: pass |

## Decisions

- Comparator `evaluation-attempt-000001-comparison`: `accepted_candidate`. Selection: `evaluation-attempt-000002-comparison`.
  - Applied frozen eligibility and ranking rules
- Comparator `evaluation-attempt-000001-comparison`: `retain_baseline`. Selection: `evaluation-attempt-000001-comparison`.
  - evaluation-attempt-000015-comparison: primary gain below required improvement
- Comparator `evaluation-attempt-000001-comparison`: `accepted_candidate`. Selection: `evaluation-attempt-000002-comparison`.
  - Applied frozen eligibility and ranking rules

## Admission

- `mechanical-0c7e5cc997ec17fa20ab0914`: admitted.

[Immutable evaluation and check records](../../artifacts/0ba538a3461a9a78cf8ef4ad7a7a6867f7457f72af3edf5a30dc2fdafe1593c4/state.json).


## Immutable output evidence

- [evaluation-attempt-000001-comparison: output](../../artifacts/6c5552dc6cf3fa551d4f93c0fc37fb8d68291738d4e45224efd0051daac22767/outputs.npz), SHA-256 `6c5552dc6cf3fa551d4f93c0fc37fb8d68291738d4e45224efd0051daac22767`.
- [evaluation-attempt-000002-comparison: output](../../artifacts/d98c697a250b4414c5412f993cd6af06344e11481371204c40188b0a88a2faaa/outputs.npz), SHA-256 `d98c697a250b4414c5412f993cd6af06344e11481371204c40188b0a88a2faaa`.
- [evaluation-attempt-000003-fitting: output](../../artifacts/ebb40d04dc39cfa5a0993cbf5928a365a8ccaf8353864665b054d51a770f2a41/outputs.npz), SHA-256 `ebb40d04dc39cfa5a0993cbf5928a365a8ccaf8353864665b054d51a770f2a41`.
- [evaluation-attempt-000004-fitting: output](../../artifacts/4548c87c6fac69d0823bd5f7ecf1229aff23ea37629175b5fe703d145e97ffa4/outputs.npz), SHA-256 `4548c87c6fac69d0823bd5f7ecf1229aff23ea37629175b5fe703d145e97ffa4`.
- [evaluation-attempt-000005-fitting: output](../../artifacts/2b1dfd471963849016e2e2cc35908b2d7012aa730f69efd91bcaf74223bebd1e/outputs.npz), SHA-256 `2b1dfd471963849016e2e2cc35908b2d7012aa730f69efd91bcaf74223bebd1e`.
- [evaluation-attempt-000006-fitting: output](../../artifacts/3dfc4dffd56014aff2046d3ed15562d65ddacc13a73e32266a4e6fee2c88563d/outputs.npz), SHA-256 `3dfc4dffd56014aff2046d3ed15562d65ddacc13a73e32266a4e6fee2c88563d`.
- [evaluation-attempt-000007-fitting: output](../../artifacts/59793ad08f6e7c540e92e0f2985668bdab3669e218d2720d63d89178ae08d319/outputs.npz), SHA-256 `59793ad08f6e7c540e92e0f2985668bdab3669e218d2720d63d89178ae08d319`.
- [evaluation-attempt-000008-fitting: output](../../artifacts/4728cbacd0e1af521147d33017c3d2a68856fa09ab0f8bf8c84b8af380f8ceeb/outputs.npz), SHA-256 `4728cbacd0e1af521147d33017c3d2a68856fa09ab0f8bf8c84b8af380f8ceeb`.
- [evaluation-attempt-000009-fitting: output](../../artifacts/8545242b02ca22bd8a931e49a8deba83382860717bcdec9e65dc64660ad80d70/outputs.npz), SHA-256 `8545242b02ca22bd8a931e49a8deba83382860717bcdec9e65dc64660ad80d70`.
- [evaluation-attempt-000010-fitting: output](../../artifacts/8f7d847ab542901f23328df623c244493a439a0d7f4f93c68cfa8e9a86a7f0e7/outputs.npz), SHA-256 `8f7d847ab542901f23328df623c244493a439a0d7f4f93c68cfa8e9a86a7f0e7`.
- [evaluation-attempt-000011-fitting: output](../../artifacts/15106b2c25e33d2db3cf4bd0820c090b629c626d47c016c3839f08d822cb2809/outputs.npz), SHA-256 `15106b2c25e33d2db3cf4bd0820c090b629c626d47c016c3839f08d822cb2809`.
- [evaluation-attempt-000012-fitting: output](../../artifacts/4213e3370e2cab4a2711c028eb0fbc483b0292363c817e928f872bc79326cba5/outputs.npz), SHA-256 `4213e3370e2cab4a2711c028eb0fbc483b0292363c817e928f872bc79326cba5`.
- [evaluation-attempt-000013-fitting: output](../../artifacts/0fe4b8ce72643274e674ef75caecbe7f642be6c5855b7f6673a444e541a4a994/outputs.npz), SHA-256 `0fe4b8ce72643274e674ef75caecbe7f642be6c5855b7f6673a444e541a4a994`.
- [evaluation-attempt-000014-fitting: output](../../artifacts/da8469da400d77c66434393ee937b549949e1435cb69ac69f516cecbdcd4d083/outputs.npz), SHA-256 `da8469da400d77c66434393ee937b549949e1435cb69ac69f516cecbdcd4d083`.
- [evaluation-attempt-000015-comparison: output](../../artifacts/ebb40d04dc39cfa5a0993cbf5928a365a8ccaf8353864665b054d51a770f2a41/outputs.npz), SHA-256 `ebb40d04dc39cfa5a0993cbf5928a365a8ccaf8353864665b054d51a770f2a41`.

## Limits

This experimental local workflow evaluates supplied trusted implementations. Process separation provides lifecycle control and is not a security sandbox. Token ceilings, production agent roles, new host integrations, automatic model training, and general scientific improvement remain deferred.

Exposed development data do not establish independent confirmation. Unknown costs and unavailable checks remain explicit. This report requires no private observation reads or network access.
