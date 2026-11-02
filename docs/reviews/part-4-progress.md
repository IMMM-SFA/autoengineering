# Part 4 implementation progress

Work continues in `.worktrees/agentic-architecture`. Part 3 edits remain intact.
The parent interoperability plan remains the acceptance specification.

## Current evidence

- Source inventory: `part-4/starting-source-inventory.json` records SHA-256
  hashes of tracked and untracked working sources at the start of this work.
  It includes the initial integration records, before adapter implementation.
- Initial metadata portion of 4.2 implemented in
  `src/autoengineering/integrations/contracts.py`. Reuses campaign strict JSON
  records and artifact references. Integration changes reject compatibility.
- Trial links require checkpoint evidence for saved proposals and committed
  observation/attempt links for tell evidence. These records do not implement
  transactions, authenticate observations, verify checkpoint bytes or authorize
  execution. Those checks remain controller responsibilities.
- Focused tests: `tests/test_integration_contracts.py`, 11 passed.
- Full source/test/example Ruff check passed.
- Checks use the main checkout's default Python 3.12 environment with
  `PYTHONPATH=src`. The imported package path was verified in this worktree.

## Remaining gates

4.1 six-framework investigation and frozen prototype limits remain open.
4.2 durable synchronization and fault recovery remain open. 4.3 through 4.9
remain unimplemented. No optional framework has been installed or promoted.
No live agents, downloaded data, remote compute or historical benchmark reruns
were used. Platform integration qualification is not attempted.

Next: complete the six-system decision record and prototype limits, then
implement the scalar/daily BMI adapter and transaction recovery fixtures.

## Broad verification in progress

The full suite is running under exec session `90542` and has reported failures
in existing agent process tests. A separate first-failure diagnostic exited 1:
`tests/test_agent_abandoned.py::test_owner_death_reconciles_as_unknown_failure_without_relaunch[None]`
failed because the supervisor exited before its readiness receipt. The cause is
not established. This is not a passing baseline. Diagnose before a completion
claim. New integration tests passed independently.

## BMI implementation increment

`src/autoengineering/adapters/bmi.py` now implements the existing adapter
lifecycle for trusted factories. Its deliberately explicit profile requires
scalar float64 buffers, exact declared units, daily interval ports, numeric
start zero and unit steps in days, and a supplied ISO origin. It rejects
unsupported metadata before stepping, validates each advancement, copies
forcing and output values, and prohibits reuse of an attempt. Initialization
failure attempts finalization and retains the primary exception if cleanup
also fails. Cleanup is idempotent.

Focused verification: 18 passed across `test_bmi_adapter.py` and
`test_integration_contracts.py`. Ruff passed for the new adapter and tests.
Seven BMI tests cover exchange isolation, repeat execution, stalled/overshooting
and nonfinite time, invalid units, wrong origin, partial initialization and
cleanup failure. These are fake-model contract tests. Direct local BMI parity,
independent BMI qualification, registration/source closure, cancellation,
restart accounting and a real campaign example remain open. This is partial
4.3 implementation, not qualification.

## Investigation and parity test update

Added `docs/decisions/part-4-integrations.md` with six framework dispositions,
ownership, official API discovery references, dependency availability, unresolved
license/platform checks and revisit conditions. Added the pre-execution limits
in `examples/interoperability/optimizer_comparison/protocol.json`. This is
partial 4.1: pinned license/dependency qualification and resolved manifests are
still required before execution or selection.

Expanded BMI tests reject wrong grid type/rank/size, dtype, names, time units,
step and end time before advancing, and reject nonfinite outputs. Added exact
local reservoir direct-driver parity, gated on bmipy. Verification command:

```sh
PYTHONPATH=src /Users/cam/projects/autoengineering/.pixi/envs/default/bin/python \
  -m pytest tests/test_bmi_adapter.py tests/test_integration_contracts.py \
  -q -p no:cacheprovider
```

Observed exit 0: 28 passed, 1 skipped (bmipy absent). Full Ruff exit 0.
The skip is unverified local parity, not a passed parity gate. The broader test
process remains live under session 90542 and has reached 28 percent with
failures. No broad-suite success is claimed.

## Isolated dependency environment and lifecycle correction

The user authorized isolated project installations. Created and resolved
`examples/interoperability/optimizer_comparison/pixi.toml` and `pixi.lock`,
separate from the base environment. Installed bmipy 2.0.1, Optuna 4.5.0,
Ax 1.1.2, OpenMDAO 3.41.0 and pvlib 0.15.2. The package metadata inventory is
`part-4/prototype-environment.json`. Resolution includes Linux but runtime
qualification is only being attempted on macOS ARM64. Earlier absence notes
remain historical. No optimizer is selected or publicly promoted.

Pixi install exited 0 with cache access. Sandboxed `pixi run` cannot acquire
its cache lock, so checks use the installed environment interpreter directly
with `PYTHONPATH=src`.

Fixed the shared `run_lifecycle` to retain the primary model exception when
cleanup also fails. Cleanup-only failures still propagate. Two tests verify
both outcomes. Default-environment focused result: 30 passed, 1 skipped.
Full Ruff passed.

The earlier full default suite completed with exit 1: 269 failed, 1170 passed,
65 skipped, 26 errors in 372.62 seconds. Failures remain undiagnosed. Do not
claim a passing baseline or qualify Part 4 from focused tests alone.

Installed prototype environment focused result: 31 passed, no skips, exit 0
in 28.89 seconds. This includes exact direct/wrapped LinearReservoirBmi parity
against the preserved example driver. Independent BMI qualification, full
campaign registration and restart accounting remain open.

## OpenMDAO lifecycle increment

Implemented `adapters/openmdao.py` with trusted fresh Problem factory, copied
immutable mappings, exact scalar unit/shape checks, explicit parameter mapping,
run_model-only execution, required finite convergence/work diagnostics and
idempotent cleanup. Setup failure closes the partial Problem and retains the
primary exception if cleanup fails. A consumed attempt cannot run again.
The inspector and factory must be included in trusted source registration.
No objective or constraint acceptance is delegated to this adapter.

Installed-environment verification: `tests/test_openmdao_adapter.py`, 6 passed
in 13.00 seconds, exit 0. Includes direct/wrapped parity with a real OpenMDAO
ExecComp, finite nonconvergence rejection, diagnostics consistency, copied
forcing/results, metadata failure cleanup and single-use attempts. Full Ruff
exit 0. These tests do not qualify coupled solves or derivatives.

Recorded the resistor/diode circuit selection rationale in the integration
decision record before comparison. Coupled parity, native optimization,
constraint/derivative checks and exact inner-work accounting remain open.

## Replay transaction increment and Optuna prototype

Added `integrations/replay.py`: owner-private, single-writer, immutable
hash-linked JSON transcript with ask intent, saved proposal, tell intent and
synchronization commits. Replay creates a disposable in-memory policy and
checks every saved suggestion exactly. Changed proposals, overlapping actions,
conflicting tells, malformed ordering and uncommitted results fail closed.
The bridge has no evaluator or physical launch method. Its committed-result
callback must be supplied by the authoritative controller, not a worker.

This recovery strategy is restricted to qualified in-memory policies without
remote or durable side effects. It does not restore arbitrary framework
checkpoints or promise exact-once remote transactions. Seed alone is not
accepted: all saved asks are verified against the reconstructed trajectory.
The controller integration and independent ledger/checkpoint anchors remain
required before public promotion.

Added a real Optuna 4.5.0 public ask/tell replay prototype under the comparison
example. It supports flat numeric/categorical spaces and explicitly rejects
conditional translation and bool/integer category collisions. Pruning is
disabled. Failed/infeasible observations have no objective and project to
Optuna FAIL while retaining full reason in the transcript. This prototype is
not a selected policy or a public backend. The seven-trial recovery test
compares fresh and resumed sessions through TPE startup and adaptation,
including one model failure and duplicate tell delivery.

Fault tests cover crash after all four commits, lost acknowledgment, replay
drift, corrupt history, duplicate/conflicting observations, changed ledger
prefix, one outstanding action and all failure statuses without penalties.
Initial installed-environment test run: 12 passed in 5.66 seconds. A final
combined run and Ruff follow the last duplicate-trial-ID guard change.
Final combined replay/prototype/record verification: 23 passed in 1.79 seconds,
exit 0. Full source/test/example Ruff passed, exit 0.

## Ax public prototype and conditional activation

Added an Ax 1.1.2 prototype using public `ax.api.client.Client` and parameter
configuration APIs. It uses serial ask/complete/failed calls, CPU generation,
four initialization trials and a pinned random seed. It does not use internal
Experiment/Trial construction. Homogeneous categorical types and at most one
categorical selector per conditional numeric parameter are supported. Other
hierarchies fail before suggestion.

Added version 1 explicit branch mapping with validated inactive defaults,
scientific active-parameter projection and canonical identity. Optuna samples
only active parameters. Ax uses public dependent-parameter declarations. Both
frameworks returned only active decisions in the four-trial conditional test.
The default expansion is for identity and deduplication, not an extra sampled
scientific parameter. Executor-level deduplication and exhaustion handling are
still required.

Installed-environment tests for branch mapping and both real prototypes:
5 passed, exit 0 in 6.74 seconds. Full Ruff passed. Ax emitted 122 upstream
Pandas deprecation warnings. Its four-trial initialization trajectory reproduced
through fresh replay sessions. Adaptive generation/replay qualification remains
open. A separate bounded six-trial adaptive API smoke is running with a
120-second subprocess timeout and one BLAS/OpenMP thread. Its retained log is
`part-4/ax-adaptive-smoke.log`. This smoke is not the frozen optimizer comparison.
Adaptive update: six-trial Ax smoke exited 0. Extended the recovery test to
six trials, including two MBM adaptive proposals, with fresh transcript replay.
Observed exact proposal agreement, 1 passed in 7.31 seconds (371 upstream
Pandas warnings). Command used `OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
PYTHONPATH=src` with the installed prototype Python and
`pytest tests/test_ax_replay_prototype.py -q -p no:cacheprovider`.
This verifies the bounded trajectory on this platform only, not arbitrary
framework state or hardware portability. Full matched comparison remains open.

## First matched runner execution retained as diagnostic evidence

Added analytic cases, resource-bounded serial subprocess supervision, per-start
result commits, replay checks, shared four-point initialization for Ax/Optuna/
Sobol and an offline report reader. Initial execution is retained under
`outputs/part-4-optimizer-comparison-v1`, with all process logs, result records,
source snapshots and supervision receipts. It completed all 27 cell processes.
No historical benchmark or agent was run.

This run cannot select a policy. The runner incorrectly fed raw Sobol activity
mask dimensions to canonical conditional decode. All conditional cells failed
before model starts. Corrected with the existing Sobol backend's selector-driven
projection convention and added a regression case. A report module was also
added during execution, so cell source inventories differ. Treat v1 as diagnostic
rather than a frozen matched-source run. Never overwrite or relabel it.

Ax additionally exposed a DataRequiredError after failed/infeasible initial
trials for continuous seed 2, and object-array conversion errors during mixed
adaptive fitting under the current resolved Pandas environment. These are retained
candidate/environment limitations pending diagnosis, not Optuna selection proof.
Ax continuous seed 0 stopped on a duplicate proposal without dispatching another
physical attempt. No penalty objective or fake failed attempt was inserted.

Next: validate the corrected runner, freeze its source inventory, then execute a
fresh bounded comparison root with the same scientific protocol. Recover and
report failed-cell physical work from retained result files, not only summaries.
Offline v1 reconstruction exited 0 and counted 179 committed physical starts,
including failed-cell work. Report:
`part-4/optimizer-comparison-v1-diagnostic.md`. Full Ruff passed. The corrected
conditional projection regression passed in base (2 passed, 2 optional skips).
A fresh v2 comparison has been launched under the same 324-start/3600-second
per-run ceilings. It preserves v1 and now rejects prototype source changes
between cells. No prototype code will be edited while v2 runs.

## Corrected comparison completed

V2 completed all 27 processes with 251 committed physical starts. Raw evidence
was preserved at `examples/interoperability/optimizer_comparison/results-v2/`.
Offline reconstruction exited 0 and wrote `part-4/optimizer-comparison-v2.md`.
Shared initial configurations and source inventories matched across all three
policies for each of nine case/seed combinations. Optuna and Sobol completed
all nine cells. Ax limits and all failed-cell work remain visible in the report.

Selected Optuna 4.5.0 for implementation, with public promotion still gated on
4.5 controller integration. The decision record explains ordered selection
criteria and preserves Ax limitations. Installed distribution license files
and hashes were retained in `part-4/installed-license-evidence.json`.

Added the initial trusted circuit factory/diagnostics in
`examples/interoperability/circuit/model.py`. It preserves the upstream coupled
model and records pinned instrumentation hooks. It has only passed Ruff, not
runtime/parity/derivative qualification. The engineering gate remains open.

## Selected-policy controller integration

Added `optimization/optuna_backend.py` and strict run-file options, lazy backend
construction, campaign dependency preflight, a named package extra and separate
Pixi `optuna` environment. Existing environment records in pixi.lock were
compared to HEAD and are unchanged. Added `optimization-optuna.yaml` and current
guide commands. The backend reconstructs disposable sessions from ledger
entries, verifies each historical configuration, samples only active parameters,
keeps failed/infeasible outcomes objective-free and derives recommendations from
the authoritative ledger. Version, environment and implementation bytes bind
resume identity. The controller remains the only execution/result authority.

Installed-environment unit/run-spec verification: 56 passed, exit 0. Focused
controller/campaign study tests with process inspection enabled: 7 passed in
23.82 seconds. Covers fresh/resume parity, committed-result recovery without
relaunch, changed-option rejection, historical-action drift, and supplied
candidate calibration with five accounted physical starts. The same campaign
test failed with reconciliation_required in the sandbox, which blocks ps.
No supervisor checks were weakened to bypass that restriction.

Public CLI ran three evaluations in `outputs/part-4-optuna-public-v1`, then
resumed the original 12-evaluation budget. Final command result is being checked.
A full base suite rerun with process inspection enabled is running under exec
session 30956, writing
`outputs/part-4-base-tests-process-access.log`. Earlier sandbox failures remain
historical failed checks, not a passed baseline. Full Ruff passed.

Remaining 4.5 work includes explicit pre-ask intent evidence for the disposable
session strategy, complete fault coverage and immutable scientific source
closure/version admission. Do not mark 4.5 or Part 4 complete from these tests.

Public CLI resume exited 0 at 12 total evaluations and cost 12 model_run.
Retained statuses: 7 model_failure, 5 success. The recommendation is a feasible
successful ledger observation. No failed result was converted into a score.

## Coupled engineering parity and derivative investigation

Added a frozen circuit protocol, scalar fixture, parity tests and development
runner. Initial direct/wrapped parity passed at .01, .05 and .1 A with frozen
voltage/current tolerances and matching work counters. The first development
run (`outputs/part-4-circuit-v1`) then failed the derivative gate before search.
The retained `derivative-failure-audit.json` showed total derivative .5971619743
versus finite difference .5971395561. The exact circuit equation agreed with the
OpenMDAO derivative. The diode constitutive residual was about 2e-9 A despite
near-zero Kirchhoff residual. Relative solver convergence had allowed this.

Tightened solver atol to 1e-13 and rtol to 1e-14 without changing the derivative
acceptance tolerance. Added Ohm's-law and diode-equation residuals to the trusted
inspector, beyond Kirchhoff balance. A second run retained an input-type failure
from a NumPy boolean in strict diagnostics. Converted the scalar residual to a
Python float. All failed directories remain intact.

Run `outputs/part-4-circuit-v3` exited 0. It retained 3 direct/wrapped parity
cases (6 starts), a 3-start derivative audit, 12 Optuna whole-problem attempts
and a separate native SLSQP run with 10 coupled solves. Native retained its
derivatives, converged with residual 2.82e-17 A and reported 959 component calls
and 295 derivative callbacks. Its final-solve iteration count is 2, not the total
iterations across the native run. The native objective was 3.77e-13 V^2 versus
Optuna's best 1.63e-6 V^2. Budgets for inner work differ, so the report labels the
comparison unmatched and makes no fixed-budget superiority claim.

The runner finished in .67 seconds after imports. Memory/deadline supervision,
installed report reconstruction, aggregate solver-iteration accounting, source
registration and final evidence sealing remain open. Raw failed/successful
artifacts currently live under ignored outputs and must be archived before
handoff. This is development evidence, not independent physical validation.

## Solar cache inventory, time contract and direct parity

Added `SubdailyTimeContract` schema 2.0 as a separate strict union member of
PortContract. The daily record remains unchanged. The new profile declares UTC
five-minute instantaneous samples, canonical timestamps, increasing axes,
explicit state reset across gaps, and independent warmup/scoring masks. It
rejects interpolation, daily relabeling, local offsets, duplicate/off-grid
samples and power-as-energy semantics. Contract/daily regression verification:
32 passed, exit 0. Full Ruff passed.

The original OEDI loader now accepts an optional explicit cache directory with
unchanged default behavior. `examples/interoperability/solar/data.py` verifies
all four existing main-checkout cache files against the preserved source
manifest. No fetch, cache copy or byte change occurred. The solar protocol
freezes 2018-06-01 through 2018-06-07, previously exposed development data,
US/Mountain localization/exclusion rules followed by UTC conversion, thermal
alternatives, bounded DC loss scale and power RMSE without energy reporting.

Added a supplied Python lifecycle adapter, explicit subdaily scalar-port
fixture and reproducible `solar.parity` command. Invalid loss gain >1 rejects
before physics. Night-time tests retain Sandia standby behavior rather than
silently clipping it to zero. An initial parity setup failed because Pandas
DatetimeIndex storage was microseconds while the fixture assumed nanoseconds.
The strict mask check caught false gap detection. Explicit `as_unit('ns')`
conversion and a microsecond-index regression test fix that mismatch.

`outputs/part-4-solar-parity-v2` exited 0 after verifying cached inputs and
executing direct and wrapped baselines. 1336 valid rows, 1109 scored rows,
148.15091534768507 kW development RMSE, 2 physical starts, 1.10 seconds after
imports. Both AC and module-temperature arrays agreed within frozen tolerances.
Retained full output arrays and masks in NPZ. SciPy emitted a division warning
at night, but all validated output arrays were finite. No energy, test-set or
confirmation claim is made. Optimizer/campaign wiring, missing-data tests,
physical controls, budget supervision and evidence archival remain open.
Solar/time focused verification after the timestamp regression: 12 passed in
4.40 seconds, exit 0; full Ruff passed.

The process-enabled full base suite completed with exit 1: 3 failed, 1426 passed,
72 skipped, 73 errors in 541.88 seconds. Most setup errors report an artifact
size mismatch for the retained Part 3 profile's pixi.lock reference (511397
bytes) after the optional-environment lock update. Preserve that original
profile and its invalidation. New profiles/tests need explicit current identity,
not rewritten historical provenance. The three failures are campaign CLI
negative-decision behavior, documentation extras metadata, and the legacy
command NPZ contract. These remain to diagnose. The earlier sandbox-only
failure count was reduced but the suite is not passing.

## Fresh-profile lock regression correction

Diagnosed the remaining base-suite setup errors: Leaf preparation and its
synthetic derivative both reused the historical template's lock reference after
capturing current lock bytes. Fresh derived profiles now bind their actual
captured environment lock and model dependency digest. Loading reconstructs the
identity from the captured lock, preserving historical snapshots. The original
Part 3 campaign template and checked evidence were not modified.

Added `test_agent_profile_lock.py`: current-lock binding, all three route
profiles, reload and byte-for-byte preservation of the historical template.
Observed 1 passed in 4.71 seconds, exit 0. Full Ruff passed.

A focused process-enabled rerun also passed the three ordinary base failures
alongside documentation: 21 passed, with preparation setup still failing before
the second correction. The docs test now includes the pinned optional Optuna
extra. The NPZ command test passed when the documented environment's bin was
included on PATH. The negative-decision CLI test passed with stable sources.

The larger preparation/comparison regression is live under exec session 62554,
writing `outputs/part-4-profile-regression.log`; it has reported no failures so
far. It must finish before a passing regression claim. Added the interoperability
README with runnable commands, prior exposure, dependency separation and explicit
remaining resource/qualification limits.

## Solar campaign registration and calibration increment

Preparation regression completed: 53 passed in 433.49 seconds, exit 0. This
covers the fresh lock corrections in matched/synthetic preparation and readers.

Registered the supplied `solar-pvlib` adapter with explicit source paths and
trusted factory. Added independent `solar_physical` checks for equipment capacity,
standby floor, nonpositive zero-POA output, forcing bounds and loss scale. Added
method/implementation binding for supplied Faiman/SAPM alternatives. Existing
checks were not weakened. Base solar/time/campaign-contract checks: 36 passed,
3 optional skips in 3.30 seconds, exit 0. Full Ruff passed.

Added a reproducible solar campaign preparation module. It verifies the existing
OEDI cache, creates fitting observations before June 5 and comparison observations
from June 5 onward, excludes unavailable labels without filling, keeps full
forcing, calibrates numeric parameters only on fitting data through Optuna, and
retains previous exposure with confirmation disabled. One supplied alternative
is evaluated under an 18-physical-start ceiling. All required scientific checks
are mandatory for eligibility.

First preparation rejected an incorrect child cost unit before execution. The
next prepared profile executed one baseline attempt (1.77 seconds), then refused
the calibration reservation: 14 future calls at a 40-second timeout reservation
could not fit the 120-second active allowance. It terminated budget_exhausted
with no unresolved work. This failed run is retained under
`outputs/part-4-solar-campaign-run-v1`.

The next profile retains the 120-second allowance and 18-start ceiling, with a
stricter five-second worker timeout and one-second termination/kill waits. Its
sources include the preparation, loader, protocol and model implementations.
Prepared at `outputs/part-4-solar-campaign-v3`; execution is live under session
from the current tool result, writing `outputs/part-4-solar-campaign-run-v2.log`.
No success or completed calibration is claimed until its evidence is inspected.

## Solar campaign outcome and proposal-intent recovery

The bounded solar campaign completed with exit 0: accepted_candidate,
15 physical attempts, zero unresolved attempts, confirmation_not_attempted.
Read-only reconstruction confirmed all required physical checks passed on
comparison evaluations. Baseline comparison RMSE was 142.99363734651664 kW;
steady Faiman without fitted parameters achieved 139.8092156459915 kW and was
selected. The fitting-selected calibrated configuration was worse on comparison
at 158.7166744753671 kW. That adverse result remains retained. These are
previously exposed development data, not independent validation or a claim
that Optuna improved the baseline.

Added optional `SuggestionEvidenceBackend` controller hooks under its existing
writer lock. The Optuna backend now saves a ledger-prefix-bound intent before
stateful ask and exact proposal bytes before controller action admission.
Historical evidence is checked before new suggestions. Pending recovery requires
both saved intent and proposal and rejects missing/corrupt evidence rather than
recreating it. The disposable-session identity is versioned to replay v2.
The authoritative controller still owns reservations and result commits.

Optuna controller/campaign tests with process inspection enabled: 9 passed in
10.06 seconds, exit 0. Added crash injection after intent and proposal evidence,
asserting no physical start before recovery and exactly one afterward. Missing
pending intent/proposal each block recovery. Existing fresh/resume,
committed-result, changed-option and drift tests also passed. Full Ruff passed.
A narrow base controller/recovery/contracts/docs regression is now running.
Narrow base controller/recovery/contracts/docs regression after the proposal
hooks: 160 passed, 21 optional skips in 9.20 seconds, exit 0.

## Evidence archives and installed report reconstruction

Added `integrations/evidence.py`: strict bounded index records, explicit SHA-256
pin verification, confined regular-file access, immutable fresh archive creation
and read-only report reconstruction. Reports import no optional framework and
execute no model or evaluator. Circuit reconstruction rechecks retained parity
and derivative tolerance. Archive verification is byte integrity, not scientific
qualification. Added corruption, missing-file, symlink/traversal, duplicate-key
and read-only regression checks: 4 passed in .61 seconds, exit 0. Full Ruff passed.

Archived the complete retained optimizer comparison (runtime locks omitted),
circuit v3 evidence, and a solar scientific-state/report snapshot under
`examples/interoperability/evidence/`, with SHA-256 pins and regenerated Markdown.
Solar raw observations/forcing and full resumable run bundle remain in the local
outputs directory pending data redistribution terms. The archive explicitly
records that omission and is not advertised as a resumable campaign.

Built wheel `autoengineering-0.2.0-py3-none-any.whl`, SHA-256
`e86a02cb84239070a5a06bdb711d6131ff1f97c9c96c641425791d42b360c8cc`,
using `pip wheel . --no-deps --no-build-isolation`. Installed without dependencies
into `outputs/part-4-wheel-install-v1`. A fresh Python -I process imported the
installed package from that target, changed cwd to /private/tmp, blocked all
optional framework imports, ran CLI help (exit 0), and rebuilt all three reports
byte-for-byte. Verification is retained at
`outputs/part-4-installed-reports-v1/verification.json`. No framework/model ran.
This qualifies that wheel's report path, not all runnable example packaging.

Added `docs/interoperability.md` and index link. Remaining required work includes
source-closure admission for new scientific profiles, full adapter/runtime and
fault qualification, independent BMI investigation, measured extension decisions,
resource-supervised engineering/solar artifacts, final fresh wheel/default/Bayes
checks and requirement-by-requirement completion audit. Part 4 remains incomplete.

## Versioned interoperability scientific admission

Added scientific closure version 3 as an exact version-1 extension containing
BMI/OpenMDAO adapters, Optuna backend and integration record/replay sources.
Worker/host modules are excluded. The version-1 and version-2 JSON manifests
were SHA-256 checked against the starting source inventory and are unchanged.
Combined generated/interoperability execution is rejected as unqualified.

Optuna preflight now rejects an older declared scientific profile or a missing
implementation reference before optional dependency construction or any model
start. Entire-package profiles retain their existing complete-source checks.
New solar preparations use the explicit version-3 profile instead of capturing
all host code. The manifest is included in package data for wheel builds.

Added exact-extension, missing-source, shortened-allowlist, base-manifest and
older-capability rejection tests. Updated the old unknown-version test to use
version 4, preserving its rejection contract now that version 3 is supported.
Identity/docs checks: 36 passed in 1.67 seconds. Process-enabled Optuna/identity
checks: 14 passed in 9.49 seconds. Full Ruff passed.

Prepared `outputs/part-4-solar-campaign-v4` and launched a fresh bounded run at
`outputs/part-4-solar-campaign-run-v3` to verify version-3 admission together with
proposal intent/recovery evidence. The previous solar runs and sealed report
snapshot remain unchanged. Do not claim this new run succeeded until inspected.
Version-3 solar campaign verification completed with exit 0: 15 physical attempts,
accepted_candidate, zero unresolved work and confirmation_not_attempted. It uses
both the explicit source profile and durable Optuna proposal evidence. Original
source/version-1 run artifacts remain unchanged.

Recorded the independent CSDMS BmiHeat source investigation and its unsupported
2D/seconds semantics in the decision record. No flattening or implicit time
conversion was admitted. Runtime/immutable-version/license qualification of that
independent implementation is not attempted. PyMT remains deferred for lack of
a named spatial exchange need. This satisfies investigation only, not general
BMI or PyMT compatibility.

## Runnable example wheel packaging

The wheel now includes explicit solar/circuit/comparator Python packages and
required protocol/solar metadata, excluding raw data and evidence archives.
Added the admitted `interoperability` package extra and separate Pixi environment
for BMI Python, OpenMDAO, pvlib and Optuna. Ax remains in the comparator project.
Resolved the lock and confirmed every original environment record remains equal
to HEAD. Added no framework to base imports or existing solve groups.

Solar preparation now captures stable logical scientific paths into a fresh
writable `source/` bundle, resolving actual engine files from the installed
package. It no longer requires output beneath the checkout or writes beside
installed code. Runtime adapter source-root resolution handles source layout
and installed package layout. Existing preparation/evidence remains intact.

Built wheel v3, SHA-256
`038d7bc6b6f5a782a67bc8b719b4aa1da5f8a239a8982c51092c2dd3109915c1`,
and installed it without dependencies into `outputs/part-4-wheel-install-v3`.
The installation reused the pinned prototype environment's dependencies. Wheel
inspection confirmed version-3 manifest and required protocols, and absence of
raw/evidence/result payloads. Documentation/identity/evidence checks: 28 passed,
exit 0. Full Ruff passed.

An initial installed solar check in shared /private/tmp failed before model
initialization because an unrelated inspect.py shadowed the standard library in
a supervised child. The stopped infrastructure attempt remains in
`outputs/part-4-installed-solar-v1` with uncertain cost. No unrelated file was
modified. A fresh private outside-checkout directory removed that interference.

The installed solar check then passed: both package and example imports were
asserted beneath the installed target, preparation used the packaged metadata,
the first invocation charged 3 starts, and resume completed 15 confirmed starts
with accepted_candidate and no unresolved work. Confirmation was not attempted.
Receipt: `outputs/part-4-installed-solar-v2/verification.json`. This proves the
installed solar path, not general framework/platform utility. Installed circuit
verification is being inspected separately.

Installed circuit verification also exited 0 from a fresh outside-checkout
directory, with package/example import paths asserted under the wheel target.
All three parity cases and the derivative audit passed; 12 Optuna starts and
10 native coupled solves completed. Native convergence passed. The comparison
remains explicitly unmatched for inner work. Installed receipts are copied to
`part-4/installed-solar-wheel-v3.json` and
`part-4/installed-circuit-wheel-v3.json`.

Remaining packaging/qualification work includes a bundled BMI parity command,
aggregate native solver iterations, resource-supervised final examples, final
wheel/default/Bayes checks and the full completion audit. No Linux runtime or
general scientific utility claim is made.

## Installed BMI parity and rate/state time semantics

Added the bundled `examples.interoperability.bmi.run` command and its frozen
three-day protocol. It imports the preserved local reservoir class and direct
BMI driver, compares complete flow/storage arrays exactly, verifies forcing
immutability and checks conservation independently. Required local/Leaf River
helper modules are packaged without raw caches or historical result payloads.

Corrected the BMI adapter's supported time semantics: instantaneous inputs must
be sampled at interval start, and instantaneous outputs must be collected at
interval end. Daily flux rates in the reservoir fixture use interval_mean with
end labels; storage is instantaneous at end. The old local parity test's storage
label was corrected without changing the numerical model or historical runner.
Wrong instantaneous output timing fails before stepping and triggers cleanup.
BMI/subdaily/identity checks: 33 passed in 1.26 seconds, exit 0. Full Ruff passed.

Direct/wrapped development execution exited 0 with exact parity and a maximum
water-balance residual of 2.220446049250313e-16 mm. Built wheel v4, SHA-256
`cbfe9aebd01a3ec23ffd4a69de23610e65a5351ca0894bc2b57f6a8d72ff25b6`,
and installed without dependencies into `outputs/part-4-wheel-install-v4`.
A fresh Python -I process outside the checkout asserted installed package/example
paths and ran the BMI command successfully. Two model starts completed with
exact parity and conservation. Receipt copied to
`part-4/installed-bmi-wheel-v4.json`. The wheel excludes raw/evidence archives.

Added the installed BMI evidence archive and pin under
`examples/interoperability/evidence/bmi-installed-v1`. The offline reader now
rechecks exact output parity and independently recomputes conservation using
digest-verified bounded NPZ loading. It also rejects unsupported rate/state
semantics. Seven evidence-reader tests passed, including self-consistent archive
indexes whose numeric parity or balance is deliberately wrong. The new BMI
reader branch has been checked from source; it needs the final fresh wheel
verification with the other readers.

Remaining work includes aggregate native iteration accounting, final resource
supervision/qualification, complete lifecycle/fault evidence, extension profiling
and final default/Bayes/wheel checks. Part 4 is not complete.

## Aggregate solver work and resource supervisor

Added per-native-solve iteration counts, total iterations and full native outputs
to the circuit report. The prior final-solve count remains labeled separately.
Added a lazy optional psutil 7.2.2 process-tree supervisor for the trusted BMI,
circuit and solar commands. It samples aggregate observed RSS, enforces a wall
deadline, tracks descendants by creation identity, stops observed work on failure
and records verified disappearance after reaping. It does not emit scientific
objectives or automatically restart interrupted work. RSS sampling is not a
kernel instantaneous quota; escaping detached work between samples is outside
this boundary. The admitted examples do not detach scientific work.

Added local success, deadline and descendant-memory tests. An initial test caught
checking stop before the killed root was reaped. Corrected to recheck actual
process disappearance after reaping. Final focused result: 3 passed in 1.08
seconds. Full Ruff passed. The optional interoperability lock explicitly declares
psutil; no base dependency was added.

Supervised BMI exited 0 in .86 seconds, sampled peak 154812416 bytes, 25 samples,
all observed work stopped. Supervised circuit exited 0 in 2.23 seconds, peak
222609408 bytes, 61 samples, all observed work stopped. The native circuit used
10 coupled solves and 52 total nonlinear iterations, with 2 in its last solve.
Both result trees remain under `outputs/part-4-supervised-*-v1`.

Supervised solar v1 failed in the monitor after 12.54 seconds with 12 observed
process identities and sampled peak 737509376 bytes, below its ceiling. All
observed work was stopped; the scientific ledger remains interrupted and cannot
be called complete. Added failure type/phase to monitor receipts and launched a
fresh bounded diagnostic run at `outputs/part-4-supervised-solar-v2`. The v1
artifacts remain preserved. No success is inferred from stopped processes.

## Resource-supervision diagnosis and verified runs

The solar v2 monitor receipt identified AccessDenied during RSS sampling. Added
an identity-checked POSIX ps fallback for protected helper executables. A live
process unreadable by both APIs still fails supervision; it is never counted as
zero. Five process-supervision tests now pass, including injected permission
denial and failure of both observation paths. Full Ruff passed.

Solar v3 completed scientific evaluations, but its wrapper exited nonzero while
formatting unresolved_attempts as an iterable instead of an integer count. That
nonzero run remains intact. Corrected the wrapper count and ran a fresh bounded
profile. Solar v4 exited 0 in 35.68 seconds, sampled peak tree RSS 573210624 bytes,
842 samples and 36 observed process identities. All observed processes stopped.
Its scientific state remains explicit about 15 starts and no confirmation.

Added durable intent/receipt files around every native circuit solve so failures
cannot discard already-performed native work. Circuit v2 supervision exited 0
in 2.10 seconds, peak 177963008 bytes and 54 samples. Verified all 10 solve
receipts and 52 aggregate nonlinear iterations against the final report. Native
work remains unmatched against the external policy budget.

Both earlier monitor failures and the report-format failure are preserved.
Added prelaunch supervisor/example code hashes, protocol and runtime identity
for future final receipts. The final wheel/resource verification must include
these identity fields; older receipts are retained as development evidence.

## Final verification batch and open completion audit

Installed the locked Bayes and admitted-interoperability environments separately.
Verified Bayes imports this worktree's package and BoTorch 0.17.2. The full base
suite (session 70815) and full Bayes suite (session 65611) are live, writing
`outputs/part-4-final-base-tests-v1.log` and
`outputs/part-4-final-bayes-tests-v1.log`. Scientific source files remain stable
during these runs. No frozen benchmark study is launched.

Dedicated admitted-environment integration checks completed: 97 passed, 1
Ax-only comparator skip and 3 warnings in 90.32 seconds, exit 0. This environment
contains only admitted frameworks, not the prototype Ax dependency stack.

Created `part-4-completion-audit.md` with the original numbered increments,
current evidence and remaining gaps, and `../part-4-handoff.md` with exposure,
candidates, conventional baselines, costs and unsupported scope. Both explicitly
remain open. The audit identifies external trial/result linkage and final fault
coverage as outstanding, rather than reducing completion to current passing tests.

Recorded quantitative serial profiling for the Ray need decision: 15 attempts,
35.68 seconds wall, 24.13 seconds summed attempt time, median 1.60 seconds and
maximum 2.04 seconds. The current policy has one outstanding action and no
predeclared independent batch. Ray/local-pool comparison remains deferred until
a concrete independent workload and numerical throughput target exist. DAKOTA
remains deferred because no current protocol declares an uncertainty decision or
justified probability distributions. These are need decisions, not framework
runtime qualification or blanket incompatibility claims.

## Production trial linkage and final installed qualification

Stopped the v1 full regression runs after they both exposed the same stale
preparation assertion. Their partial results are preserved: base 966 passed,
9 skipped and 1 failed; Bayes 504 passed, 6 skipped and 1 failed. Both exited 2
on intentional interruption. Fresh preparations correctly capture the current
lock, so the assertion now checks that dependency identity without modifying the
historical template. Neither interrupted run is a complete passing suite.

Optuna recovery version 3 now saves explicit logical experiment and trial IDs
with proposals. It persists tell intent before replaying a committed observation
and a synchronization receipt afterward. Receipts bind exact proposal, result,
ledger prefix and implementation dependencies. Campaign receipts reference actual
existing campaign attempt IDs. Standalone calls retain action-ledger accounting
without manufacturing campaign attempt IDs. A completed study with deleted or
changed synchronization evidence fails reconciliation. Only an exact pending
result transition may finish interrupted tell records. Replay verifies the full
action, including its seed. Changed implementation identity requires a fresh run.

Added fault checks after both tell boundaries, corrupt/missing result receipts,
changed seeds, failed/infeasible finite-space exhaustion, and missing/wrong
framework versions. Additional checks cover physical OpenMDAO output despite
driver scaling, invalid derivatives before optimizer comparison, nonfinite
constitutive residuals, solar gap warmup, absence of labels from forcing, and
nonfinite forcing at the shared lifecycle boundary. The final dedicated check
completed with 108 passed and four dependency warnings, exit 0. Open-chain
checks completed with nine passed, three wind/hybrid skips and 17 warnings.

Wheel v5 SHA-256 is
`78b5372b32c69343444ce099d217a399d1046aff6524c4ecaf0e532330b8e235`.
It was installed without dependencies in a fresh target. All three supervised
examples ran outside the checkout from that target. BMI/circuit/solar elapsed
0.91/1.94/45.97 seconds and stopped all observed identities. The solar run paused
at three starts and resumed to 15 confirmed starts, no unresolved attempt and
no confirmation. A separate installed solar direct/wrapped check passed all
1336 rows (1109 scored), preserving power units and night behavior. It used two
physical calls. Full output arrays and matching source/context identities remain
in the local parity directory.

The first v5 qualification invocation again encountered an unrelated
`/private/tmp/inspect.py` through Python's script-directory path. It performed
no model work. Safe-path invocation in a fresh private directory passed. The
initial solar archive script also selected the disposable state-name cache,
rather than the scientific state artifact, and failed reconstruction. Its
unpinned archive is retained as `diagnostic-solar-cache-projection-v5`. The
corrected archive reads the verified event chain and referenced state artifact.
No scientific run was repeated for that correction.

Seven pinned archives reconstruct from the final installed wheel with all
optional framework imports blocked. Reports match the retained bytes. Installed
CLI help also passes under the same import block. Qualification receipts,
environment versions, source inventory, reader verification and supervised
process identities are in `docs/reviews/part-4/*-v5.json`. The resource summary
and `integration-burden.md` document the observed overhead and responsibilities
removed from callers without claiming engineering-hour savings or scientific
superiority. The optional task is `pixi run -e interoperability test-interoperability`.

The final base and Bayes v2 suites run against the finished Python sources in
`outputs/part-4-final-{base,bayes}-tests-v2.log`. Their terminal results remain a
completion gate. Frozen benchmarks, remote compute and paid agents were not run.

The named optional Pixi task passed unchanged with 108 tests and four warnings
in 14.43 seconds, exit 0. A final preservation check confirms 124 inventoried
historical files unchanged, all six original lock environments unchanged, and
the original checkout clean. The wheel comparison verifies 196 current source,
protocol and lock payloads byte for byte and excludes caches/output archives.
These checks do not substitute for the still-running full regression suites.

## Final closeout

The complete v2 base suite exited 0: 1531 passed and 83 skipped in 1418.72 seconds.
The complete v2 Bayes suite exited 0: 1587 passed, 31 skipped and 44 warnings in
1581.82 seconds. Both used source inventory v5. No failed gate was relaxed.

A final identity review reproduced a valid standalone StudySpec display name
with spaces/slash failing at synchronization metadata. The exact failed test is
retained in `outputs/part-4-display-name-before-fix.log`. Only
`optimization/optuna_backend.py` changed after the full suites: the standalone
receipt study ID now derives from immutable experiment identity. Campaign IDs
retain their actual existing records. All 109 admitted integration tests passed
after this correction (four warnings, 17.37 seconds). The full-suite environments
skip optional Optuna tests, so those complete suites were not repeated for this
isolated correction. Post-correction documentation/CLI/run-file/recovery checks
also passed: 156 passed and one skipped in 8.84 seconds.

Final wheel v6 SHA-256:
`aa9a55a661f29570b3ac02bfb9cfd4efc72430b9449cd4ef6e92f5917682a94f`.
All 196 source/protocol/lock payloads match current files. All three supervised
installed examples passed outside the checkout. BMI/circuit/solar elapsed
0.83/1.56/38.36 seconds. All observed identities stopped. Solar retained 15
confirmed attempts, no unresolved attempt and no confirmation. Its 12 child
receipts match committed observation hashes, ledger prefixes and actual attempt
IDs. Native circuit receipts retain ten solves and 52 total nonlinear iterations.
The independent installed direct/wrapped solar parity check also passed.

All ten pinned evidence archives reconstruct from wheel v6 with optional
framework imports blocked. Installed help also passes under that block. Strict
integration receipts, full source and environment identities, installed reader
and supervision records, dependency/code footprint and final verification are
retained under `docs/reviews/part-4/`. Historical failures and v5 artifacts remain.
The original six lock environments and original checkout are preserved.

The completion audit and Part 5 handoff now close the original Part 4 scope for
bounded macOS ARM64 delivery. Linux runtime, independent confirmation and
need-gated PyMT/DAKOTA/Ray extensions remain explicitly unverified, not attempted
or deferred as specified. No commit, push, release or deployment was performed.
