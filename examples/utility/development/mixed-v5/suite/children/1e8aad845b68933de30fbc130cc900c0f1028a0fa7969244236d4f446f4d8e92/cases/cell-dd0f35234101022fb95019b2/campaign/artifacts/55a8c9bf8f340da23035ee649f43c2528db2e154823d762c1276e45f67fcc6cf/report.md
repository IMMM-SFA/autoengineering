# Campaign utility-exposed-solar

Previously exposed OEDI power reconstruction

Scientific specification: `b35c2685cc8bacdf81305af31ff7b3678d9eebd1bd92b0d3189698157e57f796`

Outcome: `accepted_candidate`.
Confirmation: `confirmation_not_attempted`.

Physical attempts: 15. Confirmed: 15. Unresolved: 0.
Reserved or consumed capacity: 15/18.
Measured cost: 15. Cost uncertainty: False.
Charged active time: 26.5775 seconds.

## Evaluations

| Evaluation | Split | Execution | RMSE | Checks |
| --- | --- | --- | --- | --- |
| evaluation-attempt-000001-comparison | comparison | success | 142.99363734651664 | finite: pass, solar_physical: pass |
| evaluation-attempt-000002-comparison | comparison | success | 139.8092156459915 | finite: pass, solar_physical: pass |
| evaluation-attempt-000003-fitting | fitting | success | 145.9540108688096 | finite: pass, solar_physical: pass |
| evaluation-attempt-000004-fitting | fitting | success | 138.71894108083356 | finite: pass, solar_physical: pass |
| evaluation-attempt-000005-fitting | fitting | success | 138.71930120625186 | finite: pass, solar_physical: pass |
| evaluation-attempt-000006-fitting | fitting | success | 138.49970251701828 | finite: pass, solar_physical: pass |
| evaluation-attempt-000007-fitting | fitting | success | 147.49443832571797 | finite: pass, solar_physical: pass |
| evaluation-attempt-000008-fitting | fitting | success | 143.95276628278035 | finite: pass, solar_physical: pass |
| evaluation-attempt-000009-fitting | fitting | success | 138.56605420734724 | finite: pass, solar_physical: pass |
| evaluation-attempt-000010-fitting | fitting | success | 139.91110902561786 | finite: pass, solar_physical: pass |
| evaluation-attempt-000011-fitting | fitting | success | 138.83545693538417 | finite: pass, solar_physical: pass |
| evaluation-attempt-000012-fitting | fitting | success | 143.33034309646152 | finite: pass, solar_physical: pass |
| evaluation-attempt-000013-fitting | fitting | success | 138.2174545909456 | finite: pass, solar_physical: pass |
| evaluation-attempt-000014-fitting | fitting | success | 138.19366163153012 | finite: pass, solar_physical: pass |
| evaluation-attempt-000015-comparison | comparison | success | 153.196972330194 | finite: pass, solar_physical: pass |

## Decisions

- Comparator `evaluation-attempt-000001-comparison`: `accepted_candidate`. Selection: `evaluation-attempt-000002-comparison`.
  - Applied frozen eligibility and ranking rules
- Comparator `evaluation-attempt-000001-comparison`: `retain_baseline`. Selection: `evaluation-attempt-000001-comparison`.
  - evaluation-attempt-000015-comparison: primary gain below required improvement
- Comparator `evaluation-attempt-000001-comparison`: `accepted_candidate`. Selection: `evaluation-attempt-000002-comparison`.
  - Applied frozen eligibility and ranking rules

## Admission

- `solar-faiman-v1`: admitted.

[Immutable evaluation and check records](../../artifacts/813609f00cbc48a82d2e8c52580aeafd2e91a0dad9ea0d7f04a7f350c0401d8a/state.json).


## Immutable output evidence

- [evaluation-attempt-000001-comparison: output](../../artifacts/6c5552dc6cf3fa551d4f93c0fc37fb8d68291738d4e45224efd0051daac22767/outputs.npz), SHA-256 `6c5552dc6cf3fa551d4f93c0fc37fb8d68291738d4e45224efd0051daac22767`.
- [evaluation-attempt-000002-comparison: output](../../artifacts/d98c697a250b4414c5412f993cd6af06344e11481371204c40188b0a88a2faaa/outputs.npz), SHA-256 `d98c697a250b4414c5412f993cd6af06344e11481371204c40188b0a88a2faaa`.
- [evaluation-attempt-000003-fitting: output](../../artifacts/2902962e3121a63bb747f6780d3a06b134b3370f28525cc04326b011a997fb59/outputs.npz), SHA-256 `2902962e3121a63bb747f6780d3a06b134b3370f28525cc04326b011a997fb59`.
- [evaluation-attempt-000004-fitting: output](../../artifacts/2d82fb04491351326c2e480167cd23e6425558d27d23b97f30a35dd3b9fe509a/outputs.npz), SHA-256 `2d82fb04491351326c2e480167cd23e6425558d27d23b97f30a35dd3b9fe509a`.
- [evaluation-attempt-000005-fitting: output](../../artifacts/849bbd867518fe850e69f6361734c892a45e797a8df346c3082167dad5c3c07c/outputs.npz), SHA-256 `849bbd867518fe850e69f6361734c892a45e797a8df346c3082167dad5c3c07c`.
- [evaluation-attempt-000006-fitting: output](../../artifacts/711a0a063f2ee59cac88e73ea57749ba016949484b54a7ebe83d232c56769cec/outputs.npz), SHA-256 `711a0a063f2ee59cac88e73ea57749ba016949484b54a7ebe83d232c56769cec`.
- [evaluation-attempt-000007-fitting: output](../../artifacts/4b59395a154ef8a29f8efab119c4b1668255918cb6b0d21e94f6dca489e865d8/outputs.npz), SHA-256 `4b59395a154ef8a29f8efab119c4b1668255918cb6b0d21e94f6dca489e865d8`.
- [evaluation-attempt-000008-fitting: output](../../artifacts/c535b1bfbf574a7272663b3d438ea87c208d7eec4dec88f6c2781742dcded141/outputs.npz), SHA-256 `c535b1bfbf574a7272663b3d438ea87c208d7eec4dec88f6c2781742dcded141`.
- [evaluation-attempt-000009-fitting: output](../../artifacts/576d871298ce34d8476f97208ff53deddb943ef5ac6e9789d2e93b638be457c0/outputs.npz), SHA-256 `576d871298ce34d8476f97208ff53deddb943ef5ac6e9789d2e93b638be457c0`.
- [evaluation-attempt-000010-fitting: output](../../artifacts/74a29c84d87ec9db5ecac3ff368aeea5690bb2959e31b608e7bfa692cd15be24/outputs.npz), SHA-256 `74a29c84d87ec9db5ecac3ff368aeea5690bb2959e31b608e7bfa692cd15be24`.
- [evaluation-attempt-000011-fitting: output](../../artifacts/0cac9c2c609f5a7e6917edffa0b0a1fca4e76513c804cd069437aaed63774b96/outputs.npz), SHA-256 `0cac9c2c609f5a7e6917edffa0b0a1fca4e76513c804cd069437aaed63774b96`.
- [evaluation-attempt-000012-fitting: output](../../artifacts/9ec8abe7204a02092299c79c040999e20b3bee2aea16241aca23fc85a551608b/outputs.npz), SHA-256 `9ec8abe7204a02092299c79c040999e20b3bee2aea16241aca23fc85a551608b`.
- [evaluation-attempt-000013-fitting: output](../../artifacts/beb4da6542ddb16eb970114b47776de4dce70f653a01e89910842549cc5f1544/outputs.npz), SHA-256 `beb4da6542ddb16eb970114b47776de4dce70f653a01e89910842549cc5f1544`.
- [evaluation-attempt-000014-fitting: output](../../artifacts/05eba5de0e83e84971d7f1fbb85a1fbd03684b1e34c97176c0a3160dad95226b/outputs.npz), SHA-256 `05eba5de0e83e84971d7f1fbb85a1fbd03684b1e34c97176c0a3160dad95226b`.
- [evaluation-attempt-000015-comparison: output](../../artifacts/05eba5de0e83e84971d7f1fbb85a1fbd03684b1e34c97176c0a3160dad95226b/outputs.npz), SHA-256 `05eba5de0e83e84971d7f1fbb85a1fbd03684b1e34c97176c0a3160dad95226b`.

## Limits

This experimental local workflow evaluates supplied trusted implementations. Process separation provides lifecycle control and is not a security sandbox. Token ceilings, production agent roles, new host integrations, automatic model training, and general scientific improvement remain deferred.

Exposed development data do not establish independent confirmation. Unknown costs and unavailable checks remain explicit. This report requires no private observation reads or network access.
