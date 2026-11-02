# Part 4 completion audit

Status: complete for bounded macOS ARM64 delivery, 2026-10-28. This is a requirement audit against the original
[implementation plan](../implementation-plans/part-4-interoperability.md).
All required increments have executable evidence below. The named need-gated
extensions remain deferred, and Linux runtime remains unverified. This audit
does not establish predictive skill or general optimizer superiority.

| Gate | Current evidence | Status and remaining requirement |
| --- | --- | --- |
| 4.1 Starting state/source custody | `part-4/starting-source-inventory.json`; original worktree retained | Inventory retained; Part 3 edits and historical records preserved. |
| 4.1 All six investigations | `../decisions/part-4-integrations.md`; installed license evidence | BMI/OpenMDAO adopted, Optuna selected after Ax comparison. DAKOTA/Ray/PyMT deferred under stated need gates. Verified resource summary, Ray need profile and `part-4/integration-burden.md` retained. |
| 4.2 Immutable contracts | `integrations/contracts.py`; strict contract tests | Implemented. Unknown/duplicate/nonfinite/path and identity changes tested. |
| 4.2 Durable ask/proposal | Controller hooks and `optimizer-proposals` intent/proposal files; 12 links checked in solar | Verified recovery version 3: explicit experiment/trial IDs, immutable tell/synchronization receipts, exact observation/proposal hashes and actual campaign attempt IDs. Standalone action accounting remains distinct. |
| 4.2 Committed results/recovery | `test_optuna_backend.py`, replay fault tests, campaign physical attempt records | Verified crash after intent/proposal/result/tell/ack, lost acknowledgment, corrupt/deleted evidence and full-action drift. Identity binds translation/controller/ledger/source dependencies. No duplicate physical start. |
| 4.3 BMI numerical/interface subset | Preserved local reservoir direct/wrapped parity, installed-wheel v6 receipt, sealed BMI arrays | Verified exact parity/conservation and lifecycle failures. Trusted applications supply factories; arbitrary worker registration and killed-state restoration are unsupported. Supervisor cancellation checks retain stopped identities and require reconciliation. |
| 4.3 Independent BMI investigation | CSDMS heat-model source review in decision record | Grid/seconds semantics unsupported; runtime not attempted. No PyMT compatibility claim. This is a recorded subset limit. |
| 4.4 Ax/Optuna/Sobol prototypes | Complete retained v2 evidence and offline report; 251 committed starts | Same seeds/initial points/source inventories; all failure records retained. Verified repeated timing/resource summary and dependency/burden record. Timing phases include replay/durability and are not cold-import benchmarks. |
| 4.5 Selected policy | Optuna 4.5.0 backend; strict run options; CLI/campaign tests; public 12-evaluation example | Verified policy recovery, actual campaign links and final installed solar/circuit use. Full base/Bayes regression passed. The isolated final receipt-ID correction passed all 109 optional integration tests and final installed examples. |
| 4.6 Coupled engineering | Pinned resistor/diode circuit; parity, constitutive residuals, derivative audit, native driver and Optuna | Actual engineering model exercised. Native work separately counted, budgets explicitly unmatched. Verified final installed supervised execution, parity/derivative gates, invalid-derivative rejection, scaled physical outputs and finite constitutive residuals. Strict receipt `openmdao-qualification-v6.json`. |
| 4.6 Native inner work | 10 durable native solve receipts, 52 aggregate nonlinear iterations; derivative/component counters | Counts inspected. Final sealed circuit archive retains full outputs, upstream/source hashes and 10 native receipts/52 total iterations. Installed reader verifies parity and derivative differences. No fixed-budget superiority claim. |
| 4.7 Solar data/time semantics | Verified existing OEDI cache; version-2 UTC five-minute sample contract; declared gaps/warmup | Data unchanged; no downloads; power remains power. Verified gap restart/warmup, no labels in forcing, nonfinite lifecycle rejection and physical vetoes. Existing causal/reset open-chain checks pass. |
| 4.7 Solar campaign | Version-3 source profile; 15 accounted starts; fitting-only Optuna child study; physical vetoes | Uncalibrated Faiman selected. Calibration worsened comparison. Confirmation not attempted. Verified final installed pause/resume, 15 confirmed starts and zero unresolved attempts. Full arrays in installed parity output; `solar-qualification-v6.json` and sealed report snapshot retain limits. |
| 4.8 Need-driven extensions | Six-system decision record; measured serial example/resource traces | No extension admitted. Verified Ray serial profile/revisit threshold and DAKOTA missing decision/distributions. PyMT spatial/seconds need remains deferred. No placeholder adapters. |
| 4.9 Optional environments | Separate locked Optuna/interoperability/prototype environments | Base independence tested. Original environment records unchanged. Final installed runs and optional task use the admitted environment. Linux remains explicitly unverified. |
| 4.9 Installed artifacts | Final wheel v6; installed solar pause/resume, circuit and BMI commands; ten installed reports | Actual installed paths checked outside checkout. Verified final wheel v6: all three installed examples, ten reports and CLI help. Readers/help block optional imports. Wheel excludes raw caches and evidence archives. |
| 4.9 Resource supervision | Success/deadline/child-memory/permission tests; supervised examples; failures retained | Sampled RSS only, not a kernel quota. Verified final prelaunch source/protocol identity, sampled RSS, all observed PID/creation identities and stopped status. Detached escape between samples remains unsupported. |
| 4.9 Base checks | Lint passed; full base suite: 1531 passed, 83 skipped, exit 0 | V1 interrupted after a stale test expectation. V2 passed after correcting the expectation while preserving the template. See the post-correction scope below. |
| 4.9 Shared optimizer checks | BoTorch 0.17.2 full suite: 1587 passed, 31 skipped, 44 warnings, exit 0 | Full terminal result retained. No frozen benchmark replacement study was launched. |
| 4.9 Admitted integration checks | Final dedicated environment: 109 passed, four warnings; open-chain checks nine passed, three wind/hybrid skips | Verified after final Python changes. Exact logs retained. Optional Pixi task reproduces the same set. |
| Part 5 handoff | Development-only exposure recorded across guides/evidence | Handoff written with catalogue, exposure, baselines, cost definitions, limits and open questions. Verified handoff for Part 5; confirmation remains not attempted. |

## Required limits in the final handoff

- Only macOS ARM64 runtime evidence is currently available. Linux dependency
  resolution is not runtime qualification.
- Solar June 2018 data, and historical open-chain selection/test periods, have
  been inspected. They are not new independent confirmation data.
- The native circuit budget differs from the external policy budget. Keep inner
  work, derivatives and failed work visible.
- The selected supplied solar alternative improved this development comparison;
  fitted parameters worsened it. Neither result demonstrates general Optuna gain.
- Runtime qualification uses trusted factories/configuration. No worker may
  install frameworks, register arbitrary imports or manufacture results.
- RSS monitoring is sampled. Cancellation/limits require stopped-process evidence
  and scientific-ledger reconciliation, not an assumed completed objective.
- Historical failed runs, metadata mistakes, monitor failures and checked Part 3
  profiles remain unchanged. New source/lock identities create fresh studies.

Final records: `part-4/final-source-inventory-v6.json`,
`part-4/qualified-environment-v6.json`, four `*-qualification-v6.json` receipts,
`part-4/installed-supervised-wheel-v6.json`, `part-4/installed-report-readers-v6.json`
and `part-4/installed-help-v6.json`. The original source inventory remains intact.

## Final verification scope

The full base and Bayes suites passed against source inventory v5. The only
subsequent Python implementation change was in `optuna_backend.py`: standalone
receipt IDs now derive from immutable experiment identity rather than the display
name. A reproduced failing case with spaces/slash in the display name now passes.
Both full-suite environments skip the optional Optuna test module. After this
correction, all 109 admitted integration tests and all three installed examples
passed against final wheel v6. Lint and documentation/CLI checks also passed.
The full suites were not repeated for this isolated optional-policy correction.
Exact counts, commands, source identity and results remain in
`part-4/final-verification-v6.json` and the chronological progress record.

Final wheel SHA-256:
`aa9a55a661f29570b3ac02bfb9cfd4efc72430b9449cd4ef6e92f5917682a94f`.
All 196 packaged source/protocol/lock payloads match current files. All ten
retained pinned archives reconstruct from that wheel with optional framework
imports blocked. Installed CLI help passes under the same block. The final
solar run contains 15 confirmed attempts and no unresolved work. All 12 child
trial receipts match committed observation digests, ledger prefixes and actual
campaign attempt IDs. Native circuit evidence retains ten solves and 52 total
nonlinear iterations, with unmatched budgets explicit.

The Part 4 implementation is complete within the stated platform and interface
limits. This is not author approval, release, push, publication, deployment,
new live-call authority or independent scientific confirmation.
