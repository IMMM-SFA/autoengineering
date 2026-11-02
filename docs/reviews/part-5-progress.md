# Part 5 implementation progress

## 2026-10-28: initial inventory and task drafts

Work continues in the existing `agentic-architecture` linked worktree at HEAD
`b393726`. Part 3/4 changes remain uncommitted and were preserved. The requested
plan is present as `part-5-utility-confirmation.md`; the main checkout does not
contain it. No source or previous evidence was overwritten.

Added `examples/utility/source-inventory.json`, `exposure-register.json`, and four
blocked task dossiers under `tasks/`. The inventory records source/configuration
SHA-256 values rather than treating HEAD as the implementation identity. It is
a development snapshot, not a source freeze for future execution.

Inspected the Part 4 handoff, solar/wind READMEs and scalar circuit factory and
bindings. Preserved Leaf River prior use, solar June 1-7 2018 and historical
2018/2019 exposure. Missing history remains unknown. No proposed confirmation
labels were opened. Hashing implementation source does not establish data rights
or exposure closure.

Selected the wind layout branch with unchanged V80 hardware and native TOPFARM
SLSQP as the draft conventional workflow. Selected source-current minimization
of electrical source power under scenario voltage requirements for the coupled
engineering question. Requirements and operating scenarios are not frozen.
The current circuit wrapper exposes only source current; new scenario bindings
must be qualified before this task can execute.

Environment directories present: default, bayes, interoperability, wind, hybrid.
Directory presence is not runtime qualification. No Linux runtime, second host,
training profile or new task adapter has been qualified. No development model
profiling, provider call, remote job or confirmation execution was performed.

G1 is an explicit incomplete suite with named blockers, not four admitted tasks.
All dossiers retain missing thresholds, partitions and numeric budgets as blockers.
The route to freezing is development profiling followed by source/data custody
closure, useful-effect and uncertainty design, then a complete numeric protocol.
G2-G8 remain unimplemented/unverified. No scientific utility verdict is available.

Verification: the default environment Python generated and parsed all six JSON
artifacts. Source inventory hashes and dossier completeness were independently
checked after generation. System `python` was unavailable; the project interpreter
was used. No package code changed, so runtime test suites were not run for this
increment. The next increment is strict immutable suite records and parent budgets.

## 2026-10-28: immutable matrix and cost contracts

Added the `utility` package with strict immutable suite/task/route/cell records,
explicit resource caps and confirmation reserves. Records reuse the existing strict
JSON serializer without changing legacy campaign or optimization schemas. Identity
binds ordered cells, candidate hashes, scientific grants, configuration, source,
locks, analysis, exposure and protocol digests. Adaptive grants must match. Paired
blocks require every assigned route with identical seed and scenario. Allocation
groups contain at most 32 cells and retain one suite budget; this is not yet child
batch dispatch.

Added physical cost receipts with exclusive allocations. Reconciliation rejects
duplicate receipts, separates resource units and preserves missing/unknown quantities.
Known partial totals cannot become a complete-cost conclusion.

Verification: repository-wide Ruff passed using the installed default environment
binary. Utility contracts/costs and legacy campaign-contract tests passed (see next
record for exact count). `pixi run lint` and `pixi run pytest` could not acquire a
cache-prefix install lock under sandbox permissions, so the equivalent installed
binaries were used. No environment or dependency configuration was changed.

G2 remains partial: durable suite store, parent reservation enforcement, child mapping,
concurrent-writer and recovery tests are still required. No task is admitted and no
scientific execution has been launched.

Focused verification completed: 44 tests passed in 12.45 seconds across
`test_utility_contracts.py`, `test_utility_costs.py` and `test_campaign_contracts.py`.
Full default and optional test suites have not been run for this increment.

## 2026-10-28: durable suite reservation journal

Added `utility/store.py` above the existing private-directory, durable-write and
advisory-lock facilities. Suite initialization commits its manifest last. Replay
checks the manifest identity, strict event schemas, linked event hashes, sequence,
cell identity and legal attempt transitions. It reads no executable factory.
Duplicate request IDs replay the original event only for identical payloads.

Reservations charge the parent regime permanently, including uncertain work.
Selection cannot spend the confirmation reserve. Started attempts cannot restart
after owner loss, child bindings cannot change, and unresolved cells block another
attempt. Cancellation blocks new starts while retaining charges. Confirmation
reservation is deliberately rejected pending the complete selection barrier.
Pinned child result digests are references, not copies of child observations.
Verification of those child artifacts and dispatch integration remain outstanding.

Ten store tests pass, including a 40-cell allocation across bounded groups sharing
a parent cap, concurrent writer exclusion, identity/tamper/symlink rejection,
commit-boundary failures, idempotent recovery, uncertain starts and reserve limits.
Repository-wide Ruff passes. The combined utility and legacy campaign contract/
recovery run initially had 56 passes and five recovery failures inside the sandbox.
Existing supervision requires `ps`, which the sandbox denied. The same combined
check was rerun with process inspection available; its final result is recorded
below. No runtime security boundary was weakened to accommodate the test runner.

G2 remains partial. Actual bounded child batch/campaign dispatch, complete cost
receipt joining and controller integration are not yet implemented. G3-G8 remain
outstanding. No confirmation data, provider calls or remote machines were used.

The combined rerun passed: 61 tests in 36.98 seconds. After adding two further
store tests, the store-only run passed all 10 tests in 1.49 seconds. The final
repository-wide Ruff check passed. `examples/utility/source-inventory-5.2.json`
pins the utility source and tests for this partial increment. Full default and
optional suites remain unrun for this increment.

## 2026-10-28: child batch dispatch and evidence reconciliation

Added `utility/controller.py` using the existing BatchSpec/BatchStore rather than
a second execution ledger. Preparation pins ordered cell-to-case bindings, checks
route configuration hashes and reserves the complete child case host/science caps
before creating a child batch. Each case conservatively reserves the whole child
elapsed-time ceiling. Training is not admitted through this path. Preparation
launches nothing. Resuming the same mapping cannot obtain new allowance.

Dispatch commits its start before calling the trusted runner. The runner must use
the existing batch physical reservation boundary. Parent acknowledgement requires
finished child evidence and no unresolved physical reservations. A lost owner
cannot automatically invoke the runner again. Reconciliation reads saved child
results, and offline verification hashes the original evidence and compares it
with the authoritative replay. Child manifests are pinned including creation time,
so opening a child cannot silently reset its clock. Interrupted child creation
without a saved manifest pin requires inspection rather than automatic recovery.

Tests use authored accounting fixtures, not real scientific utility. Forty cells
execute through two actual bounded BatchStores, with 40 physical callback starts
and one shared parent science cap. Read-only result verification adds no starts.
Additional tests cover child commit before suite acknowledgement, unresolved
work, tampered evidence, mapping identity and repeated preparation/dispatch.

Repository-wide Ruff passed. The combined utility/batch suite passed 54 tests in
19.17 seconds before the final child-manifest pin check. The controller suite
was rerun after that change; its result is recorded below. Full default and
optional suites remain unrun. G2 remains partial pending complete receipt joining,
failure injection across batch creation and host-specific preparation. G3-G8 and
real task admission remain outstanding. No provider or scientific model ran.

Final controller verification passed: 6 tests in 16.99 seconds after the manifest
pin change. The incremental source identity is saved in
`examples/utility/source-inventory-5.2-dispatch.json`.

## 2026-10-28: receipt joining, reporting and creation failures

Added offline batch receipt joining. Each metric has a stable receipt identity,
and repeated copies of the same source/resource quantity are rejected. Different
quantities from one physical receipt are permitted. Joining verifies original
observation and case-finish artifacts. It does not interpret a reservation or a
successful status as proof of a physical process start. Missing durations, token
fields and provider prices remain unknown. Per-attempt host/science durations
are separate quantities and are not added into an inclusive wall-time claim.
Task-level physical-start, training, solver, preprocessing, preparation and human
receipts remain required for complete cost evidence.

Added an offline accounting report with every assigned cell in its denominator,
parent charges, verified receipt quantities and named evidence blockers. No
executable model/provider is loaded. It reports no utility verdict and explicitly
withholds complete-cost status while task-level receipt coverage is incomplete.

Preparation now has failure injection at child mapping, parent reservation,
child creation and manifest pin boundaries. Tests verify idempotent resumption
without renewed caps. Child creation interrupted before the pin remains blocked
for inspection rather than acquiring a new clock origin. No scientific model,
provider call or confirmation execution was used by these authored tests.

Repository-wide Ruff passed. Focused tests and the full default suite were
launched with the installed default interpreter. The full suite uses process
inspection outside the restricted sandbox because the legacy recovery boundary
requires `ps`. Final results follow when processes terminate. Optional suites
have not been run for this increment. G2 remains partial and G3-G8 outstanding.

Focused utility/batch verification completed: 62 tests passed in 19.74 seconds.
The source snapshot is `examples/utility/source-inventory-5.2-receipts.json`.
Full default pytest remains running under exec session 17705. Its terminal result
has not yet been observed and no full-suite pass is claimed.

## 2026-10-28: exposure and chronological partition contracts

Added `utility/exposure.py` with strict immutable exposure records and chronological
partition manifests. Unknown exposure, missing custody/rights evidence, source
hashes, people or access history block admission. Ordered fitting, selection and
confirmation periods cannot overlap and embargoes must cover feature windows.
Manifest identities bind masks, preprocessing, initial state, causal carryover,
gap policy, seasonal coverage and access policy. No label file is opened.

Admission checks the entire pinned register, not just a new custody assertion.
Prior overlapping labels, diagnostics or aggregate exposure veto confirmation.
Removing a prior record changes the register identity and is rejected. Metadata
and driver-only access is distinguished from scoring exposure. Dates with unknown
history cannot establish nonoverlap. Scenario-only exposure is representable,
but scenario partition admission still needs its own implementation.

Ten focused exposure tests passed in 0.63 seconds. Repository-wide Ruff passed.
These files were added after collection of the running full default suite, so
that run does not cover them. It has not yet produced a terminal result. The same
exec session 17705 remains live and has reached 8 percent without reported failures.
No existing source used by that test run was modified during this increment.
G1 remains blocked on actual data custody. G2 and G3-G8 remain incomplete.

## 2026-10-28: registered engineering outcome semantics

Added `utility/outcomes.py` with separate versioned engineering outcome and
acceptance records. Units, minimize/maximize direction, scenario aggregation,
scoring callable source identity, useful gain, secondary limits and required
physical checks are frozen into their identities. Unknown/changed registrations
stop before scoring callbacks. Each scenario retains raw finite outcomes and
individual check results. Forcing arrays are hashed with shape and dtype.
Scoring receives copied read-only arrays to protect baseline inputs.

Engineering decisions verify saved aggregates and scenario identities, screen
secondary degradation using each declared direction, and invoke the existing
campaign eligibility/ranking implementation. Physical failures and unavailable
outcomes cannot win. Exact ties retain an eligible baseline. No prediction metric
is synthesized against artificial observations. Legacy AcceptanceSpec remains
unchanged and continues to reject engineering outcome names.

This is not yet a CampaignSpec/controller/calibration extension. Engineering task
adapters and authoritative scenario dispatch remain required. Registered callbacks
are trusted Python, not an isolation boundary or generated-code admission. Callable
source identity does not close imported dependencies; suite source closure must
cover those separately. G3 is partial and no engineering task is admitted.

Repository-wide Ruff passed. Focused outcome and legacy campaign-contract tests
were run using the default installed interpreter. Their final result follows.
The original full default suite (session 17705) remains live, with no terminal
result yet. It collected before these outcome tests were added.

Outcome and legacy contract verification completed: 30 tests passed in 3.14
seconds. Source hashes are in `examples/utility/source-inventory-outcomes.json`.
Process inspection confirmed that the default pytest process is alive with child
Python processes. It has not been restarted or treated as terminal.

## 2026-10-28: trusted offline preparation

Added `utility/preparation.py`. Preparation validates ordered candidate snapshots
through the existing AdapterRegistry without calling create or any factory. It
verifies pinned source inventory and lock bytes, dossier/outcome identities,
qualification artifacts, required capabilities, partition identity and the full
exposure register. Missing families/preparations and invalid custody produce
explicit blockers. It estimates every assigned cell and bounded allocation group
without creating a journal or reserving work. Even a ready-for-review result
explicitly authorizes zero starts.

Qualification artifacts are review evidence, not machine proof of scientific
adequacy. Task dossiers remain blocked in the repository. Capability profiles and
adapter registrations are application-owned; configuration cannot import its own
factory. Source or lock changes reject preparation. Scenario-only partitions and
training profiles remain unsupported here, pending their versioned contracts.
No task adapter was qualified by this increment. Campaign calibration integration
and task-specific direct/wrapped parity remain outstanding under G3.

Three preparation tests passed in 0.69 seconds, including real artifact hash
checks, immutable candidate order, capability rejection and a factory that raises
if preparation attempts construction. Repository-wide Ruff passed. No package
source loaded by the already-collected default suite was modified. That suite
continues under its original exec session 17705, without a terminal result yet.

## 2026-10-28: coupled engineering development adapter and native workflow

Added a ground-potential input binding around the intact existing OpenMDAO circuit
under `examples/utility/engineering.py`. The independent residual inspector now
uses voltage differences relative to ground in Ohm/diode constitutive checks.
Source power is current times the source-to-ground node voltage. Absolute node
voltage is a declared feasibility check rather than a fabricated prediction loss.
Existing Part 4 code/protocols were preserved.

Direct/wrapped parity passed for -0.05, 0 and +0.05 V development ground scenarios.
Native total derivatives agreed with finite differences. The SLSQP comparator
retains derivatives, solves the restrictive minimum-ground scenario and separately
checks every scenario. The reduction follows the circuit's voltage-translation
invariance, not retrospective scenario selection. Physical solve counts, inner
iteration/component/derivative counters and driver success are separate records.
Native derivative counters are cumulative snapshots and must not be summed.

Three optional engineering tests passed with four expected OpenMDAO coupled-group
warnings in 1.14 seconds. The authored selection test originally used 0.55 V, which
did not veto its low-current fixture. The development requirement was corrected to
0.62 V to exercise that veto. This is a disclosed fixture choice, not a frozen
confirmation threshold or an empirical finding.

Executed `python -m examples.utility.rehearse_engineering --output
examples/utility/development/engineering-v1` in the installed interoperability
environment. It preserved source/version identities, six direct/wrapped solve
receipts and native records: 18 physical solves in total, with native driver
success and scenario feasibility. Source hashes and receipt counts were checked
after execution. The generated records contain exposed modeled development outputs.
The exposure register and engineering dossier now preserve that use. No agent,
provider, remote compute or independent confirmation ran. Utility remains
not_attempted. G3 still requires campaign/calibration integration and the other
three task paths. Repository-wide Ruff passed.

## 2026-10-28: supplied-layout wind adapter

Added `examples/utility/wind.py` with immutable internal layout vectors and a
scalar ModelAdapter profile for annual energy (GWh), spacing/boundary checks (m)
and turbine power limits (W). General array ports are not claimed. Catalogue,
baseline rectangle, hardware, wake model, numerical direction grid and source
closure participate in model identity. Unknown layouts, turbine-count changes,
out-of-bound positions and spacing violations reject before wake execution.
Numerical grid variation is not an independent weather scenario.

Added tests for geometry rejection, copied/immutable catalogue inputs and direct/
wrapped PyWake parity. Repository-wide Ruff passed. The installed wind environment
initially lacked both the editable package and PyWake/TOPFARM. With PYTHONPATH=src,
two tests passed and the optional parity test skipped in 0.83 seconds. Actual
module discovery confirmed both optional runtimes absent. No wind scientific
parity or native-comparator qualification is claimed from those two tests.

Started `pixi install --locked -e wind` using the existing dependency lock. The
installation remains running under exec session 10548. The original full default
test run remains live under session 17705 and reached 39 percent with no terminal
result observed. Neither process has been restarted. Native wind comparison,
independent scenarios and complete campaign admission remain outstanding.

The locked wind installation completed successfully. `pixi.lock` was verified
against its pre-install SHA-256 from the engineering rehearsal manifest. The
wind tests then passed with actual PyWake execution: 3 passed in 22.45 seconds.
A compiled dependency emitted a NumPy ndarray binary-size RuntimeWarning. This
warning remains a runtime qualification limit, not a passing compatibility claim.
The corner-layout modeled outputs were added to the exposure register. No
observed production, independent weather, native wind comparator or agent
comparison was tested. The default suite subsequently reached 47 percent and
remains live with no terminal result observed.

## 2026-10-28: observed hydrology and measured solar development paths

Added `examples/utility/hydrology.py` and `solar.py` using the supplied daily
hydrology and subdaily pvlib adapters. Hydrology explicitly preserves soil and
reservoir storage, ET, discharge and initial states, and recomputes daily mass
balance. Both PET alternatives agree with the independent kernel invocation.
Solar preserves measured POA, fixed equipment, transience, gap warmup and common
masks. Its score is AC RMSE in kW, with no energy or advance-forecast claim.
Empty/nonfinite scoring evidence remains insufficient_data. Learned hydrology
is explicitly unsupported until causal training artifacts and conservative
state/flux outputs are admitted. No training was launched.

Three prediction-task tests passed in 6.79 seconds, with nine dependency/oracle
warnings retained (Pandas deprecations and SciPy invalid-division warnings).
Repository-wide Ruff passed after removing an unused import. Ran the bounded
`examples.utility.rehearse_predictions` command with the existing verified solar
cache in the main checkout. It read only exposed June 1-7 2018 solar data and
historically exposed Leaf River development data. No acquisition or cache writes
occurred. Five cases and ten model starts are preserved under
`examples/utility/development/predictions-v1`. Every direct/wrapped parity and
physical check passed. Source hashes, saved cases and start counts were verified.
The SciPy warnings remain visible; finite-output checks passed. This is development
parity evidence, not comparative utility or independent confirmation.

The original full default suite terminated: 1 failed, 1575 passed, 83 skipped in
1234.23 seconds. The sole failure was the legacy shell-command NPZ test, because
its command invokes `python` and the direct interpreter launch had not populated
PATH. Reran that exact test with the default environment bin directory on PATH:
1 passed in 0.92 seconds. No runner/test behavior was changed. The original run
collected before later utility modules/tests were added and cannot qualify them.
No full-suite pass is claimed. Later utility tests need a final consolidated run.
G3 still needs scientific task admission, calibration integration and complete
native/accounting paths. G4-G8 remain outstanding.

## 2026-10-28: immutable suite selection barrier

Added strict `SelectedCell` and `SelectionManifest` records and a hash-linked
suite freeze event. The complete ordered matrix must have terminal child evidence
or explicit not_attempted status. Attempted cells cannot be relabeled unattempted.
Unresolved work blocks freeze. A selected snapshot must be in the frozen candidate
pool, appear in the authoritative successful child evidence, and retain verified
source artifacts in the suite archive. Every child result and manifest is checked
against its original journal, including adverse/no-eligible outcomes.

Once the freeze event commits, subsequent parent selection reservations and starts
are rejected. Freeze is idempotent across interruptions before/after commit.
Changed selections require a new suite, not a mutable projection. Replay verifies
the sealed manifest and selected source bytes, so tampering blocks recovery.

This implements a prerequisite for G5 while G3/G4 integration remains open. No
private scorer, confirmation access intent or label-grant path is enabled. The
suite's confirmation reservations still reject. Privacy isolation, access receipts,
uncertain scoring recovery and comparative confirmation remain unimplemented and
must not be inferred from this barrier. A fully not_attempted manifest can be
sealed for honest evidence delivery but provides no scientific confirmation.

Repository-wide Ruff passed. Consolidated utility contracts/store/controller/costs/
exposure/outcomes/preparation/barrier tests passed: 71 in 18.24 seconds before the
final selected-snapshot attestation check. The barrier suite was rerun after that
check with a selected-model fixture and source-tamper test; final result follows.
No scientific model, agent, provider or confirmation labels were accessed.

Final barrier verification passed: 7 tests in 1.16 seconds after the selected-model
attestation requirement. Source hashes are preserved in
`examples/utility/source-inventory-selection-barrier.json`.

## 2026-10-28: paired analysis and public receipt reconstruction

Added strict `AnalysisPlan`, `ContrastSpec` and `ScoredCell` records with frozen
scientific units/direction, useful gain, confidence, resampling seed, bounded
bootstrap count and multiplicity handling. Paired Student intervals and percentile
bootstrap intervals operate on complete successful feasible pairs. Every assigned
pair remains in feasibility/reliability denominators. Missing/failed values are
never assigned penalty objectives. Known target failures retain censor counts;
unknown target status remains separate. Incompatible scientific units reject.
No global scientific score is calculated across heterogeneous tasks.

Complete evidence failing the required feasible-selection rate yields failed
confirmation. Missing/unresolved evidence or too few valid pairs yields an
inconclusive result. Otherwise the interval must exceed the frozen useful-gain
threshold to support a task-specific effect. Absence of useful gain does not
establish equivalence. Efficiency verdicts remain inconclusive without complete
cost evidence. Time-series dependence and scenario uncertainty remain separate
from variation across paired search repetitions. Their policy identity is bound,
but their estimators still need implementation. Shared baseline score allocation
is not yet implemented; duplicate score references currently reject explicitly.

Added a pinned public-score receipt reader. It verifies hash/size and suite/schema
identity before reconstructing analysis, without models, providers or private data.
These are analysis facilities, not trusted-scoring/private-custody qualification.
Synthetic public envelopes in tests do not establish real confirmation evidence.
Confirmation scoring and its isolation boundary remain outstanding under G5.

Repository-wide Ruff passed. Analysis/outcome/barrier tests passed 20 in 1.31
seconds before adding the pinned-reader test. The final analysis-only result is
recorded below. No scientific or provider executions occurred in this increment.

The pinned-reader test initially expected the duplicate-score error text, but
repeated cells correctly rejected earlier at the unique-cell check. Corrected
the assertion. Final analysis verification passed: 7 tests in 0.89 seconds.
Final repository-wide Ruff passed. Source hashes are in
`examples/utility/source-inventory-analysis.json`.

## 2026-10-28: CLI, bundled fixtures and wheel reader check

Added lazy `utility` CLI commands: validate, prepare, status, freeze, cancel,
report and verify. Preparation accepts strict input records and application-owned
adapter profiles, launches no factory and always reports zero starts authorized.
Read-only status/report/verify reconstruct authoritative journals and preserve
unknown costs. Errors omit input payloads and private paths. JSON and Markdown
reports retain evidence limits. run/resume/confirm remain absent until executable
route and scorer integration exists; their absence is documented, not completion.

Added authored offline suite/selection fixtures and package resource discovery.
Added `docs/utility.md` and updated the documentation index and README scope.
The fixture has placeholder hashes and no scientific admission. Its all-unattempted
freeze demonstrates honest evidence sealing, not confirmation. Real task dossiers
remain blocked. Included utility examples/fixtures in wheel discovery without
bundling raw measured data or the development result trees.

Three CLI tests passed in 1.67 seconds. The documentation command registry test
then identified its expected set missing the new utility group. Updated that
contract. Repository-wide Ruff and final CLI/documentation checks were rerun.
Final result follows. No legacy CLI behavior was altered.

Built a wheel offline with pip --no-deps --no-build-isolation. Build succeeded,
SHA-256 6e932092457e9599ea5a9baedccac06fed812be7e754b506984712d65019e871.
Extracted the wheel to a fresh temporary installation tree, ran from outside the
checkout in isolated Python mode, and asserted imports came from that tree.
Seven offline CLI invocations passed: validate, blocked prepare, status, freeze,
JSON/Markdown reports and verify. No optional Torch/BoTorch/OpenMDAO/pvlib/PyWake/
TOPFARM modules were imported. Minimal fixtures were found through package resources.
This check reused installed base dependencies; it is not a fresh dependency solve
or installed model execution. The first attempt correctly rejected the macOS
/var symlink ancestor, then passed after using the resolved /private path.
The saved result is `examples/utility/installed-offline-check.json`.

G6 is partial: only a local macOS offline-reader wheel check is established.
Linux, a second actual host, installed model runs, complete task/cost integration
and the independent utility matrix remain outstanding. No scientific model or
provider ran in this increment.

The documentation contract also required matching agent command guidance. Added
an explicit utility scope/limits paragraph without granting execution authority.
Final CLI/documentation verification passed: 22 tests in 1.62 seconds. Final
repository-wide Ruff passed. Incremental source hashes are in
`examples/utility/source-inventory-cli.json`.

## 2026-10-28: durable engineering calibration bridge

Added `utility/studies.py`. Its separate EngineeringStudySpec binds the exact
OptimizationRunSpec, engineering acceptance/scenario profile and source identity.
Only deterministic system studies with explicit physical budgets are admitted.
The existing legacy CalibrationSpec and its strict deserialization are unchanged.
The bridge uses OptimizationStudy/ObservationLedger, not an alternate search loop.

A caller-pinned active child batch must reserve all scenario executions for the
maximum fitting matrix. The trusted executor owns scientific execution and must
use existing batch reservations/observations. Each reservation binds the exact
optimizer action, scenario and profile. Missing, mismatched or uncertain physical
work blocks acknowledgement. Scenario order, action configuration, raw scientific
records and feasibility checks are verified before generating optimizer outcomes.
Failures retain explicit statuses rather than penalty objective values.

Saved engineering records and charged reservations are reverified by the public
pending-result resolver. A crash after saving the scientific result does not
invoke the evaluator again. Missing results after dispatch intent block recovery.
Modified saved costs cannot overwrite the physical evidence. An explicit
EngineeringReconciliationRequired signal bypasses the optimizer's ordinary
exception-to-zero-cost fallback. Added OptimizationStudy.release_pending_writer()
to release only advisory ownership after dispatch exits, preserving the pending
action and ledger. Existing recovery semantics perform the actual reconciliation.

Initial tests identified an incorrectly nested batch operation lock, then retained
pending-writer ownership after interruption. The bridge now uses each physical
executor's batch lock and explicitly releases optimizer ownership when yielding
for reconciliation. No lock or accounting requirement was weakened.

Utility bridge plus existing optimizer system/recovery verification passed:
113 passed, 21 skipped in 5.52 seconds. Added missing-result and cost-tamper tests.
Final bridge-only and Ruff results follow. Tests used authored physical callbacks,
not real model calibration. Task-specific campaign/route registration and real
engineering calibration rehearsal remain outstanding under G3/G4. No provider or
confirmation data were used.

Final bridge verification passed: 6 tests in 1.35 seconds after resolving the
registered evaluator factory. Final repository-wide Ruff passed. Source hashes
are in `examples/utility/source-inventory-engineering-study.json`.

## 2026-10-28: real coupled-model calibration rehearsal

Added `examples.utility.engineering_study`: a four-trial Sobol development study
using the intact OpenMDAO adapter, registered source-power outcome, three ground
scenarios and absolute node-voltage feasibility. The child batch reserves twelve
scientific starts and zero host calls. Each synchronous lifecycle execution has
an immutable action/scenario/profile reservation, saved outputs, solver diagnostics,
duration and cleanup observation. OptimizationStudy remains authoritative for
search, fitting costs, explicit statuses and recommendation.

Executed the command into a new `examples/utility/development/engineering-study-v1`
directory. It paused after one trial (three scenario starts), resumed to four trials
(twelve total starts) and added zero starts when run again after completion.
Offline inspection verified source hashes, twelve stopped observations, four
optimizer ledger entries and total charged cost of twelve physical executions.
Trial statuses were success, success, scientific_infeasible, success. The infeasible
trial remains in the ledger and cannot supply the final recommendation. All these
scenario/design results were added to the exposure register.

Fixed bridge propagation of target_value and evaluator duration into the existing
optimizer controller. No legacy calibration schema was changed. This rehearsal
uses trusted synchronous lifecycle execution; it does not qualify subprocess
owner loss, hard time enforcement, private confirmation, or full suite route grants.
It ran no agents, providers, remote compute or independent confirmation. The
scientific utility verdict remains not_attempted.

Added a real-model calibration pause/resume regression test and ran it with the
engineering parity/native-driver and bridge tests in the installed interoperability
environment. Final results follow. G3/G4 remain partial: task-specific route
registration, native wind accounting and the complete route matrix are outstanding.

Final optional engineering/bridge verification passed: 10 tests, four expected
OpenMDAO coupled-group warnings, 2.26 seconds. Repository-wide Ruff passed. The
incremental source inventory is
`examples/utility/source-inventory-engineering-calibration.json`.

## 2026-10-28: bounded native wind comparator

Added `examples/utility/wind_native.py` around native TOPFARM SLSQP and PyWake
with derivatives retained. Wake objective and gradient callbacks each have an
explicit cap enforced before the next callback. Immutable receipts retain entered,
completed and failed work, positions and energy where available. Iteration limits
remain distinct from callback limits. Cleanup runs on normal return and failure.
Budget exhaustion returns its adverse record rather than discarding spent work.
The result validates callback indices, counts and limits. A failed/budget-stopped
run cannot assert feasibility. Final-layout scoring is separately reserved work.

The first native test exposed NumPy scalar values crossing the strict record
boundary. Converted those values explicitly to Python scalars without weakening
the serializer. Final wind verification: 4 passed, 4 warnings in 3.77 seconds.
Warnings remain the known NumPy binary-size warning, upstream pyDOE syntax warning
and TOPFARM deprecation warnings. Repository-wide Ruff passed. These are runtime
qualification limits, not evidence of general dependency compatibility.

Saved a new bounded development rehearsal under
`examples/utility/development/wind-native-v1`. The nominal native run converged
within two iterations with two wake calls and one gradient call. The deliberate
budget control stopped after one wake and one gradient call. Two separately
recorded final-layout evaluations gave baseline and native energy both
37.06343379120568 GWh: zero modeled development gain. Source hashes, recorded calls
and ceilings were independently checked. All results, including the budget stop
and absence of gain, remain saved. Gradient calls contain differentiated wake
work and cannot be added to objective-call counts as interchangeable units.

This uses the exposed four-turbine bundled distribution, not independent weather
or measured production. Added the exposure to the register. No agents, providers,
remote compute or independent confirmation ran. Parent suite integration, process
interruption/timeout qualification and full route comparisons remain outstanding.
G3/G4 remain partial. Source hashes are in
`examples/utility/source-inventory-wind-native.json`.

## 2026-10-28: shared-pool route construction and mechanical ablations

Added `utility/routes.py` with strict ScientificGrant, HostGrant, RoleAllowance,
RouteRecipe, TaskRoute and versioned RoutePlan records. Shared grants bind ordered
candidates, partitions, bounds, acceptance, research corpus, hardware and optional
training profile. Agent routes share model/version, host profile, permissions and
aggregate host allowance. Prompt hashes and individual role caps remain explicit.
Conventional construction retains supplied choices and aggregate numeric limits.
Scientific acceptance is mandatory in every recipe.

Role-removal builders require a frozen mechanical replacement for exactly the
omitted role. Remaining role caps and aggregate allowance do not change. Unused
role allowance remains visible rather than being redistributed. Single-agent
construction has its own explicit prompt and call cap under the same host grant.
These builders do not modify existing Leaf River protocols or worker templates.

Route plans cover the full task/route cross product and reject changed information,
hosts, candidate order, partitions or aggregate allowances. Per-task recipes bind
into suite RouteSpec identities. Matrix expansion persists randomized route order
inside repetition blocks and identical seeds/scenario IDs across paired routes.
A six-route primary/ablation fixture expands to sixty cells over two bounded child
groups, with one scientific grant. It is an authored schema test, not a scientific
or live-host comparison. Plans bind prompt, seed and recipe changes into identity.

Construction is not runtime qualification. Existing broker/scheduler permissions
still need to consume these recipes, enforce individual role caps and execute the
mechanical substitutions. No live role-removal capability is claimed. Shared
physical baseline allocation and private data grants remain open. Repeated logical
baseline cells must not be presented as independent baseline model runs.
G4 remains partial and no run authority is created by a recipe.

Route/contracts/CLI verification passed: 24 tests in 1.92 seconds before adding the
versioned-plan roundtrip test. Final route-only and Ruff results follow. No model,
agent, provider or confirmation execution occurred in this increment.

Final route verification passed: 7 tests in 0.92 seconds. Final repository-wide
Ruff passed. Source hashes are in `examples/utility/source-inventory-routes.json`.

## 2026-10-28: persistent role allowances before host delegation

Added `utility/role_host.py`. RoleBoundHost wraps existing host interfaces and
commits a role permission reservation in the suite journal before delegation.
Replay checks the pinned RoutePlan against the exact frozen route and cell matrix,
active child binding, role inclusion, per-role cap and aggregate host allowance.
Omitted-role requests stop before the delegate is called. Host failures retain
the role charge and invocation IDs cannot be redispatched automatically. Raw
prompts are not copied into these permission receipts; task/prompt identity is
hashed. Existing worker/host journals remain authoritative for physical execution,
transcripts, permission grants, provider usage and recovery.

Wrapper construction verifies child pin, assigned scope, stable qualified host
version, requested model, host profile and prompt-template hashes. Native batch
capabilities include a batch/case suffix. The wrapper accepts only the stable
version or the exact bound suffix, avoiding an impossible circular dependency
between frozen recipes and batch creation identity. Cancellation delegates to the
existing host boundary; no role charge is refunded.

Added role_reserve suite events and explicit role permission counts in offline
accounting reports. Permission reservations are not observed host starts. These
checks cover the current serial writer interface; concurrent thread dispatch is
not qualified. Mechanical ablation handoffs and full broker integration remain
unfinished. The wrapper supplies no private data grant, tool capability or live
host authority. Fake-host tests qualify only the permission/accounting behavior,
not a second actual host implementation.

Combined role-host, suite store, route, barrier and existing scheduler tests passed:
38 in 2.46 seconds. Final role-host/CLI and Ruff checks followed the report update;
results are recorded below. No scientific model, provider or live host ran.
G4/G5 remain partial.

Final role-host/CLI verification passed: 7 tests in 1.87 seconds. Final repository-wide
Ruff passed. Source hashes are in `examples/utility/source-inventory-role-host.json`.

## 2026-10-28: confirmation reservation and access/score journal

Extended the suite journal with separate selection/confirmation phase charges.
Confirmation can reserve only after the full barrier and only for an immutable
selected model. It consumes the frozen confirmation reserve rather than opening
new selection allowance. One confirmation attempt per cell remains permanently
charged. Access and score commits bind the active attempt, exact grant, resources,
partition, outcome contract, selected artifact and selection manifest identity.

Added `utility/scoring.py` as an application-owned scorer accounting interface.
It exposes no private path, evaluator import string, provider or data loader.
Access intent commits before calling the trusted scorer. PublicScore is strict,
finite and bound to the registered outcome name/units. Failed scoring cannot
supply penalty objectives. Private scorer exception text is suppressed while the
access history and allowance remain. A committed score is acknowledged/replayed
without rescoring. Interruption before the score commit remains uncertain and
blocks automatic retry, including an orphaned uncommitted score artifact.

Offline reporting now distinguishes selected child evidence from confirmation
receipts. It can read public scores without invoking their scorer and reports
scored_unanalyzed rather than turning a score into a comparative utility verdict.
The utility verdict remains not_attempted until the comparative evidence path is
integrated. Eligibility/confirmation accounting alone cannot establish utility.

This is not a qualified private scoring execution boundary. The trusted callable
runs synchronously and must be supplied by application code. Kernel/process data
isolation, hard time/resource bounds, score-worker receipt recovery before journal
commit, label-leak canaries through all runtime channels and real custodian access
remain outstanding. No confirm CLI is enabled and no real private data were used.
Tests use synthetic scalar scorers and public fixture models only. G5 is partial.

Suite scoring/barrier/store/role-host/CLI verification passed: 30 tests in 4.07
seconds before the final public-report test. Final scoring/CLI and Ruff results
follow. No model, provider or real confirmation execution occurred.

Final scoring/CLI verification passed: 10 tests in 3.20 seconds. Final repository-wide
Ruff passed. Source hashes are in
`examples/utility/source-inventory-confirmation-accounting.json`.

## 2026-10-28: private scoring worker and resource admission blocker

Added a fixed standard-library JSON-vector RMSE worker and a private macOS scorer
profile using the existing deny-default sandbox, resource wrapper, process
supervisor and owner watchdog. Public predictions bind the selected model and
partition. Labels remain in a separate private directory. The worker imports no
model/provider and emits only the registered scalar score/status. Private errors
are suppressed. Resource reservations must cover timeout plus stop grace. Saved
process completion/public-output hashes support read-only scorer recovery without
reading labels or restarting the process. Kernel isolation for other worker/host
profiles is not implied by this implementation.

Actual synthetic probes failed before worker entry: the existing Darwin
resource wrapper could not set the requested 256 MiB RLIMIT_DATA. A plain
`python -I -S` subprocess attempting the same limit also failed with
ValueError: current limit exceeds maximum limit. No sandbox exception caused it.
The scorer now performs this no-data prerequisite probe and refuses registration
before opening private bytes when it fails. No memory cap was removed or replaced
with an observed quantity. Private scoring is therefore unqualified on this host.
Linux remains unsupported by this macOS profile, with no permissive fallback.

Separated an authored kernel privacy probe from resource qualification. Under the
existing deny-default boundary, an unprivileged workspace was denied access to the
synthetic private label file. That probe deliberately does not admit a scorer or
claim working resource limits. Boundary/scoring verification: 9 passed, 2 skipped
in 2.75 seconds. The two actual full-scorer tests skip only because the required
data-memory limit is unavailable. A separate test proves the admission failure
happens before private file reads.

Standalone worker math/format tests run without claiming OS isolation. They cover
analytic RMSE, no scored samples, invalid private values and absence of a label
canary in stdout/stderr. Private JSON duplicate/unknown fields reject without
printing values. Three tests passed in 0.07 seconds before the final duplicate-key
validation change; final worker/scoring results follow. Repository-wide Ruff passed.
No real confirmation data, host calls or providers were used. The affected scoring
profile remains blocked, while unrelated software work can continue. G5/G6 remain
incomplete and no confirm CLI is enabled.

Final worker/scoring verification passed: 10 tests in 2.80 seconds after private
JSON validation changes. Final Ruff passed. Source hashes and the explicit
resource blocker are in `examples/utility/source-inventory-private-scorer.json`.

## 2026-10-28: shared baseline receipts and confirmation-to-analysis reader

Added strict SharedBaseline allocations across assigned unchanged-baseline cells.
One physical deterministic receipt can support several logical repetition blocks
without duplicating physical starts or cost. Allocations retain complete logical
denominators, require identical outcome/status/metadata, and have exclusive weights
summing to one. Cross-task and adaptive-route reuse reject. A cost-allocation helper
retains one physical quantity with explicit logical shares instead of charging it
a second time or making baseline work free.

Extended public receipt reconstruction with an explicit shared-baseline envelope.
Analysis now reports both logical scored cells and distinct physical score receipts.
Shared values remain one frozen deterministic reference, not independent baseline
replications. Uncertainty continues to describe algorithm repetition variation;
independent observation/scenario uncertainty is a separate unfinished estimator.

Added analyze_confirmation to read only journal-committed public confirmation scores
after the complete selection barrier. It does not invoke a scorer or open private
labels. Optional shared-baseline expansion verifies that all logical selections
pin the same immutable model. Missing comparison scores remain inconclusive with
full assigned denominators. Execution-time baseline sharing and predeclared cost
amortization policy integration remain outstanding. No complete efficiency verdict
or independent confirmation evidence is claimed from these readers.

Initial regression testing found duplicate-source validation had moved ahead of
the existing duplicate-cell check. Restored validation ordering without weakening
either condition. Baseline/analysis/cost tests passed 20 in 1.13 seconds. The final
baseline/analysis/scoring/barrier regression results follow. Ruff passed. No
scientific model, private data, host or provider was used.

Final baseline/analysis/scoring/barrier verification passed: 27 tests in 3.66
seconds. Final Ruff passed. Source hashes are in
`examples/utility/source-inventory-baselines.json`.

## 2026-10-28: observation dependence and scenario uncertainty

Added `utility/uncertainty.py` with strict prediction/scenario uncertainty policies
and a versioned DependencePlan. Prediction policies freeze sample interval, ordered
time support, mask, segment IDs, block length, resampling count, confidence, seed
and development/partition identity. The custodian-side paired RMSE estimator uses
segmented circular moving blocks. It splits at excluded samples, state-segment
boundaries and calendar gaps. Every scored value must be finite. Empty masks,
short segments and too few blocks remain insufficient_data instead of changing
the frozen block length. Only aggregate numbers leave this API.

Scenario policies distinguish a finite fixed-case census from an independent
scenario sample. Fixed engineering cases produce a finite-case mean with no
population confidence interval. An explicitly declared independent sample can
use paired scenario bootstrap. Missing scenarios remain in the assigned count
and prevent interval completion. Neither estimator treats search repetitions as
independent real tasks or combines scientific units across tasks.

Tests cover analytic constant-error intervals, deterministic seeded resampling,
mask/identity rejection, calendar gaps, missing cases, fixed-case versus population
claims, empty/short series and a persistent-error example where moving blocks
correctly give wider uncertainty than sample-wise resampling. Numeric conversion
prevents integer wraparound and squared-loss means are scaled before summation.
No measured data were used in these authored estimator checks.

This is a separate estimator layer. Joining its pinned custodian outputs into
final task-specific verdicts, multiplicity across uncertainty families and final
report/figure reconstruction remain unfinished. Existing repetition analysis is
still explicitly conditional on valid paired search outcomes. No new scientific
utility verdict or real confirmation evidence is established. G8 remains partial.
Ruff and final uncertainty/analysis/baseline results follow.

Final uncertainty/analysis/baseline verification passed: 20 tests in 1.10 seconds.
Final Ruff passed. Source hashes are in
`examples/utility/source-inventory-uncertainty.json`.

## 2026-10-28: executable mechanical role removals

Added `utility/mechanical.py` with source-bound registered replacements for
investigator, implementer and reviewer handoffs. The investigator chooses the
next untried supplied candidate in frozen catalogue order. The implementer uses
the trusted supplied configuration. Mechanical review verifies that mandatory
coded evidence is present, retains failed checks for the scientific controller's
veto and stops if required check evidence is unavailable. No agent invocation or
worker handoff is fabricated for an omitted role.

AblationBroker reuses CampaignBroker scientific transitions, staging, request
identity and recovery. Mechanical receipts commit in the suite journal with the
approved input projection, registered policy and exact output. Replay regenerates
the mechanical result and verifies it against its frozen RoutePlan. The broker
requires a bound RoleBoundHost, an assigned child directory, supplied execution,
matching candidate pool, bounds, data identities and acceptance rules. Child
confirmation must be disabled so it cannot expose data ahead of the suite barrier.
Remaining agent roles retain their original policy and call limits.

Added end-to-end authored-fixture tests for all three removals. Each uses existing
batch physical accounting, the actual campaign controller and scripted hosts.
All three removed the intended host role, retained the accepted scientific
configuration (multiplier 1.5), used exactly two scientific attempts, and added
no host calls when the completed broker advanced again. Mechanical receipts and
child results replayed correctly. These are tiny orchestration fixtures, not
real scientific utility or live-host ablation evidence.

The first integration run rejected an inconsistent fixture worker timeout. Aligned
its declared batch worker timeout/task caps with the existing worker profile;
no runtime boundary was relaxed. The three integration tests then passed in
20.71 seconds. Added missing-coded-evidence/failed-check review tests and ran the
broader legacy broker and utility regression set. Final results follow.
Ruff passed. No live host, provider or independent confirmation ran. G4 remains
partial pending real-task route registration and complete matrix rehearsal.

Final mechanical/role-host/store/legacy broker verification passed: 33 tests in
84.86 seconds. Ruff passed. Source hashes are in
`examples/utility/source-inventory-mechanical.json`.

## 2026-10-28: selected parameter/evaluation identity before route execution

While preparing the generic execution coordinator, found that SelectedCell pinned
only the implementation ModelSnapshot. That omitted calibrated parameter state.
Closed this prerequisite before adding route launch support.

Added SelectedState and selection schema v2. A selected state binds the immutable
model, exact parameter mapping and eligible evaluation. Replacement evaluations
also bind their admitted CandidateSnapshot identity. Evaluation model/configuration
mismatches reject. Freeze requires the selected-state artifact in the authoritative
child's evidence and verifies it during replay, alongside model/source bytes.
Legacy schema v1 remains usable for all-unselected manifests but cannot authorize
an unbound selected model. No historical evidence was overwritten or promoted.

Private prediction envelopes now bind the selection-barrier digest as well as
model and partition. Shared baseline allocation requires the same selected model
and parameter-state artifact for every logical baseline cell. Matching code alone
cannot justify sharing scores from differently calibrated configurations.

Initial barrier/scoring/baseline/CLI verification passed: 23 tests in 3.97 seconds.
Added exact-configuration/model mismatch, selected-state tamper, legacy-unbound
selection and shared-baseline parameter-mismatch tests. Final regression results
follow. Ruff passed. No scientific model, provider or real confirmation ran.
The generic scripted execution coordinator remains outstanding; G4/G5 are partial.

Final barrier/scoring/baseline/analysis/CLI verification passed: 33 tests in 4.06
seconds. Final Ruff passed. Source hashes are in
`examples/utility/source-inventory-selected-state.json`.

## 2026-10-28: trusted scripted campaign execution coordinator

Added `utility/execution.py` with strict ScriptedExecutionPlan/TaskCampaign inputs,
source/lock closure, exact frozen route/matrix identity and explicit development
purpose. ScriptedCoordinator verifies installed core source bytes and registered
prompt hashes before model dispatch. Only trusted supplied prediction campaigns
with exposed data and disabled child confirmation are admitted. Expert/live-host,
generated-code, independent confirmation and unsupported adapter profiles reject.
Candidate pool, bounds, partitions and acceptance remain frozen. Paired cell seeds
are applied consistently to the scientific campaign and deterministic calibration.

The coordinator creates bounded child batches under the existing parent reserve,
uses BatchCampaignController for scientific attempts and BatchScriptedHost receipts
for authored handoffs. Conventional, single-agent, full-role and registered ablation
branches reuse existing controllers/brokers. Baseline-only execution evaluates the
unchanged model. BatchScriptedHost performs no provider call. RoleBoundHost retains
persistent per-role/aggregate caps. No host privileges are created by this profile.

Pause/resume at cell boundaries preserves reservations and child clocks. Completed
cells verify/replay without new dispatch. A started cell is only acknowledged from
finished child evidence; unfinished mid-cell work remains blocked for explicit
reconciliation rather than restarting a runner. This is a retained limit, not full
crash-recovery qualification for the complete route matrix.

Completed cells now archive selected model/source bytes, parameter/evaluation
SelectedState and matching child attestations. selection_manifest reconstructs a
reviewable schema-v2 barrier from authoritative child results. It never scores
confirmation labels. The coordinator does not automatically freeze or confirm.

Two actual tiny supplied-campaign integration tests passed, including a conventional
and multi-role cell, pause/resume, idempotent completed replay, exact selected-state
archival and successful suite freeze: 2 passed in 11.64 seconds. Changed source/plan
inputs reject before dispatch. After moving the archive symlink check ahead of any
directory creation, source-rejection/CLI/barrier tests were rerun; results follow.
Ruff passed. Tests used authored local models and scripted hosts, not real utility
comparisons, paid calls or private confirmation. G4 remains partial pending broader
route rehearsal, public run/resume wiring and real-task registration.

Final source-rejection/CLI/barrier verification passed: 13 tests in 2.17 seconds.
Final Ruff passed. Source hashes are in
`examples/utility/source-inventory-execution.json`.

## 2026-10-28: public scripted run/resume commands

Added utility run/resume with required --scripted-development. The commands load
only the strict scripted development execution profile, verify source/protocol
compatibility, pin the exact execution plan and preserve all parent reservations.
run refuses existing execution state. resume requires its saved matching plan.
Completed cells replay without added starts. Unfinished mid-cell attempts remain
blocked for reconciliation rather than restarting a scientific/host runner.

Completed matrices return a saved selection_proposal artifact. Sealing stays an
explicit separate utility freeze action. Neither run nor resume confirms models,
opens independent data or creates live-provider authority. Help and current guide
state the prediction-campaign/development scope. Real engineering/wind coordinator
profiles and full interruption recovery remain outstanding.

Tightened preflight by deriving numerical-recipe identity from the supplied
campaign queue, baseline, interventions, calibration, workflow, execution limits
and paired-seed rule. Mismatches reject before model dispatch. Worker timeout,
elapsed and workspace bounds must fit the child batch. Frozen prompt hashes
are checked against the actual registered templates.

The CLI integration test completed one cell, resumed the second, rejected a
second run command, added zero work on repeated completed resume, and returned
an unsealed selection proposal. It passed in 14.55 seconds before the final
numerical/resource checks. Final execution/CLI/documentation verification passed:
26 tests in 25.64 seconds. Repository-wide Ruff passed. The authored local fixtures
used no provider, live host or private confirmation data. G4 remains partial.


## 2026-10-28: scripted recovery after a saved scientific response

The scripted coordinator now reopens an interrupted cell's original campaign and
worker journals. It verifies the paired input bytes, campaign specification and
worker identity. Campaign recovery and batch reconciliation read original
physical stop evidence before the broker can advance. A saved scientific response
can therefore complete its interrupted worker acknowledgement without repeating
the baseline model evaluation. Parent allocations, child and worker clocks,
scientific request IDs and physical receipts remain unchanged.

This is a narrow recovery profile. Pending worker invocations, pending source
preparation, unsettled physical reservations, missing journals and changed inputs
still block execution. Cancelled/frozen suites cannot resume unfinished work.
Finished child cases can still be acknowledged without running their campaign.
The suite controller's generic dispatch continues to reject started attempts.

Fault injection interrupts conventional and multi-agent cells immediately after
the baseline scientific response is saved. Both resume with the same first
physical receipt and exactly two scientific starts total. Negative tests retain
an unresolved host reservation and reject cancellation without adding batch events.
Execution/controller/CLI/documentation checks passed: 40 tests in 67.75 seconds.
After adding the cancellation test, both final refusal tests passed in 11.24
seconds. Repository-wide Ruff passed. No live host, provider or independent
confirmation was invoked. G4 remains partial; G5/G6 and scientific utility remain
unqualified. Source hashes are recorded in
`examples/utility/source-inventory-scripted-recovery.json`.


## 2026-10-28: bind dependence uncertainty to comparative verdicts

Closed a verdict gap: repetition intervals alone could previously support a
scientific-gain label without the separate observation/scenario evidence. Legacy
utility-analysis-v1 records keep their exact serialized fields and digest. Their
repetition result is now a diagnostic; their final scientific verdict remains
inconclusive without a declared combined decision policy. Complete failed
feasibility evidence still yields failed_confirmation.

Added utility-analysis-v2 with the frozen all_paired_lower_bounds rule. Public
PairedDependenceEvidence records bind the exact route/comparator cells and score
hashes to a task dependence policy. Readers reject altered gains, stale policies,
duplicate/unpaired receipts, mismatched units, insufficient family confidence and
changed partitions. BoundScenarioUncertaintySpec adds a versioned partition hash
for full forcing/scenario manifests while preserving the older diagnostic schema.
Prediction policies already bind their partition and frozen time support.

A positive scientific verdict needs complete feasible pairs, the adjusted
repetition lower bound above the useful threshold, and every paired dependence
lower bound above it. The nominal family error allowance is split equally across
the two uncertainty sources, then across contrasts, regimes and assigned pairs as
applicable. Fixed scenario censuses supply exact finite-case gains and no
population interval. Their claim is restricted to those cases. Wide repetition
intervals crossing the useful threshold remain inconclusive. Missing or
insufficient dependence evidence cannot support a gain verdict.

Offline readers consume pinned public aggregates and do not call resamplers or
open private arrays. They retain both uncertainty sources separately. These
records do not qualify a custodian, private execution boundary or real-task
confirmation. Trusted custodian production and admission remain outstanding.
Efficiency and role-retention decisions remain incomplete.

Final focused analysis/uncertainty/scoring/CLI/documentation checks passed: 66
tests in 3.83 seconds. Repository-wide Ruff passed. A broader intermediate utility
run passed 157 tests with 9 skips in 98.39 seconds before the final partition-bound
scenario additions. The final broader run and source inventory follow below.


Final utility regression command:
`PATH="$PWD/.pixi/envs/default/bin:$PATH" .pixi/envs/default/bin/python -m pytest tests/test_utility*.py -q -rs -p no:cacheprovider`.
Result: 158 passed, 9 skipped in 92.44 seconds, exit 0. Skips were four OpenMDAO,
one pvlib, two actual macOS data-memory-limit qualification blocks, one PyWake and
one TOPFARM check. Process-inspection access was enabled for physical-stop tests.
No skip establishes support for that runtime or private-scoring profile. The
standalone offline import check loaded none of Torch, BoTorch, OpenMDAO, PyWake
or pvlib. Full default, optional-environment and installed-wheel checks were not
rerun in this increment. Source hashes are in
`examples/utility/source-inventory-dependence-decisions.json`. G5/G8 remain partial.


## 2026-10-28: offline comparative tables and reconstruction exports

Added strict ReportSpec references for frozen analysis, optional dependence
policies/evidence and explicit shared-baseline allocations. Comparative reporting
requires the sealed complete selection barrier, reads committed public scores and
preserves every assigned cell. Selection status explains why confirmation may be
unavailable. Contrast denominators and failure counts remain those of the scored
evidence. No model, scorer, resampler or provider is called by the reader.

Added report --inputs and --export-directory, plus verify with matching options.
Existing accounting-only commands retain their behavior. New exports contain
report.json, summary.md and eight CSV tables: cells, paired effects, contrasts,
failure counts, physical costs, cost allocations, role permissions and dependence.
Unknown quantities stay blank. Physical receipts appear once in the physical-cost
table. Allocations retain the original physical quantity for reference and a
separate exclusively allocated quantity. Permissions are not counted as starts.

Exports require an absent directory without symlink ancestors. Their manifest is
written last. Verification reconstructs every byte from current authoritative
suite evidence, then checks the manifest and actual files. Tests reject tampered
numbers even when their export hashes are updated. Later journal changes require
a new export; historical-prefix reconstruction remains unimplemented.

Reporting tests cover missing/no-eligible selections, uncertain confirmation
access, stale policy/source artifacts, shared costs, blank unknowns, overwrite and
symlink refusal, changed journal heads and CLI reconstruction. One initial test
incorrectly expected an unattempted status where the authored selection had no
eligible model; the expectation was corrected to preserve the recorded outcome.
Final focused reporting/CLI/analysis/dependence/documentation checks passed: 52
tests in 5.40 seconds. Final utility regressions passed: 166 tests, 9 skips in
96.34 seconds. The skips were four OpenMDAO, one pvlib, two blocked actual macOS
data-memory-limit qualifications, one PyWake and one TOPFARM test. Repository-wide
Ruff and the installed-check script's Ruff check passed.

Built a wheel offline with pip wheel --no-deps --no-build-isolation --no-index
--no-cache-dir. SHA-256:
2030dccb0959afd720d5a6c9b98f6da3e80e78df122f1aa6e874d4b7070ac75c.
A fresh extraction outside the checkout passed seven CLI operations under Python
-I, using invoking-environment dependencies and a two-cell synthetic unattempted
fixture. Subprocess launch and socket connection/bind operations were denied
before package import. Ten exported files were reconstructed. Optional model
frameworks were absent from sys.modules. Wheel reporting/CLI bytes were also
compared directly with current sources. This is offline reader qualification,
not an isolated dependency install or installed model execution. The initial
macOS temporary /var alias was rejected by confinement; resolving the temporary
root fixed the check without changing confinement. Evidence is retained in
examples/utility/installed-report-check.json and the reproducible script is
scripts/utility_installed_report_check.py.

Complete confirmation/training/solver/human cost joining, constraint/residual
exports, task plots, actual independent four-family results and the final G8
audit remain outstanding. No scientific, efficiency or role-retention gain is
claimed. Source hashes are in
examples/utility/source-inventory-comparative-exports.json. G6/G8 remain partial.


## 2026-10-28: optional scientific report figures

Added lazy Matplotlib rendering for comparative exports. report --figures emits
SVG/PNG plots plus exact figure-data.json and the existing tables. Paired-effect
plots retain raw valid-pair gains, repetition means/intervals, outcome units,
minimum useful gain, full assigned denominators and the computed verdict.
Observation/scenario dependence intervals have their own figures and frozen
confidence/method labels. Assignment status plots retain every cell, including
failures and unresolved/missing evidence. Roles can be shown through their frozen
contrasts, but no role-retention decision is inferred from a plot. Total-cost
comparison remains explicitly blocked rather than plotting an incomplete proxy.

The rendering profile pins the renderer source, Matplotlib/Freetype versions,
width and resolution. Style uses a light background, earth tones, status hatching
and local plotting defaults. Figure data can be reconstructed in the base
environment without importing Matplotlib. Normal verification labels image/hash
agreement only internally_consistent and image_rendering not_repeated. Optional
--rerender-figures checks the rendering profile and compares regenerated image
bytes. A test alters an SVG and updates its hash: numeric-only verification
retains its stated limit, while explicit rerendering rejects the change.

Rendered authored illustrations at 8-inch and 5-inch widths in the existing wind
environment (Matplotlib 3.11.1, Freetype 2.14.3). Inspected paired-effect, assignment
and dependence PNGs for labels, clipping, units, legends and captions. The first
visual check had six valid pairs alongside timeout statuses from a separate
illustration. It is retained under figure-rehearsal-v1 with INVALIDATED.md.
The replacement figure-rehearsal-v2 uses the same scored-cell statuses for effect
and assignment plots and includes the separate dependence example. No illustration
represents an executed utility experiment. The narrow SVG label test initially
assumed wrapped text was one XML element; it now checks combined visible text.
The first font-cache initialization reported unavailable system cache directories;
rendering completed with the explicit temporary Matplotlib cache and bundled font.

Base utility regression: 168 passed, 13 skipped in 111.86 seconds before the final
two refusal/image-tampering test additions. Skips included the four optional
Matplotlib checks, four OpenMDAO checks, one pvlib check, two blocked actual macOS
private-scoring data-limit checks, PyWake and TOPFARM. Final optional rendering,
reporting, CLI, dependence and documentation checks: 52 passed, 1 skipped in
10.39 seconds. The skip checks the base profile where Matplotlib is absent.
Final base figure/documentation checks: 22 passed, 5 optional-renderer skips in
2.30 seconds. Repository-wide Ruff passed. A separate Python -I base-reader check
reconstructed a 15-file public authored export with Matplotlib unavailable and
process/network calls denied. Evidence is figure-reader-check.json. This was a
source reader check; installed-wheel qualification was not repeated here.

No models, private arrays, providers or independent confirmation were used by the
figure renderer/readers. Complete-cost, constraint/residual, time-series and real
scenario-physics views remain outstanding. G8 remains partial. Source and rendered
artifact hashes are in source-inventory-figures.json.


## 2026-10-28: declared human-effort receipts and frozen efficiency rule

Added EffortPlan, explicit phase/work scopes, exclusive cell shares, permitted
measurement methods and a frozen amortization horizon. HumanTimeSource records
contain actor hashes, activity, method and UTC epoch windows. HumanTimeLog binds
those exact source fields to a scope. The reader verifies public artifacts,
rejects duplicate evidence and overlapping positive windows for the same actor,
and keeps timer versus self-reported work separate. It never observes a person
or measures time automatically. All checks used authored synthetic logs.

EffortClosure requires explicit logs, including zero-duration logs for zero work.
Absent closures, unknown time and incomplete coverage yield null total effort.
Partial known measurements remain visible. Common setup and one-time integration
are allocated once, with distinct first-use and amortized totals. The policy must
cover every assigned cell and is frozen before results through its digest.
Declared closure cannot independently prove that no human work was omitted.

Added utility-analysis-v3 (EffortAnalysisPlan) and a frozen EffortCriterion for
each contrast. It requires scientific noninferiority in the task's outcome units,
full paired/dependence coverage and a useful human-effort saving. The nominal
error allowance is divided among repetition, dependence and effort intervals,
then across the existing contrast/regime/pair family. Legacy v1/v2 serialized
records retain their fields and identities. A supported human result is labeled
with efficiency_basis declared_logged_human_effort and units person-s. It does
not support a computational/monetary efficiency or role-retention claim. Total
physical-cost evidence stays incomplete.

Added utility-report-inputs-v2 (EffortReportSpec) with pinned EffortInputs and
scope closures. Existing report/verify --inputs commands deserialize both input
versions. Exports add effort cell, allocation and paired-saving CSVs, plus scoped
human statistics in JSON/Markdown. Source fields cannot be changed by updating a
projected log alone. Changed methods, horizons, sources or criteria reject against
the original frozen identity. Existing figure readers now accept the v3 analysis
and its three-part confidence allocation. Earlier saved figure rehearsals retain
their historical renderer hash; new exports pin the current source.

Tests cover exclusive allocation, first-use/amortized conservation, unknown and
missing logs, forbidden self-reporting, original-source mismatch, actor overlap,
duplicate references, explicit zero effort, no saving, scientific degradation,
missing dependence, and the stricter nominal uncertainty family. The positive
synthetic example has unchanged scientific quality and lower declared logged
effort. Missing evidence or degraded quality prevents that synthetic efficiency
label. CLI exports reconstruct the logged quantities without confirmation or model
execution. Optional rendering tests also reconstruct v3 report image bytes.

Verification: full utility regressions passed 180 tests with 14 skips in 100.22
seconds. The skips were four OpenMDAO, five Matplotlib, one pvlib, two blocked
actual macOS data-memory-limit private scoring checks, PyWake and TOPFARM.
After the final v3 image-reconstruction test branch, base focused tests passed
63 tests in 6.28 seconds. Wind-environment figures/effort checks passed 18 tests,
with one inverse base-profile check skipped, in 6.78 seconds. Ruff passed across
src/tests/examples. A fresh effort-reader import loaded no optional model or
plotting framework. Installed-wheel, full default and other optional-environment
checks were not rerun in this increment.

This advances the human-accounting portion of G2/G8. Actual human records,
complete computational/monetary accounting, four-family independent confirmation,
second-host/Linux qualification and the final completion audit remain outstanding.
No actual efficiency gain is claimed. Source hashes are in
examples/utility/source-inventory-human-effort.json.


## 2026-10-28: full local checks and installed-execution packaging repair

Created docs/reviews/part-5-completion-audit.md as an explicitly incomplete,
requirement-by-requirement audit. It preserves the full objective and distinguishes
admission, software, execution, privacy, platform, accounting and scientific claims.
The next execution dependency is a source-closed supervised engineering scenario
executor: the current trusted synchronous callback does not enforce its own timeout
or recover a partially dispatched scenario set. It must not be relabeled as a
prediction campaign by fabricating observations.

Executed the full default and Bayes suites on unchanged runtime/test bytes. Default:
1,711 passed, 97 skipped in 1,397.03 seconds. Bayes: 1,767 passed, 45 skipped,
44 warnings in 1,567.98 seconds. Both exited 0. The default process appeared stationary
while CPU-active during the expensive process/conformance tests; it subsequently
advanced and completed without restart. The suites overlapped for part of their
runtime, so their durations are not a performance comparison. Recorded source and
configuration fingerprints for 689 files were unchanged through both completions.
Some raw pytest skip locations retain earlier worktree path strings; raw logs were
preserved verbatim. The active checkout remains b393726 with prior work intact.

The documented interoperability matrix passed 109 tests with 4 warnings in 14.21
seconds. Utility engineering/prediction/study tests in that environment passed 13
tests with 13 warnings in 3.34 seconds. Utility wind tests passed 4 tests with 4
warnings in 19.51 seconds. Optional commands used one numerical thread. Retained
warnings include OpenMDAO atomic nonlinear groups, pandas/pvlib/SciPy behavior,
a PyWake NumPy ABI-size warning, pyDOE2 syntax and TOPFARM deprecation. Qualification
is limited to the tested subsets. No frozen benchmark matrix was rerun.

Added scripts/utility_installed_model_check.py for a retained installed smoke. The
first local wheel failed at the import probe: examples.campaign_contracts was not
packaged. That attempt started zero models and is preserved as failed evidence.
The repair includes the existing authored fixture package and small JSON/YAML
inputs. It was tested in a staging copy while Bayes ran, then applied to pyproject
only after both full suites completed. No source/test Python changed. Before/after
TOML copies retain this packaging-only difference. The final worktree wheel was
rebuilt and tested independently of the staging wheel.

The final smoke installs the local wheel without dependency downloads into a new
temporary venv that inherits invoking-environment dependencies. The producer uses
the existing repository fixture; all execution runs outside the checkout. Module
imports are checked under that venv. Two cells complete with four supervised model
invocations; saved commands use the installed interpreter and have successful,
verified stop receipts. Completed resume adds no model work. Separate freeze,
report, verify and status operations pass. Independent confirmation and providers
are not invoked. The guarded offline wheel reader also passes seven operations,
reconstructing ten files with model/network/process dispatch blocked. Final wheel
SHA-256: d24cd78afc8673b390b5993302ee00bf4245976bb255449234c991b50f2fa417.

Final documentation checks passed 19 tests in 0.95 seconds. Ruff passed for
src/tests/examples and the new installed check script. Raw logs, JUnit, environment
versions, failed/final wheels, original installed failure, and full installed-smoke
journals are retained under examples/utility/verification-v1. Temporary venvs are
removed after each check; retained journals are offline evidence, not permission
to relaunch or rewrite a completed study. Source and evidence hashes are in
examples/utility/source-inventory-full-verification.json.

These checks advance local macOS G6 coverage and detect/fix a real packaging gap.
They do not supply an independent real task, a qualified private scorer, a Linux
runtime, a second actual host, complete physical costs, real human logs or actual
scientific/efficiency gains. The full objective remains incomplete and active.

## 2026-10-28: supervised engineering scenarios and partial recovery

Added EngineeringExecutionSpec, a fixed engineering worker and
SupervisedEngineeringExecutor. Each trusted supplied scalar scenario reserves
through the existing batch before process launch. Owned supervision bounds timeout
and output, watches the parent and retains stop evidence. Reservations allow five
seconds beyond scientific timeout for stopping/supervision. This is not a
filesystem, network or memory sandbox and is not a private scoring profile.

The immutable binding includes ordered forcing, registration, complete declared
source directory, lock, limits, interpreter, host environment and installed package
versions. Static registration checks do not import parent packages. The worker
rechecks the original binding before importing supplied code. Preflight failures
remain infrastructure_failure, supplied-code errors become model_failure and
expired processes remain timeout. Missing outcomes remain missing. Solver work
requires explicit units and valid counters. Native coupled circuit solving and
derivative work remain intact.

EngineeringStudy binds the supervised executor into optimization recovery.
Default reconciliation only reads verified original process results. Explicit
resume_scenarios=True may continue never-reserved scenarios of the original pending
action, including during constructor reconciliation. It never relaunches an
existing reservation. Unknown original starts remain charged and block retry.
The legacy synchronous callback retains its previous behavior and does not gain
process timeout enforcement.

Retained exposed rehearsals in development/engineering-supervised-v1 and -v2.
The final v2 record has two Sobol designs over three already exposed ground-voltage
scenarios. Reopening after the first design preserves three reservations. The
completed run has six successful, verified stopped processes. Repeated completed
resume adds zero reservations. Checked 173 captured runtime/example/lock files
against current bytes. Recorded modeled outcomes, required checks and native
solver diagnostics. The utility verdict remains not_attempted. Added an exposure
record rather than treating the repeated development scenarios as independent.

Final regression checks: all utility tests plus optimization recovery/run-spec
tests passed 304 tests, with 15 skips, in 122.23 seconds. The optional engineering
process/domain/study subset passed 23 tests with 4 existing OpenMDAO warnings in
21.10 seconds. Documentation passed 19 tests in 0.62 seconds. Ruff passed for
src/tests/examples and the installed-check script. Raw logs and JUnit are retained
under examples/utility/verification-engineering-v1. Skips preserve the unavailable
optional models/rendering and actual macOS private-scoring data-memory limit.
Earlier full default/Bayes and installed-wheel results predate these runtime/test
changes and were not rerun for this increment.

Updated the interim completion audit. Engineering campaign/controller and route
registration are now the next execution dependency. Independent real-task
admission, wind route integration, full matrix rehearsal, private scoring,
Linux/second-host qualification and complete costs remain open. No scientific,
efficiency or role-retention benefit is claimed. Increment hashes are in
examples/utility/source-inventory-engineering-process.json.

## 2026-10-28: engineering scientific controller and exact selection

Added EngineeringCampaignSpec and EngineeringCampaign above the existing
supervised scenario executor. Registered baseline and fixed designs use the frozen
search space. Calibration reuses EngineeringStudy and its original numerical
ledger. The existing EventStore owns request/result commits and selection, while
batch receipts remain authoritative for physical work. One case binds one campaign
identity and location. A second controller cannot expand its grants or rebind it.

The JSON tool boundary supports state, fixed evaluation, calibrated evaluation,
review, freeze and cancellation when no request remains unresolved. Configuration
overrides, executable request fields and confirmation operations are rejected.
Scientific request intent precedes dispatch. Lost acknowledgements replay their
original response. Interrupted fixed or numerical requests recover only original
completed work by default. Explicit scenario continuation can launch never-reserved
work under the original request. Unknown starts stay charged. Empty directories
from before durable intent can recover without inventing a physical attempt.

Replay checks the registered model/configuration, execution binding, original job,
forcing, score, status and elapsed time against batch evidence. Review applies the
existing engineering gain, secondary-outcome and required-check rules. Selection
uses the exact model, configuration and evaluation in SelectedState. A failed
baseline can freeze an explicit no_eligible_model outcome without selected state.
Opening without an executor permits offline reads and original-response replay,
but refuses new mutations. Native solver diagnostics retain their explicit units.

The first controller test incorrectly expected an alternative to win despite the
authored 1 W minimum gain and less than 1 W improvement. Corrected that assertion
to require baseline retention. The criterion and implementation were unchanged.
Focused controller tests subsequently passed 12 tests in 41.30 seconds.

Retained engineering-campaign-v1 as the earlier exposed controller rehearsal.
The final engineering-campaign-v2 includes the case ownership binding. It runs
the 0.1 A baseline, supplied 0.03 A design and two Sobol designs over the three
already exposed ground-voltage scenarios. It preserves twelve stopped processes,
four evaluated designs, a scientific decision and frozen state. Reopening after
baseline retains three reservations. Replaying the original request after freeze
adds none. A guarded reader in the base environment reconstructs the same decision
and selected state with process, network and scientific registration imports
blocked. Compared 174 captured runtime/example/lock files with current bytes.
Recorded this repeated development exposure explicitly. Utility remains not_attempted.

Final checks: all utility tests plus optimization recovery/run-spec tests passed
316 tests with 15 skips in 169.39 seconds. The optional engineering controller,
process, domain and study subset passed 35 tests with four existing OpenMDAO
warnings in 61.16 seconds. Documentation passed 19 tests. Ruff passed for
src/tests/examples and the installed-model check script. Raw logs, JUnit and
commands are under examples/utility/verification-engineering-campaign-v1. The
default and optional runs overlapped, so their durations are not performance
comparisons. The earlier full default/Bayes suites and installed wheel predate
this controller and were not rerun for this increment.

Engineering route brokers, utility-coordinator/public-CLI wiring and conventional
native-driver orchestration remain incomplete. Wind integration, independent task
admission, qualified private scoring, Linux/second-host execution and complete
costs also remain open. No scientific, efficiency or role-retention gain is
claimed. The full goal stays active. Source/evidence hashes are in
examples/utility/source-inventory-engineering-campaign.json.

## 2026-10-28: supervised native circuit tool and separate inner work

Added NativeDriverSpec, a fixed native worker, supervised execution/report records
and engineering campaign schema v2. Existing v1 campaign fields and identities
remain unchanged. The native registration and its complete source/environment
binding are checked before supplied import. Owned supervision bounds elapsed time
and output. Lost process acknowledgements recover original receipts. Unknown starts
stay charged and cannot launch again. Fixed owner-private parent creation before
any scientific launch after the initial test exposed a directory-mode failure.

The native tool has a separate iteration and inner model-call ceiling. One batch
reservation represents the outer driver process, not one inner model solve. The
qualified circuit callback passes its limits into the existing SLSQP recipe, which
refuses an additional model call before exceeding its cap. An instrumented optional
test confirms one actual entry under a one-call optimization allowance. Arbitrary
new callbacks are not qualified by the generic result validator. No filesystem,
network or memory sandbox is claimed.

Successful native output supplies only a configuration. Fresh scenario jobs apply
the original acceptance rules before it can enter selection. Failed native work
commits an explicit report without an eligible candidate. Default pending-request
recovery cannot start the missing followup jobs. Explicit continuation reuses the
completed native process and starts only never-reserved scenarios.

Native records distinguish shared-problem snapshots from independent scenario
calls. Added a final driver snapshot after discovering derivative work can occur
after the last nonlinear solve. Result schema v2 requires it. The final circuit
run records 250 driver derivative calls, versus 245 in its last solve snapshot.
Legacy result v1 stays readable without changing its identity or inventing the
missing final counters. Cost exports keep outer starts, inner model calls, final
driver derivatives and independent scenario derivatives separate. Missing inner
results remain unknown after failure or timeout.

Retained engineering-native-v1 with the earlier result profile and -v2 with the
final snapshot. The final exposed rehearsal has sixteen stopped outer processes,
twelve inner native model calls and five evaluated designs. Original-request replay
adds no reservations. The native process succeeded, but fresh low-ground voltage
was 0.6199999999999917 V against the strict 0.62 V requirement. Its lower power did
not make it eligible. Selection retained the supplied 0.03 A design. No threshold
changed. A guarded base-environment reader reconstructs the original decision,
selection and native cost quantities with process, network and scientific imports
blocked. Compared 177 captured runtime/example/lock files with current bytes.
The exposure register records these already exposed assumptions. Utility remains
not_attempted.

Final runtime checks passed 329 utility/recovery/run-spec tests with 16 skips in
191.43 seconds. The optional engineering subset passed 49 tests with three OpenMDAO
warnings in 83.65 seconds. A subsequent test-only addition covers interruption
after native completion and before fresh scenario work. The final native test file
then passed 14 tests with one optional skip in 23.86 seconds. No runtime source
changed after the broader checks. Documentation passed 19 tests, and Ruff passed.
The default and optional runs overlapped, so times are not performance comparisons.
Raw logs, JUnit, reader code and commands are retained under
examples/utility/verification-engineering-native-v1. Earlier full repository
default/Bayes suites and installed wheels predate this increment and were not rerun.

The native scientific tool now exists for the exposed circuit. Conventional and
agent route brokers still need to use it through shared grants and the utility
coordinator. Suite cost joins, public CLI wiring, wind integration, independent
task admission, qualified private scoring and Linux/second-host qualification
remain open. Engineering readers also retain original absolute campaign/job
locations, so portable archive relocation remains unqualified. No scientific,
efficiency or role-retention utility is established.
The full goal remains active. Increment hashes are in
examples/utility/source-inventory-engineering-native.json.

## 2026-10-28: engineering route brokers and seven-route rehearsal

Added EngineeringBroker over the existing scheduler, worker grants and durable
CampaignAction requests. Baseline and conventional recipes call the same
engineering controller. Conventional execution includes the registered native
driver. The single-agent path creates only single_agent tasks with bounded
normalized history. The four-role path keeps separate contexts. Summaries expose
the frozen parameter domain, scalar scenarios, declared model-port/outcome units,
recipe limits and original evaluation evidence. Workflow phase and scientific
state remain distinct. No source patch or configuration override is admitted.

The three role removals use existing parent-bound mechanical policies. Omitted
roles create no host task, and their allowance is not redistributed or refunded.
Paired seeds are applied to scenario and numerical execution while preserving
the frozen recipe identity. Each calibration result receives review. Valid
advisory stops remain completed handoffs, rather than malformed output eligible
for automatic repairs. Scientific checks still veto ineligible candidates.

Engineering cancellation now has an independent inbox. Worker deadlines forward
both revocations, and scientific/native supervisors observe them. Original charges
and process-stop evidence remain. Caller-supplied revocation predicates are
preserved. Default pending-request recovery reads completed original work.
Explicit advance(resume_scenarios=True) continues only never-reserved work. A
focused test verifies one completed baseline scenario stays counted once while
the original pending request continues to a frozen selection.

Initial fixture checks exposed insufficient host/transcript allowance and an
unused zero-allowance case. Corrected those fixtures. Corrected the new broker's
CandidateBrief field mapping to the existing candidate_id contract. The initial
broker suite then passed 14 tests in 118.61 seconds. The first seven-route circuit
rehearsal completed with scripted advice. Review found missing public domain and
recipe details, which were added before the final qualification.

The expanded-summary prerequisite caught a nonexistent BudgetSpec.to_dict call.
The broader checks had been launched before that failure was inspected. Stopped
their identified owners with exit 143, retained partial logs and fixed the summary
to use the existing StudySpec serialization. The isolated prerequisite then
passed. The failed -v2 rehearsal retains its sources, parent/child/worker journals,
two finished cells and no pending physical work. Its console was overwritten when
starting -v3, so that traceback is unavailable. This evidence limit is recorded in
verification-engineering-broker-v1/interrupted-runs.json. No stopped check is
counted as passing, and no earlier output directory was reused for new execution.

The final exposed engineering-routes-v3 rehearsal completed seven cells through
the existing parent/child stores. All share one paired seed and the same supplied
choices. It records 99 stopped scientific processes, 85 scripted host calls and ten
mechanical substitutions. The baseline retains 0.1 A. All adaptive scripted routes
select the supplied 0.03 A configuration. These are code-path results, not LLM or
independent scientific utility. Native inner work remains a separate quantity:
six driver jobs record 72 inner model calls. The 150 reserved host allowances are
not replaced by the 85 observed calls. No selection barrier or confirmation
access was performed.

A guarded base-environment reader reconstructs all seven parent/child results,
selections, paired seeds, summary domains, omitted-role tasks and reserved budgets
with model imports, physical dispatch and network blocked. Compared 179 captured
runtime/example/lock files with current bytes. Recorded the repeated exposed use.
The producer is an explicit development script, not a declarative coordinator or
public run/resume implementation.

Final runtime checks passed 345 utility/recovery/run-spec tests with 16 skips in
374.83 seconds. The optional engineering subset passed 65 tests with three
OpenMDAO warnings in 236.95 seconds. A later test-only addition for partial broker
continuation passed in 16.27 seconds. Runtime/example bytes were unchanged after
the broader checks. Documentation passed 19 tests, and Ruff passed. The final
rehearsal and two check environments overlapped, so times are not performance
comparisons. Raw logs, JUnit, guarded reader code and commands are retained under
examples/utility/verification-engineering-broker-v1. Earlier full repository
default/Bayes and installed-wheel results do not cover this runtime increment.

Next: declarative engineering execution plans, reusable utility-coordinator/public
CLI wiring and suite-level selected-source/state export. Wind integration, four
independent admitted families, complete cost/effort evidence, qualified private
scoring, Linux and a second actual host remain open. No scientific, efficiency or
role-retention benefit is established. The full goal stays active. Increment
hashes are in examples/utility/source-inventory-engineering-broker.json.

## 2026-10-28: declarative engineering plans, CLI and suite selection export

Added ScriptedEngineeringPlan and its coordinator over the existing child-batch
scheduler. Plans embed native-enabled engineering campaigns, shared source/lock
closure, route matrix, worker/batch limits and a pinned interpreter/package
identity. Validation imports no supplied model registration. It rejects runtime,
source, task/outcome/scenario, recipe, role-template and host-grant drift before
dispatch. This profile remains exposed scalar engineering with scripted advice.

Grouped-case tests found legacy scenario/native permission IDs collided when
paired routes shared one batch. Added execution schema v2 with case-scoped physical
identities. Existing v1 formulas and records retain their meaning. The new plan
requires explicit v2 preparation, rather than relabelling an existing ledger.
EngineeringStudy and offline campaign readers validate the appropriate identity.
Interpreter and installed package versions are fixed before allocation as well as
in existing per-case execution bindings.

Extracted selected-state archiving and scientific-allowance hooks from the existing
prediction coordinator. Prediction behavior and artifact bytes remain covered by
its existing tests. Engineering completion archives verified model sources and
exact parameter/evaluation state, with matching child evidence for suite sealing.
The public utility run/resume commands select the versioned plan by schema and pin
its exact bytes. Default recovery reconciles original completed work. Engineering
resume accepts --continue-pending-scenarios for never-reserved work under the
original pending request. Prediction plans reject that flag. Unknown starts stay
charged and cannot be redispatched. No model/worker journal is replaced after
scientific work.

The focused engineering/prediction execution set passed 17 tests in 142.52 seconds.
It covers grouped permissions, native-job separation, cell boundaries, saved
scientific responses, interrupted archiving, explicit continuation, source/runtime
drift and the public CLI. Final utility/recovery/run-spec checks passed 356 tests
with 16 skips in 467.68 seconds. The optional engineering subset passed 76 tests
with three OpenMDAO warnings in 332.36 seconds. Documentation passed 19 tests, and
Ruff passed. The final rehearsal and test environments overlapped, so durations
are not performance comparisons.

The public producer engineering-plan-v1 uses one child batch and seven paired
cells over the already exposed circuit scenarios. Six owned CLI operations run
one cell, resume six, check completed resume, separately freeze, verify and inspect
status. It preserves 99 stopped scientific processes and 85 scripted host calls.
Completed resume adds zero cells. All seven exact selections are sealed. No
confirmation access or provider call occurs. This remains scripted development,
not independent scientific or LLM utility evidence.

A guarded reader in the base environment validates the sealed manifest, original
child/campaign results and all selected source bytes. Scientific imports,
physical/network dispatch and reads from the original source root are blocked.
Public verify/status also pass under those guards. Compared 180 captured
runtime/example/lock files with current bytes. Recorded this repeated exposure.
Raw logs, JUnit, outer process receipts and reader code are retained under
examples/utility/verification-engineering-plan-v1 and the development directory.

Next: mixed-family execution and wind integration, followed by complete
source-bound cost/effort joins and a full matrix rehearsal. Independent task
admission, qualified private confirmation, Linux, a second actual host, installed
engineering execution and archive relocation remain unqualified. No utility or
role-retention benefit is established. The full goal stays active. Increment
hashes are in examples/utility/source-inventory-engineering-plan.json.

## Mixed prediction and engineering execution

Added a versioned mixed plan with embedded prediction and engineering campaigns,
one runtime/source/lock closure and the existing parent allocation ledger. The
coordinator checks task-specific candidate, partition and outcome identities,
scientific/host grants and group allowances before allocation. It dispatches to
the existing executors and exports their exact selected states into one suite
manifest. Prediction metrics and engineering feasibility remain separate.

Extracted the existing prediction input/recipe and engineering task/recipe
validators for reuse. Existing plan schemas retain their identities and behavior.
The public CLI recognizes the mixed schema, pins the exact plan and retains
explicit engineering scenario continuation. Neither completion nor resume freezes
the suite or accesses confirmation automatically.

Eight focused checks passed before the final prediction source preflight was
expanded. They cover both executors, both agent brokers, CLI pause/resume,
source/lock/outcome rejection, one selection barrier and interruption after each
executor's original scientific response. The fixtures are authored contract tests,
not a real mixed-family scientific rehearsal. Final broader checks are recorded
separately below when complete.

The first fixture runs exposed incorrect private-directory permissions, a stale
new-source identity, an insufficient parent allowance and an incorrect test field
name. These were fixture defects. No admission, scientific or accounting gate was
relaxed. The ledger refused work exceeding its original parent allowance.

Next: a real exposed mixed-task rehearsal, wind public execution, source-bound
cost/effort joins and the full matrix. Independent task admission, qualified
private confirmation, Linux, another actual host, installed engineering execution
and archive relocation remain open. The full goal remains active.

Final verification for mixed execution passed 369 tests with 16 skips in 476.67
seconds across the utility, optimization recovery and run-spec tests. The thirteen
mixed tests include private-data, unsupported-family, catalogue, runtime and corpus
rejection before allocation. The optional corrected subset passed nine tests in
51.65 seconds. Documentation passed 19 tests, and Ruff passed.

The expanded prediction source check initially consumed a candidate generator.
Materializing its snapshots fixed the preflight defect. The initial broad check
retains five failures with 359 passes and 16 skips. An initial optional check also
retains those five failures and one existing engineering CLI source-drift failure.
A recheck in that fixture's original environment rejected changed captured source
bytes, and a fresh engineering CLI check passed. The later catalogue test needed
its route grant changed with its task pool to reach the intended campaign check.
Its eleven passes and one failure remain recorded. No gate was relaxed.

A separate final reader check passed with model imports, physical/network dispatch
and captured-source access denied through os.open, Python open and pathlib.
The stronger guard changes only the test. Production sources stayed fixed during
the final broad check. Earlier reader/broad checks used the narrower guard.
Evidence and exact scope are under examples/utility/verification-mixed-plan-v1.
Full repository default/Bayes, installed wheel, real mixed-family and remote/host
qualification were not rerun for this increment. Increment hashes are in
examples/utility/source-inventory-mixed-plan.json. The goal remains active.

## Three-family exposed rehearsal and integration repairs

Added examples.utility.rehearse_mixed to prepare Leaf River, OEDI solar and circuit
campaigns under one runtime, source/lock closure and parent suite. Its 21 cells
cover baseline, conventional, single-agent, multi-agent and three role removals for
each task. It captures the preparation helpers and original Leaf template. The
existing read-only solar loader verifies the caller's cache and fetches nothing.
Independent task drafts remain unadmitted. The old Leaf protocols are unchanged.

Guarded preparation checks an exact closed source tree, zero allocations, shared
locks, exposed data and the actual prediction campaign JSON creation boundary.
Dependency imports and platform metadata are initialized before installing the
all-process dispatch guard. The initial guard caught dependency calls to uname
and file, not scientific execution. Those failed logs remain retained.

The first actual CLI attempt exposed a JSON/YAML boundary defect. The coordinator
writes JSON, but campaign creation decoded it as YAML, misreading scientific
notation in Leaf calibration. CampaignController.create now uses strict JSON for
.json/.JSON paths, preserving notation and duplicate-key rejection. Seventeen
campaign controller checks passed. The failed mixed-v1 suite has no scientific
start and remains unchanged.

The next attempt performed one stopped baseline evaluation, then encountered the
64 KiB child receipt limit when exporting the 110813-byte model and 112818-byte
selected state. The incomplete mixed-v2 suite retains that charged evaluation.
Selected artifact binding v1 now gives large JSON payloads a small authoritative
child receipt. It binds exact kind, digest, size and suite reference. Writer and
reader verify the full payload. Existing small child receipts retain their bytes,
and the child limit remains 64 KiB. The existing artifact limit remains 64 MiB.
Selection schema v2 is required. No scientific or receipt limit was relaxed.

Focused artifact/confirmation, prediction and mixed checks passed 32 tests in
112.37 seconds. The final campaign/utility/recovery/run-spec check passed 486 tests
with 17 skips in 642.84 seconds. Documentation passed 19 tests and Ruff passed.
The earlier overlapping check retains one source-closure failure, 482 passes and
17 skips. Its traceback verifies that a registered source changed during repair.
The final run used fixed production/test bytes.

At the 2026-10-28 22:04 UTC checkpoint, fresh mixed-v3 had finished all seven Leaf
cells and was executing solar. Confirmation access remained zero. Its public CLI
operation is still active, so no completed three-family rehearsal is claimed by
this checkpoint. The final contract run and rehearsal overlapped. Their durations
are not performance comparisons. The guarded reader also prepares a partial cost
join from batch receipts and native work, retaining unknown money, starts and
human effort. Complete cost/effort accounting remains open.

The mixed-v3 public resume later stopped in the first solar cell after two stopped
evaluations. It retains seven finished Leaf cells, one started solar cell and
thirteen reserved cells. All 231 scientific and 56 scripted host reservations have
verified observations, with no unresolved physical work or confirmation access.
Its frozen paired seed is 6045573192120957115. A no-model diagnostic reproduced
Optuna's 32-bit sampler seed restriction. An original-case recovery retained the
failed action and reported stale_revision after partial work. That recovery result
is not relabelled as successful reconciliation.

Optuna now derives one uint32 sampler seed with NumPy SeedSequence only when the
immutable study seed exceeds uint32. The backend identity records the mapping
version and sampler seed. Existing uint32 seeds pass through unchanged. The source
identity changes require new studies; old records and study seeds are not edited.
The owned Optuna/seed/recovery subset passed 24 tests in 15.69 seconds, including
large-seed resumed versus uninterrupted proposals, costs and no duplicate work.
The earlier sandboxed attempt retains its reconciliation_required failure.

A separate real solar canary completed with that original 63-bit seed and the
new mapping: 15 confirmed starts, none unresolved, accepted_candidate on already
exposed development data. Its prepared parent suite allocated no cells. The
canary is not a full matrix, private confirmation or a utility comparison.

A fresh mixed-v4 full matrix and contracts-seed-final check were launched against
the new source. The offline guarded reader targets mixed-v4, but has not yet been
run because that matrix is still active at this checkpoint. The repeated starts
and failed v1-v3 evidence remain charged in their original ledgers. Raw evidence,
source snapshots and failed-run counts are under
examples/utility/verification-mixed-rehearsal-v1. The full Part 5 goal remains active.

The fresh post-seed contract run passed 486 tests with 17 skips in 664.74 seconds.
Mixed-v4 then stopped after all seven Leaf cells and the first solar fit/review.
All 15 solar evaluations were confirmed, with no pending physical work. The last
worker task asked for a freeze, but the scripted orchestrator assigned an
investigator while one untried candidate remained. The controller correctly
rejected that handoff as invalid_output because the one-candidate allowance was
exhausted. This was a scripted-host defect, not another seed failure.

The scripted orchestrator now honors that explicit freeze request while retaining
its previous choice when investigation is allowed. Two focused stage tests passed.
The broker, single-agent and role-removal regression subset passed 39 tests in
148.89 seconds. A separate real solar no-investigator canary completed one bounded
cell with 21 observed reservations and verified stops. It allocated no work in the
original prepared three-family parent and did not freeze or access confirmation.
Its second assigned circuit cell remains reserved and unexecuted.

Fresh mixed-v5 is running with the repaired host source. Its process handle must
be polled before any resume or restart. The guarded reader targets mixed-v5 but
remains unrun. Source inventories, test scopes and the active handle are recorded
under examples/utility/verification-mixed-rehearsal-v1. The full matrix remains
unqualified until that run and its reconstruction finish. No Part 5 completion,
independent confirmation or utility verdict is claimed.

## Matrix completion and wind evaluator foundation

The original mixed-v5 producer completed all six public CLI operations: run one,
resume twenty, completed resume, separate freeze, verify and status. It finished
21 cells and completed resume added zero cells. The sealed selection digest is
359b828f7f12546a17e9d69d9aa24e40b0632a14780d9e908feb583c6341b92e.
No confirmation access occurred. This is exposed scripted development, not an
independent utility experiment. Its guarded reconstruction/cost reader remains
active at this checkpoint; completion is not inferred from CPU activity.

Added separate wind example modules without changing the matrix's captured
runtime. WindGeometry keeps fixed hardware, exact scalar parameter bounds and
existing geometry checks. Its model identity stays fixed across configurations,
and context sources can come from a captured root. WindNativeSpec and proposal
records separate wake/gradient callback traces, preserve failures and require
fresh evaluation. A native point outside exact parameter bounds yields no
configuration even if the physical tolerance accepts it. No coordinates or gates
are adjusted. Coupled-solver residuals or inner wake-solve counts are not invented.

A registered scalar wind evaluator reuses the existing supervised engineering
process executor. The profile admits four turbines and one bundled distribution.
Direction-step metadata are numerical configuration, not unseen weather. The
first real probe produced energy but an unavailable mandatory finite check vetoed
eligibility. That stopped process and its original source remain in wind-scenario-v1.
The missing registration is fixed and covered by a positive check-availability test.

Wind-scenario-v2 runs two source-bound processes on the actual Horns Rev corner
coordinates. Direct/wrapped modeled energy agrees at 37.06343379120568 GWh with
all mandatory checks passing. Completed replay adds zero reservations. A guarded
base reader verifies original jobs, process completions, outputs, bindings and 183
archived source files without scientific imports, dispatch or original-source
access after archiving. Relocation and installed execution were not attempted.

The final wind subset passed 26 tests with five warnings in 12.03 seconds. Base
checks passed 18 with four skips. Documentation passed 19 and Ruff passed. Raw
checks, the earlier source-mutation regex mismatch and both probe versions remain
under examples/utility/verification-wind-parameters-v1 and development/wind-scenario-v*.
Wind public routes, its native-process bridge and prelaunch infeasibility
classification remain incomplete. The four independent dossiers, private scoring,
platform/host and full cost/effort gates remain open. The full goal stays active.

## Installed wind archive reconstruction

A locally built wheel installed into a temporary venv passed the wind archive
reader outside the checkout with isolated Python startup. Replay denied original
checkout access, scientific imports, process dispatch and sockets. Both original
process stops, job/result bindings, checks and all 183 source files verified. The
venv reused base environment dependencies. This qualifies the saved wind reader
on this macOS host, not installed wind execution, Linux or another host. Raw build,
installation and reader evidence is in verification-wind-relocation-v1. The mixed
reader remains running at this checkpoint. Full Part 5 completion remains open.

## Completed mixed archive reader

The original mixed-v5 reader finished with exit status zero. It reconstructed all
21 selections (seven each Leaf, solar and circuit), all 419 science and 167 host
observations with verified stops, and 28 large selected artifacts. Its guards
denied scientific imports, model/network dispatch and original captured-input
reads. Public verify/status also passed under those guards. The partial cost join
retains unknown records and excludes total wall/CPU/GPU/energy and human effort.
There were zero confirmation accesses. All 330 captured runtime files stayed
unchanged through execution and reading. No rehearsal process remains active.

This closes the exposed three-family archive check. It does not admit the four
independent tasks, qualify wind public/native execution or establish scientific
utility, role retention or cost gains. Full Part 5 remains active.

## Wind native process and fresh evaluation

The shared native supervisor now exposes job, binding and worker-selection hooks.
Its existing circuit defaults and schemas are unchanged. Separate wind records and
a fixed core bootstrap bind actual sources before supplied execution. Wind keeps
wake and gradient callback traces and ceilings, without circuit residuals or
invented inner solve counts. Missing returned traces leave callback costs unknown.
Unresolved callbacks cannot provide a layout configuration.

The source-bound wind-native-process-v1 development probe converged with two
completed wake callbacks and one completed gradient callback. A separate reserved
scenario process passed all mandatory checks at 37.06343379120568 GWh, equal to the
prior baseline. Both stops verified and completed recovery added zero reservations.
A guarded base reader verified original job/report/binding/process/output bytes,
the exact fresh configuration and 188 archived source files. It denied scientific
imports, dispatch and original captured-source reads after archiving. This probe
uses the bundled distribution and establishes no native or utility gain.

Focused default wind/circuit checks passed 28 with two optional skips. The final
wind environment checks, including stdout tampering, passed 37 with five dependency
warnings. Repository lint passed. The broader engineering/study/cost/wind regression
run is still active at this checkpoint. Its original session is recorded in
verification-wind-process-v1/runtime-checkpoint.json. Initial sandbox, bootstrap,
exception-assertion, occupied-output and direct-reader-path failures remain visible.

The public campaign types still require circuit native diagnostics. A versioned
callback-result contract is needed before wind can enter the common route builder.
That integration, prelaunch infeasibility handling, installed native wind execution,
independent tasks, private scoring, platform/host and full accounting remain open.
The full Part 5 objective stays active.

## Wind process verification closeout

The broader final-source engineering/study/cost/wind run passed 110 tests with
12 optional skips in 329.89 seconds. Wind passed 37 with five dependency warnings,
documentation passed 19, and repository lint passed. Final readers deny both
built-in and importlib scientific imports, physical/network dispatch and original
source access during replay. The installed reader passed outside the checkout
under isolated startup. It matched 185 installed source files to the original job
and verified all 188 archived files. Its temporary venv inherits base dependencies.
All source checkpoint hashes stayed unchanged during the checks. No job remains
active. No full repository/Bayes/interoperability rerun is claimed for this increment.

This qualifies the saved native wind reader, not installed scientific execution or
public wind routes. Those routes need a versioned callback-result contract because
the current campaign record requires circuit diagnostics. Independent tasks,
confirmation, platform/host and full accounting remain open. Full Part 5 stays active.

## Callback campaign contract and public wind routes

Added callback-native spec/job/result/report records and a fixed worker, with
canonical frozen options, typed callback traces, caps and source-bound process
recovery. Campaign v3 accepts that profile alongside the unchanged v1/v2 circuit
campaigns. Callback costs and worker summaries use callback quantities rather than
invented circuit residuals or inner solves. The wind adapter maps its existing
bounded TOPFARM trace to this contract. Fresh scenario checks still gate eligibility.

Nine initial default tests passed. The shared-route test then exposed one remaining
broker assumption that native results contain coupled solves. Callback worker
summaries now keep callback entries/statuses separate. The focused shared baseline,
conventional and single-agent test passed. A zero-allocation wind preparation passed.
The source capture from before the broker correction remains preserved and unused.

The real wind-plan-v1 suite completed seven cells through the six public CLI
operations, with completed resume adding zero cells and no confirmation accesses.
Its sealed selection is
bbb43f27380e07c3da055b11a400c55c12c41e9983e6775339280cfdf381c636.
The guarded reader and broader regression check remain running at this checkpoint.
Current handles and the immutable runtime hash list are under
verification-wind-routes-v1. No runtime/source files will change during those checks.

The public wind path is implemented for bundled development. A single four-family
runtime/rehearsal is still missing: wind lacks pvlib/Optuna and interoperability
lacks PyWake/TOPFARM. No dependencies were added in this increment. Independent
weather/task admission, prelaunch scientific-infeasibility classification, installed
scientific execution, private scoring, Linux, a second host and full accounting
remain open. Full Part 5 and comparative utility remain incomplete.

The installed copied-suite reader passed with the original checkout, models,
processes and network denied. Explicit inspection retains original scenario jobs
and binding identities while following only local confined archive paths. It
refuses executors, request handling and cancellation. Post-change campaign/native
checks passed 38 with one skip. Additional checks passed eight tests, covering all
three campaign schemas, changed job seeds/paths and wind trace translation.

The selected development outcomes are retained in development-outcomes.json:
baseline selected 37.06343379120568 GWh, and all six other scripted routes selected
the same point at 37.14054878357185 GWh. This is one exposed paired run, with no
independent weather, LLM utility, role-retention or cost conclusion. A prefix-three
unit test originally assumed advisory route order in its name. Its final name and
assertions now describe the actual balanced advisory coverage. The full real
seven-route rehearsal independently covers all seven routes.

## Common four-family runtime and installed science

A direct wind/interoperability feature combination failed resolution: TOPFARM 2.6.2
requires OpenMDAO 3.39.*, while interoperability pins 3.41.0. The separate optional
utility profile pins 3.39.0 with the existing pvlib, Optuna, PyWake and TOPFARM pins.
It installed successfully. All pre-existing environment lock entries stayed equal.
Pixi retained its warning that offline mode does not guarantee offline PyPI access.
The circuit implementation label now reflects its actual installed version. No old
run or frozen criterion was relabelled. The wind model module is included in wheels.

The common runtime passed 14 science checks with five warnings, including circuit
parity, derivatives, physical vetoes and native limits. Three guarded preparation
checks passed. Another 70 runtime checks passed, with one stale documentation extras
assertion failing. The intentionally expanded extras/pins contract then passed all
19 documentation tests. Numerical criteria were unchanged. Raw warnings and failures
remain in verification-four-family-v1.

The new mixed option prepares 28 cells over all four exposed development tasks. It
copies declared bytes, rejects conflicts, rebinds exact source references and uses
one parent/runtime/lock inventory. The original three-family option remains. The
actual four-family-v1 rehearsal is running under original session 2696. At the latest
checkpoint all seven Leaf and seven solar cells were finished. Current ownership,
source hashes and continuation instructions are in verification-four-family-v1.

A wheel installed into a separate temporary venv ran a bounded native wind process
and separately reserved fresh scenario from an exported bound input bundle. Both
stops verified and energy was 37.06343379120568 GWh. Completed recovery added zero
reservations. A fresh installed interpreter verified completed receipts without an
executor, adding zero reservations, observations or batch events. A declared Python
audit policy denies original checkout opens and sockets. Dependencies are referenced
from the resolved utility site directory without activating its editable hooks.
This is not an OS private-label boundary or preparation from scratch.

The initial installed root permission refusal and finished-case executor refusal
remain recorded. Neither started extra science. The owner-private root and receipt
verification path passed without weakening either guard. Permanent copied receipts,
inputs, logs and source are under development/installed-science-v1 and
verification-installed-science-v1. These two qualification processes are separate
from the 28-cell rehearsal. Independent admission/confirmation, privacy, platform,
second-host and complete cost/effort requirements remain open. Full Part 5 stays active.

Installed preparation from the exported bound bundle also passed. A fresh installed
interpreter prepared all 28 cells with zero allocations and dispatch denied. It
rebound the runtime, startup policy and affected source/recipe/grant identities into
a new study, leaving the original study unchanged. It does not qualify raw-data
acquisition or source generation. Its initial field-name error occurred before the
new suite was created and remains recorded. At the next main-run checkpoint,
all Leaf, solar and circuit cells and two wind cells were finished.

The original 28-cell producer completed all six public commands with exit status
zero. Completed resume added zero cells and confirmation accesses remained zero.
Its selection digest is
cfbedf3b1ebdac55f1e0dcfc7e46c69bea076c980b8544c016e186ea1b30fd0a.
The guarded reader remains running under original handle 53173. Public CLI child
durations are retained separately in cli-wall-times.json. Completed resume and
verification are CPU-intensive despite no new scientific work. Stack sampling
confirmed active verification. No performance or total-cost benefit is claimed.

A separate installed four-family baseline smoke also passed the six public commands
outside the checkout from exported inputs. It completed one baseline for each task,
added zero cells on completed resume and sealed with zero confirmation accesses.
The Python startup policy remained active. This advances G6 to installed baseline
science across all families, plus the separately checked native/fresh wind path.
It does not qualify all 28 installed comparative routes, acquisition/source creation,
Linux, another actual host or the OS private scorer boundary.

## Four-family reconstruction closeout

The original guarded reader completed with exit status zero. It reconstructed all
28 selected cells, verified 227 source/data files and 28 large selected artifacts,
and checked stops for 444 science and 220 host observations. All 370 recorded
scientific evaluations are retained: Leaf 229, solar 91, circuit 31, wind 19.
Scientific imports, physical/network dispatch and captured-input reads were denied.
This completes the exposed common-runtime producer and reader. No process remains
active. Confirmation accesses and scores remain zero and utility is not attempted.

The installed baseline smoke separately verified six science observations across
four families, plus the earlier two-process native/fresh wind check. All stops
verified and completed resume added no cells, observations or events. These auxiliary
checks remain separate from the main study. Costs are still partial and unknowns
are retained. Full repository/Bayes/interoperability suites were not rerun in this
increment. The full goal stays active with independent task admission/confirmation,
prelaunch infeasibility semantics, privacy, platform/host, full cost/effort, expert
workflow and final utility/role-retention requirements open.

## Preflight geometry increment

New engineering execution v3 binds minimum-distance constraints to the execution
identity. Wind preparations declare all six turbine pairs using the existing
spacing tolerance. In-domain violations produce durable scientific infeasibility
before scenario reservations. Metrics stay unavailable. Numerical study limits
still bound zero-physical-cost results. Campaign selection and relocated inspection
retain the veto. Original v1/v2 serialization and process behavior are preserved.
Existing physical charges cannot be replaced by a zero-start receipt.

The initial focused checks passed 50 tests with two optional skips. Common-runtime
wind and three/four-family preparation checks passed 32 tests with one existing
NumPy binary-size warning. The bounded actual wind probe rejected an overlapping
layout without dispatch, then ran one feasible baseline with one verified stop.
Its energy was 37.06343379120568 GWh. Completed recovery added no reservations.
A guarded base reader verified the rejection and physical stop accounting without
scientific imports, dispatch or original captured inputs. It does not qualify
independent weather or independent replay of the feasible output.

The final preflight tests passed 11 cases, including cancellation and conflicting
charges. The default suite finished with 1853 passes, 106 skips and one shell PATH
failure. That command-runner test passed when the project interpreter was placed
on PATH. Interoperability passed 114 tests with four warnings. The Bayes suite is
still running. Raw failed test harness assertions are retained. The earlier
four-family suite was not rerun and remains qualified only for its original source
snapshot. Independent admission/confirmation, privacy, complete effort/cost,
platform/host and the remaining utility/role-retention requirements stay open.

The separate v3 native wind probe also passed: two reserved processes and two
verified stops, with zero additional reservations on recovery. Two wake entries
and one gradient entry completed. These callback counts do not establish inner
wake solves or CPU work. No comparative matrix was rerun.

A newly built local wheel contains all current core Python bytes. Its rejection
reader passed outside the checkout, with no optional wind/solar/OpenMDAO packages,
original-checkout Python opens denied and sockets denied. Dependencies were reused
from resolved cached base paths without editable activation, not installed through
a clean minimal solve. The first venv used the unresolved project interpreter path
and the original-access guard refused a standard-library import. The corrected
venv uses the resolved interpreter. Both attempts and the unchanged policy remain
recorded. This qualifies installed rejection reading, not private-data isolation.

## Four-family saved diagnostic figures

The offline exporter now reads all 28 selected states and hash-pinned saved arrays
and engineering scenario records. Its 3941 prediction rows reproduce RMSE and bias
for every selected Leaf/solar cell. The 28 scenario outcomes, 56 checks and 28 turbine
positions remain separate tables with explicit units. All seven routes remain in
each task. Exact overlaps are grouped only in the rendered marks: six selection
routes share each prediction curve and all seven wind routes share one layout.

Prediction/residual and circuit/wind scenario figures were rendered at 11 and 8
inches. Visual inspection caught an overlapping solar legend and an incorrect
minimum-node label. The final figure names Node 2, moves the legend, retains support
gaps and shows the actual constraint thresholds. Initial images and warnings remain
under verification-diagnostics-v1. The final data/PNG/SVG/caption package is
examples/utility/development/diagnostics-four-family-v4.

A fresh installed reader, with optional scientific packages absent and original
checkout/socket access denied, reconstructed every table and the summary byte for
byte from 94 copied pins. The first exporter used a SuiteStore constructor and
required unrelated ledger directories. It now deserializes the immutable suite
spec directly. It relies on the earlier qualified full reader and hashes for
ledger provenance, rather than asserting a fresh full ledger replay. Both attempts
remain recorded. No model work or confirmation access was added. This advances
G8 development diagnostics, not independent utility, complete costs or role benefits.
Bayes regression verification remains running on its original handle 59944.

Final diagnostic QA passed both figure layouts and all table/image/code hashes.
A changed CSV was refused before rendering. Documentation checks passed 19 tests
and lint passed. All 15634 pinned files in the original four-family study and all
187 pinned core files remain unchanged. The export added no study events or model
work. Untouched partitions, custodian and qualified scoring runtime are requested
and remain unresolved. This does not change the full goal or authorize private data
access, live providers, remote work or a new independent run.

## Broad verification closeout and interim handoff

The original Bayes process completed with exit status zero: 1910 passed, 54 skipped
and 44 warnings in 1973.35 seconds. Its raw log/XML and bayes-terminal.json remain
in verification-preflight-v1. Warnings include dependency deprecations and the
existing BO numerical/input warnings. Core bytes remained fixed throughout the
run. This is the documented test suite, not a new frozen benchmark matrix.

The interim docs/utility-handoff.md now maps supported development tasks, source
snapshots, installed/diagnostic evidence, limitations and remaining steps. It keeps
independent confirmation, private scoring, complete cost/effort, Linux and another
actual host open. It does not rename development evidence as independent results.

Read-only local inventory found OrbStack with a Linux ARM64 daemon and a cached
ARM64 Python 3.12 image. No container was started, image pulled or runtime chosen.
That does not qualify Linux x86-64. Claude Code 2.1.310 version/help probes also
completed without a prompt or inference. The current host record accepts only
fake and Codex, so a real second-host implementation remains necessary. The
second-host increment records its implementation and approval gates. Its bare
mode requires API-key/helper authentication, not an inferred subscription profile.
No credentials, account status or provider call were accessed by these probes.

## Second-host raw transport foundation

The new Claude primitive pins CLI 2.1.310, checks supported flags and executable/
helper bytes, requires an explicit OS wrapper, clears inherited authentication,
and fixes tools, MCP, settings, session and API estimate-budget options. Its helper
verifier is part of the persisted command. Secret material never enters the job
environment. Original-job recovery checks the pinned job and model and never
relaunches. Existing host records, scheduler admission and process validation were
not changed.

The first fake-executable run exposed empty option arguments rejected by the
shared supervisor. The command now uses --tools= and --setting-sources=, verified
with installed CLI help only. Primary documentation then clarified SDK estimates
and incomplete top-level error counters. Normalization now keeps top-level counts
separate, uses per-model whole-call categories, treats crash zeroes as unknown work,
and keeps billed cost unknown. Earlier code, logs and installed checks are retained.

Final focused checks passed 111 tests across the new transport and existing Codex,
record, scheduler and process contracts. No model, provider or real credentials
were used. Installed fixture qualification is being completed on the final bytes.
The earlier full default/Bayes results remain evidence of their preceding source
snapshot, rather than a new full-suite result for this module.

The raw primitive is not an admitted scheduler Host. A qualified boundary/profile,
versioned truthful host records, scheduler/factory/cost integration, full conformance
package and explicitly authorized actual calls remain next work. The full Part 5
objective, independent data/privacy/platform and utility requirements remain open.

Second-host foundation closeout: 112 focused tests passed, including both owner-loss
windows. The fresh installed wheel then passed all 52 final authored fixtures
outside the checkout. All current core Python bytes matched the wheel. Original
checkout access and sockets were guarded by the existing Python startup policy
in the parent and ordinary Python children. The fixed helper verifier uses isolated
Python. No OS privacy or actual-host claim follows from this policy. The Anthropic
SDK was absent. Current documentation checks passed 19 tests and lint passed.

The raw module is still not an admitted scheduler Host. Its tests do not qualify
all roles on actual Claude, actual authentication, an OS boundary, a hard billed
USD ceiling, or another platform. Those requirements remain in the second-host
increment. No full default/Bayes suite or scientific matrix was rerun after this
additive raw-module change.

## Candidate Claude macOS boundary checkpoint

The new `claude_policy.py` renders an explicit deny-default policy with a private
home, read-only worker packet, fixed runtime/helper/executable paths and bounded
localhost endpoint ports. The actual v5 kernel probe passed all 14 syscall controls,
Claude help startup and direct pinned-helper startup with a synthetic fixture.
No inference, real credentials or production admission was involved.

Raw failed attempts, source copies and the final receipts are archived under
`examples/utility/verification-claude-policy-v1` and `development/claude-policy-vN`.
The numeric endpoint grammar failure and missing public ICU startup dependency are
preserved. The final probe binds host source identity
`86b89bd3d3f2dade5fe0cad06650a72267a4536d0e7db2d675b55e216d9fcb8d`.
Prior qualification records keep their original identities.

Focused host/process/policy checks passed 128 tests. Twelve archive checks passed
both in the checkout and using the existing installed wheel outside it. The actual
saved probe was reconstructed with checkout access, processes, sockets and optional
model/provider imports blocked. The archive reader verifies recorded stop evidence,
not current process state. It cannot grant host admission.

Next work remains actual Claude helper-hook/controlled-peer integration, permission,
resource and lifecycle qualification, truthful host records and scheduler/factory/
cost integration. External API traffic needs a separately qualified broker. IPv6,
UDP, DNS/TLS, preferences/shared memory, process environment privacy and Linux are
unqualified. Only after these requirements and model/authentication choices are
resolved can a concrete live conformance package request execution authority.
The full Part 5 scope and independent-data/scorer requirements remain unchanged.

## Native Claude controlled-peer checkpoint

The actual native helper hook and structured-output roundtrip now work against an
application-owned loopback peer with synthetic input and authentication. Final v7
records exactly one peer request, successful structured output and a verified stop.
No provider or scientific model ran. Reported token and dollar values are authored
fixture data. They are not cost/utility evidence or actual role conformance.

Transport 1.4 binds an integer-only local endpoint through fixed settings. It puts
both temporary-directory settings in the isolated home. The supervisor admits the
non-secret CLAUDE_CODE_TMPDIR only when it equals explicit HOME. Credentials remain
forbidden in environment records. Policy 1.4 grants the measured /bin/sh launcher,
/bin/bash delegate and public selector, without granting /bin as a read/exec tree.
The native result requires explicit terminal completion to accept a StructuredOutput
tool_use stop. Plain text and incomplete/error/tool-usage results remain rejected.

All failures are archived, including the temp override, shell/delegate and native
terminal-result discoveries. The final policy probe also passed its 14 syscall
controls on host source identity
8402762a4b9dbbb4292a08e502997a8d54e5ffd6418153825a8a41fbe5eaf07f.
The offline native reader checks pinned raw evidence and never executes an archive.
Its eight regressions passed. A fresh wheel matched all 181 current core Python
files, passed 100 installed authored fixtures, and reconstructed the actual final
native/policy archives with original-source opens, sockets and processes blocked.
The initial installed interpreter-alias setup failure remains recorded.

See examples/utility/verification-claude-loopback-v1/README.md for commands and
source-specific limits. The broad agent test run remains active at this checkpoint.
The original study's 15634 pinned files are unchanged. Old production pins retain
their original source scope and cannot be reused or rewritten for changed source.

A production upstream broker, truthful host records/admission, scheduler/factory/
cost integration, full runtime/privacy/lifecycle qualification and actual authorized
LLM conformance remain unfinished. The diagnostic peer has no upstream. Independent
data/custody, a qualified scorer, final protocol/cost/effort and Linux x86-64 remain
open. This checkpoint does not close G6 or the full Part 5 objective.

Native lifecycle closeout on the same core bytes: actual timeout, cancellation and
output-limit probes all stopped after one authored-peer request. Completed replay
added zero requests and reproduced the original process, parsed result and job.
After active supervisor death, the watchdog stopped the group, the completion
remained missing, and recovery refused without a new job. Its outcome stays
unknown_owner_loss. A separate fault after saved completion recovered only the
prelaunch-bound original result with zero added jobs. These local synthetic checks
do not supply real model conformance or production integration/qualification.

The all-agent regression run completed: 939 passed in 1175.53 seconds with fixed
core source. Its exact collection and terminal receipt are preserved. This is not
a new full default/Bayes run or a frozen science matrix. All independent-data,
scorer, protocol, platform, live-call and full Part 5 completion requirements remain.

## Durable Anthropic exchange checkpoint

The new Messages exchange and endpoint now have distinct policy identities while
preserving existing Responses record shapes. They rebuild the frozen role request,
reserve one attempt before dispatch, retain bounded raw JSON, reject incomplete/
wrong-model/tool output and construct a new StructuredOutput stream only after
validation. Exact saved requests replay without another callback. Reported usage
is preserved separately for rejected handoffs. Missing categories stay unknown.

The combined source check passed 222 tests. Two actual native CLI probes through
the durable endpoint and an authored callback completed with verified stops and
unchanged recovery. Each recorded two HTTP connection attempts, one accepted
exchange and one callback. The missing-cache probe shows SDK zero-fill while the
broker keeps unknown totals. These are synthetic counters, not provider work.
No real key, provider, science or independent partition was accessed.

Evidence: examples/utility/verification-anthropic-exchange-v1. The final source
identity is b595972dc5e2e20320bb5b4b1c960c42b3dc7d98cd7ea8c103308e30dc83ced8.
Earlier source pins remain unchanged. A real upstream and credential/runtime
qualification, host records/admission, scheduler/factory/cost integration, actual
LLM conformance and all other full Part 5 gates remain open. Authentication profile
preference has been requested without granting or requesting live-call authority.

Durable exchange verification closeout: the fresh default suite passed 2016 tests
with 106 optional skips in 2145.54 seconds. All 364 frozen source/test files were
unchanged. Installed checks passed 46 exchange cases under a deny-all-sockets
guard and 13 endpoint cases under a separate loopback-only guard. The initial
combined guard mismatch is retained. Installed readers checked caller-pinned
archive bytes and recovered complete, missing-cache, owned-command and six failed/
uncertain exchange cases with original opens, sockets and subprocesses denied.
Optional scientific packages and the Anthropic SDK were absent.

The owned-command native probe verified both process stops and original response
recovery. Its incorrect initial driver enum is retained alongside the corrected
fresh run. Six fault fixtures explicitly observed zero replay callbacks while
preserving reservations and unknown states. These are authored local checks with
zero actual provider calls. The full Part 5 objective remains incomplete.


## Prepared API upstream checkpoint

The explicit private API lease and fixed isolated Messages worker are implemented
and tested with authored credentials only. The shared reader now refuses FIFOs
without blocking. Exact production-command refusals verify no send intent and
local stops. A separate owned TLS fixture proves one request, original-byte
recovery after lease removal and no repeated launch. Production verification
rejects its routing shim.

Final checks: 299 transport regressions, 52 strict installed cases and six installed
TLS/process cases passed. All 187 core wheel files matched source. Ruff and diff
whitespace checks passed. Evidence and initial failures are preserved under
examples/utility/verification-anthropic-upstream-v1. Host source identity:
5996c60747b6a39355a994d2cd7cf7b830c7088151f2640f05fd9770cf1a00ae.
The earlier full default suite retains its b595972d source scope.

The API profile remains provisional pending authentication preference. No real
credential read, provider call, independent access or production admission occurred.
Full runtime/privacy/resource qualification, host records, scheduler/factory/cost
integration and actual authorized conformance remain open. This checkpoint does
not close G6 or any independent-data/scorer/protocol/platform requirement. The
full Part 5 objective remains incomplete.


## Owned Claude composition checkpoint

The native process, durable Messages exchange, endpoint stops and broker usage now
produce one bound transport result. Native job binding precedes the launch gate.
Original-byte recovery and append-only stop captures never relaunch. Corrupted
bindings still trigger listener cleanup. Typed role/scientific authority and
upstream process/remote-stop obligations remain outside this primitive.

Related tests passed 169 cases. The installed wheel matched all 188 core Python
files and passed 24 composition cases. Actual Claude Code 2.1.310 completed under
the candidate macOS policy against one authored callback, with verified local
stops. Recovery returned the same HostResult and added no callback. The broker
total stays unknown while SDK diagnostics report 17 fixture tokens. No real
credential, provider or independent scientific partition was accessed.

Source: bf795307c0b31643daa37651c6ea91fbbd1f2adc44c1fe5c4606c91f4a9b8eca.
Evidence: examples/utility/verification-claude-composition-v1. Earlier suite/source
pins retain their scope. Host records/admission, full runtime/privacy/resource
qualification, factory/scheduler/cost joins and explicit actual-model conformance
remain open. Part 5 data/scorer/protocol/platform and comparative requirements
remain incomplete.


## Claude host/profile integration checkpoint

The provisional Claude/API adapter now has distinct version 3.0 selection,
capability schema 1.1 and configuration binding schema 1.1. Legacy fake/Codex
serialization and configuration digests remain unchanged. A separately versioned
qualifier requires every source/runtime/executable/model/API/limit binding and raw
indexed check. No actual Claude profile has been qualified by these fixtures.

Serial CLI/factory/scheduler dispatch, typed role validation, original-result
recovery and permanent batch accounting are implemented. The installed CLI
completed seven authored calls across all four roles. Resume added no calls or
changed worker bytes. Batch lost-acknowledgement recovery retained one charge.
Broker unknowns remain explicit. Native estimated USD and zero-filled counters
never replace them. Capabilities disclose the current platform, authentication,
remote-stop, billing and resource-cap limitations.

The final wheel matched all 190 core Python files and passed 29 installed checks.
The CLI test requires an explicitly exported repository fixture producer, public
lock and byte-identical source/resource mirror. Initial missing-producer and
missing-closure-layout failures are retained. This is not wheel-only preparation.
Evidence: examples/utility/verification-claude-host-v1. Source identity:
dd06d8ff96bed0d21b40134a4271307dce1d7a4552f8b28ffa19ce12da45e88b.

The fresh default suite is running under original session 5875. Source/test bytes
are fixed. Actual qualification, Claude conformance preparation/handler and live
model authority remain open. The existing conformance commands keep their Codex
protocol. Real task routes, full cost/effort, independent data/custody, scorer,
protocol and Linux requirements remain incomplete. No real credential or provider
was accessed. This checkpoint does not close G6 or the full Part 5 objective.


## Task dossier reconciliation during the fixed-source test run

The four draft task dossiers now distinguish implemented exposed development from
missing independent admission. Hydrology's explicit stores/fluxes and mm/day
conversion, and the engineering campaign/derivative/scenario integration, have
source and saved-evidence references. Their obsolete implementation blockers were
removed. The wind dossier now names the actual four-turbine profile. Its current
scenario executor cannot ingest independent weather resources. Solar's wrapper
also binds the historical development input protocol.

All tasks remain blocked_draft with no admitted confirmation partition or frozen
effect margin. No new data, model run or confirmation access occurred. Before/after
bytes and evidence digests are in examples/utility/verification-task-dossiers-v1.
The 363 core/test files of default session 5875 remain unchanged. Independent wind
resource ingestion is a concrete remaining software task, alongside data/custody,
private scoring and final protocol admission.


The exposure register now identifies the old 2024-2025 solar partial-cache metadata
as unknown exposure. Its advertised filenames and byte ranges do not establish
exact cached dates or prior use. It is not an untouched confirmation fallback.
Three legacy hydrology source hashes were also verified. No new observations,
model execution or confirmation access occurred. See exposure-reconciliation.json
in verification-task-dossiers-v1. The updated dossier wheel matches all 190 core
Python files and the four JSON resources, without a new runtime execution claim.


## Host increment verification closeout

Original default session 5875 completed with exit zero: 2127 passed and 106 skipped
in 1811.17 seconds. All 363 pinned source/test files were unchanged. Current-source
limited kernel/help and actual native-composition probes also passed, with one
authored callback, verified local stops and zero replay callbacks. A trusted driver
additionally measured all 19 synthetic syscall controls with the Claude renderer,
including owned environment, synthetic plist and shared-memory controls. The shared
object was unlinked and owned carrier stopped. Executable substitution and runtime
renderer hooks remain explicit. Actual preference-service privacy and complete
host qualification remain unverified. No real preferences, key or provider was read.

Terminal records, raw driver source, byte archives and source bindings are under
examples/utility/verification-claude-host-v1. Earlier running-status paragraphs are
historical checkpoints. This closeout applies to source identity
dd06d8ff96bed0d21b40134a4271307dce1d7a4552f8b28ffa19ce12da45e88b.
Task/exposure reconciliation changed metadata only. No independent task, private
scorer, protocol, Linux, actual-model conformance or full Part 5 gate is closed by
these checks. Next software work includes independent wind-resource ingestion and
its protected confirmation path, plus the Claude conformance package/handler.


## Supplied wind resource implementation

The new resource profile accepts explicit joint direction/speed mass tables and
uses the same bound resource in native optimization and separately reserved fresh
evaluation. Legacy bundled-resource records retain their shape. Input integrity,
geometry, probability/energy alignment, callback ceilings and original recovery
are checked. This adds no general array-port capability or private-score boundary.

Wind checks passed 71 tests with four retained environment/deprecation warnings.
Base wind checks passed 62 with nine optional skips. A fresh installed wheel ran
the bundled synthetic example without checkout access or sockets. A separate base
reader with optional models absent reconstructed its pinned NPZ/JSON arithmetic
with original opens, sockets and subprocesses denied. Cached dependencies were
reused. The earlier full default result retains its pre-wind-increment source scope.

Evidence: examples/utility/verification-wind-resource-v1. All resource tables are
hand-authored synthetic fixtures. No real weather, provider or independent
confirmation was accessed. The current profile publishes its resource asset in
the source bundle and must not be used for private confirmation weather. Final
source/custody/rights, protected scoring, task/protocol, host conformance and Linux
requirements remain open. Full Part 5 is incomplete.


## Claude conformance preparation increment

The versioned preparer now accepts the explicit Claude 3.0/API profile under
preparation schema 1.1 and a separate protocol digest. It captures only the fixed
public scalar campaign after checking the caller-pinned qualification and host
configuration. No credential is opened, runtime created or clock started. The six
cases retain fixed outer allowances of thirteen host calls and two science starts.
API criteria preserve remote-stop uncertainty and separate local stop evidence.

All Claude execution handlers remain missing. Inspection reports them and returns
execution_ready false. Direct runtime creation and resume refuse before batch
allocation. Cross-profile schemas, protocol/case pins and host configurations are
refused. Existing Codex preparation and runtime regressions are checked separately.
Actual qualification, a complete executable live package and explicit live authority
remain open. This is preparation software only and does not close G6 or Part 5.

Final conformance/documentation verification passed 75 tests in 105.63 seconds,
plus Ruff and whitespace checks. Tests used authored qualification and local peers.
Initial sandbox failures and preliminary results remain under
`examples/utility/verification-claude-conformance-preparation-v1`. Current source
hashes are saved there. No full default/Bayes or installed runtime rerun is claimed.


## Claude conformance runtime increment

Runtime schema 1.1 now selects BatchClaudeHost for text, all four roles, timeout,
cancel and malformed-output repair. A separate fixed-Anthropic evidence reader
binds original model/lease/path, API version, route, intent and response bytes.
It opens no credential and dispatches no work. Local stopping and remote
completion stay separate. Missing usage categories stay unknown. Runtime origin
versions distinguish the existing Codex path from the new API path.

Owner loss remains unimplemented. The ordered runtime stops before it and the
report stays incomplete. The malformed handler is checked in isolation after an
explicit unit-only owner verdict. That test does not establish owner-loss behavior.
A missing implementation prevents live_conformance_complete even if fixture case
verdicts all say passed. Positive authored provider-proof stubs are also rejected
as live evidence. Actual qualification and any live calls remain separate gates.

Final conformance, fixed API worker/upstream and documentation regressions passed
134 tests in 147.27 seconds. Ruff and whitespace checks passed. The source remained
unchanged during that run. Logs, retained fixture failures and source hashes are
in `examples/utility/verification-claude-conformance-runtime-v1`. No actual provider
or real credential was used. These authored checks do not qualify a host.


## Claude owner-loss implementation

The remaining conformance handler now holds the fixed API worker before lease
preflight and interrupts only its owned supervisor. Claude's separate abandoned
reader verifies original native inputs/job binding, API exchange/request, fixed
worker sources, both watchdogs and absence of their shared supervisor. It never
launches, signals, opens a lease or contacts an old endpoint. Partial completed
records need their normal decoder. Unknown usage, duration and resolved model
remain unknown and the permanent reservation remains charged.

All six Claude handlers are implemented. execution_ready describes that software
availability, not actual qualification or live authority. Authored native/profile
and provider-proof fixtures remain distinct from the owned worker/watchdog tests.
No actual provider or real credential is used. The complete Part 5 gates remain
open, including actual qualification and independent scientific confirmation.

Final checks passed 295 host/conformance/recovery/API/documentation tests, plus six
follow-up corruption checks. Runtime source stayed fixed. Ruff and whitespace
checks passed. One original owned case, its test bootstrap/native peer and digest
index are retained under verification-claude-conformance-owner-v1. The full authored
six-case run completes and replays unchanged, but live conformance remains false.


## Owned CFPreferences domain observation

A new current-source diagnostic targets one generated synthetic user-domain key.
The control can read it with the native private HOME environment; the substituted
probe under the Claude policy cannot. Owned processes stop. The key is cleared.
Asynchronous plist flush initially prevented bounded empty-file deletion. Original
failures remain. Caller-pinned cleanup reconciliation verifies original process
and control records, removes only the empty owned file, and starts no new probe
or CFPreferences call. Watchdog process-observation helpers remain explicit.
All generated domain files are now absent.

Claude qualification 1.1 requires preferences.owned_user_domain_canary_not_visible
in addition to the previous checks. Version 1.0 and a missing service-domain check
are refused. Codex requirements are unchanged. This substitutes a canary executable
and does not qualify actual native preference behavior or a complete host. No
actual qualification, key, provider or independent confirmation was used.

The final 135 profile/host/preparation/canary/documentation checks and Ruff passed.
Raw controls, failures, cleanup receipts and source snapshots are preserved under
examples/utility/verification-claude-preferences-v1. Full Part 5 remains incomplete.


## Private scorer access ordering

The RMSE scorer now registers opaque label/prediction metadata without reading
labels. It validates public predictions and selected identities first, then writes
a private access intent before its only label read. The confirmation service's
reservation/access event precedes that call. Uncertain preparation or launch stays
charged and cannot be retried. Saved recovery verifies original public input,
worker and owned-process bindings without reopening labels or rescoring.

The private-json-rmse-macos-v2 identity binds parent source as well as worker,
inputs, outcome, partition, boundary and timeout. Old v1 attempts are not upgraded.
The actual macOS memory boundary is still unqualified and refuses before private
access. Authored positive boundary tests do not override that refusal.

Final checks passed 93 tests with two expected memory-qualification skips, plus
Ruff and whitespace checks. Source and logs are under
examples/utility/verification-private-access-v2. No real private/independent data
or provider was accessed. Full Part 5 remains incomplete.


## Confirmation cost projection

New public confirmation receipts optionally carry a versioned callback measurement
bound to grant, scorer and exact public score. The service measures elapsed time
only around the trusted scoring callback. That duration includes private I/O and
nested workers inside the callback. It excludes registration, grant validation and
reservation work, and it is neither CPU time nor a runtime enforcement mechanism.
Do not add it to overlapping worker durations or describe it as total phase cost.

Accounting now emits confirmation-category reservations, committed access intents
and committed scores. A measured callback adds its completion count and duration.
Worker/model starts remain unknown. Legacy receipts retain their exact serialized
shape and unknown callback time. Uncommitted scores and interrupted callbacks also
retain unknown time. Public reports/CSV exports do not open private data, invoke
the scorer, sample a new duration or fill unknown quantities with zero.

An outstanding confirmation reservation is reported as reconciliation_required,
not not_attempted. Complete-cost evidence remains false: solver/training work,
preparation, CPU/GPU/RSS, provider and human-effort closure still need their own
physical evidence. This is accounting software, not a real confirmation run.

The final utility/documentation group passed 397 tests with 26 optional/platform
skips in 503.38 seconds. Source remained fixed. A new wheel matched 192 core Python
files and rebuilt ten synthetic public export files outside the checkout, with
original access, sockets, subprocesses and scoring callbacks denied. It reused
cached base dependencies. Logs, source hashes, raw authored data, wheel and reader
checks are under examples/utility/verification-confirmation-costs-v1. No real
confirmation or complete-cost conclusion is claimed.


## Native work in suite cost reports

Suite accounting now joins original circuit, generic callback and wind native
reports to their reserved cells. It checks typed jobs, frozen specifications,
observed report bytes and saved process output without running an entrypoint.
Invalid native evidence produces an accounting blocker. It cannot supply counters.
Native job metadata is limited to 4 MiB in this reader.

| Resource | Meaning | Limit |
| --- | --- | --- |
| Native process starts | Original process identity in a verified stopped report | A subset of generic science reservations; do not add both as starts. |
| Native inner model calls | Circuit solve records | Different from solver iterations and callback entries. |
| Driver final solver/component counters | Final shared-problem snapshot | Do not sum the shared snapshots as exclusive work. |
| Scenario solver/component counters | Sum across declared independent scenario problems | Separate from later fresh evaluation jobs. |
| Wake/gradient callback entries | Attempted/completed/failed/unresolved calls | No inferred inner wake solves or derivative operations. |

Failed traces retain unknown counts, including each generic callback's frozen
kind. Old circuit results without final counters also retain unknown fields.
The circuit verifier now checks original job/completion/stdout before accepting
its counters. Scalar outcomes and feasibility remain separate from these costs.
Full scientific, training, resource, provider and human-effort closure is still
required before any total-cost conclusion.

Final native/accounting/integration checks passed 145 tests with two optional
skips in 365.37 seconds, plus Ruff and whitespace checks. A wheel matched 193 core
Python files and projected 27 relocated authored native rows with original roots,
processes and sockets denied. It reused cached base dependencies. The old exposed
28-cell rehearsal projected 108 native rows read-only with unchanged head, zero
confirmation receipts and no new model work. Source and evidence are under
examples/utility/verification-native-cost-join-v1. Full Part 5 remains open.


## Scenario process costs in suite reports

Suite accounting also reads the supervised engineering scenario profile. It binds
an observed receipt to its reserved case, execution binding, scenario job,
original process command, completion and bounded output. The reader imports no
supplied evaluator and does not open its captured source tree.

The projection separates outer process starts, lifecycle duration and each
explicitly declared count diagnostic. Physical residuals and boolean convergence
flags are not costs. Missing solver/component/derivative counts stay unknown.
Failed processes can have a known outer start while their inner work stays
unknown. Unobserved reservations do not acquire inferred starts.

Scenario starts are a subset of science reservations. Lifecycle duration overlaps
process duration. Neither is extra work to add to its enclosing total. These
records do not close training, provider, resource or human-effort costs, qualify a
private scorer or establish scientific utility. Part 5 remains incomplete.


Final corrected-source checks passed 104 tests with one optional skip in 152.87
seconds, plus full-source Ruff and whitespace checks. The earlier broad utility
run passed 423 tests with 26 skips before the relocation correction. A wheel
matched 194 core Python files and reconstructed six authored rows with original
roots, sockets and processes denied. Failure logs and both source snapshots remain
under examples/utility/verification-scenario-cost-join-v1. No independent task,
private scorer or provider ran. Full Part 5 and complete cost evidence remain open.


## Provider token components in cost reports

Batch cost projection now retains the normalized uncached-input, cached-input,
cache-creation and reasoning-output token fields alongside input/output/total
tokens. It copies only recorded values. Missing categories stay unknown, including
legacy records and interrupted calls. It does not subtract components from totals,
replace missing values with zeros or use top-level SDK summaries in place of the
adapter's normalized whole-call usage. Components and totals can overlap and must
not be added as separate token consumption.

Accounting Markdown and comparative summaries state that overlap and retain
unknown billed spend. Existing CSV cost tables preserve unknown values as blank
cells. This exposes more of the original usage evidence. It does not measure a
provider bill, establish full cost closure or qualify a live host.


The provider component increment passed 58 focused accounting, reporting, CLI,
controller and documentation tests in 27.84 seconds. A wheel matched 194 core
Python files and reconstructed an authored suite with four tested denial controls
for original checkout/test roots, sockets and subprocesses. Optional model/provider
packages were absent. Source remained fixed during tests. Raw fixtures, reader,
source hashes and setup failure are preserved under
examples/utility/verification-provider-token-costs-v1. No provider call or real
scientific comparison ran. Full Part 5 remains open.


## Campaign lifecycle costs in suite reports

The public campaign attempt profile now joins outer process starts and committed
model lifecycle timing to its reserved suite cell. The reader follows the final
event-committed controller state. It checks the original campaign specification,
attempt, nonce-bound process receipt, lifecycle artifact and output hash. It does
not open original input/source roots, decode model arrays or import an adapter.
Journal replay rehashes committed public artifacts, including any committed
forcing override.
Campaign projections are reused within one join instead of replaying the same
journal for every observation.

The disposable state cache and mutable scratch metadata are not accounting
evidence. Missing committed lifecycle timing remains unknown, including failed
workers and recovered records without that artifact. Outer worker starts are
subsets of science reservations. They do not count inner solver, model or training
operations. Lifecycle timing runs through inspection and excludes cleanup. It
overlaps the enclosing process duration, which must not be added as extra work.

The adapter training record does not declare a cost unit. The reader validates
that record but does not report it as seconds, CPU time or dollars, or declare
training qualified. Full training/resource/provider/human-effort closure and the
independent experiment remain open.


Saved-result recovery also had a software gap: its synthesized receipt omitted
process identity, so the batch observer could not settle the original worker
charge. New campaign-recovery-receipt-v2 records preserve the verified original
identity/stop and commit the lifecycle metadata. Recovered evaluation provenance
retains the actual execution seed. This follows the existing group-absence and
nonce checks and never launches a replacement worker. Malformed process identities
remain unresolved. Legacy recovery receipts without identity retain unknown
starts and lifecycle timing and stay charged. No legacy receipt is rewritten.


Final campaign/recovery, batch science, utility execution, mixed-task, reporting,
CLI and documentation regressions passed 200 tests in 315.60 seconds. Runtime and
test sources remained fixed. An installed wheel matched 195 core Python files and
read normal, recovered and authored legacy receipts without input/source bundles.
Six controls denied original roots, sockets and subprocesses. Legacy work remained
unknown and charged. Initial 63/73-test snapshots and the two interruption-fixture
failures remain preserved under examples/utility/verification-campaign-cost-join-v1.
No independent task, private scorer or provider ran. Part 5 remains incomplete.


## Current full default regression checkpoint

The original full default process (handle 86834) terminated with exit 0: 2309 tests
passed and 109 skipped in 2231.82 seconds. JUnit totals independently match the
terminal output. All 401 pinned source/test/configuration files were unchanged
after completion. The 11469 example Python files in the preceding inventory also
retained their hashes. Source remained fixed throughout this run.

The long three-route test is an authored synthetic accounting/recovery regression
with 114 bounded scientific evaluations and no provider calls. It is not a new
independent utility experiment. Optional/runtime skips remain explicit. Private
scoring, independent task admission, actual host/platform qualification and full
cost accounting are not established by a green regression suite. Raw log, XML,
environment metadata, source pins and terminal receipt are under
examples/utility/verification-part-5-base-closeout-v1. A separate current full
Bayes regression is running and has no result at this checkpoint. Part 5 remains
incomplete.


## Current full Bayes regression checkpoint

The original full Bayes process (handle 35864) terminated with exit 0: 2365 passed,
57 skipped and 44 warnings in 2407.67 seconds. JUnit matches the terminal counts.
All 401 pinned source/test/configuration files and 11469 previously inventoried
example Python files retained their hashes. Source stayed fixed throughout. The
existing environment used Torch 2.13.0 and BoTorch 0.17.2, without installation or a
fresh dependency solve. Warnings retain Torch/SMAC deprecations, small-noise and
negative-variance rounding, and input-scaling diagnostics in the experimental BO
tests. No warning was hidden or criterion relaxed. No frozen scientific matrix ran.

The completed current base suite remains a separate 2309-pass/109-skip result.
These overlapping suites are not summed as independent tests or scientific
evidence. The current readiness check still finds four blocked task drafts, null
confirmation partitions/effect margins, an absent protocol.json and an unqualified
macOS private scorer. The custodian/runtime questions are unanswered. After the
authorized regression work became terminal, the first no-next-action audit starts
from these unresolved admission/runtime/protocol prerequisites. Part 5 remains
incomplete. Task-specific training/scoring, cost closure and independent-result
views are not declared done. Raw verification and readiness records are under
examples/utility/verification-part-5-bayes-closeout-v1.


## Independent-run prerequisite impasse

Three consecutive post-regression goal turns confirmed the same missing task
custody/admission, protected-runtime and frozen-protocol prerequisites. Both full
regression processes had already terminated with exit 0. The last two turns made
no implementation progress and did not rerun tests. Four unchanged blocked drafts
still have null confirmation partitions and effect margins. No input/runtime
choice arrived. The goal is being marked blocked, not complete. Recheck these
prerequisites on resume. Readiness records are preserved under
examples/utility/verification-part-5-bayes-closeout-v1.


A standalone synthetic-only probe is now prepared in
scripts/utility_container_probe.py. It checks cgroup memory/swap/CPU/PID values,
all five Linux capability sets, no-new-privileges, UID/GID, read-only root, bounded
tmpfs and loopback-only interface observations. Nonmatching contexts refuse.
The CLI accepts no private input path. Synthetic scoring creates its known
64-element inputs internally and executes only hash-pinned fixed-worker bytes.
Every successful output still reports qualified=false.

Focused probe/private-scorer/documentation tests passed 45 with two expected
production-profile skips. The initial sandbox-denied ps failure remains recorded.
An actual Mac memory-overrun invocation refused before allocation. No container
started, image pulled, private data read or remote/provider job ran. Actual Linux
enforcement, daemon/container identity and owner-loss/timeout proof remain unrun.
Runtime selection and data custody remain pending. This added script/test has its
own source snapshot and is not silently included in earlier full-suite counts.
Evidence is under examples/utility/verification-local-runtime-probe-v1.


## Actual local ARM64 development controls

The user approved the concrete prepared local candidate. Four bounded synthetic
containers ran serially with the cached image ID, no network/private mounts or
pulls, 64 MiB memory/no swap, one CPU and 16 PIDs. Actual preflight observed those
limits, unprivileged execution, empty capability sets and the expected read-only
root/tmpfs. An 8 MiB allocation and fixed RMSE 1.0 control passed. A 128 MiB
overrun exited 137 with OOMKilled=true. Every exact original container ID was
removed and absence checked through the local Unix-socket API.

An independent owner-pipe watchdog was armed before start; normal owner-pipe
closure caused exact-ID cleanup. This is not yet an actual owner-death test.
Cleanup can remove only the original image/name/nonce identity, and does not
require resource settings to be correct before safely removing an owned rejected
created container. New explicit no-restart hardening has separate unit checks;
raw metadata confirms zero restarts and the no-restart policy in the four earlier
executions. Their original controller copies are preserved and not relabelled as
executions of the later source. Final focused tests passed 62 with two skips.

This is partial development qualification. Actual network/path-denial controls,
timeout/cancellation/owner-loss, lost acknowledgement and relocated public proof
verification remain. No private scorer is admitted. ARM64 is not Linux x86-64 or
independent hardware. Data custody, admitted tasks and the frozen full protocol
remain unresolved. Evidence: examples/utility/verification-local-runtime-controls-v1.


The local runtime archive now has an offline verifier. All 84 raw files passed
verification after relocation with the separately retained manifest digest. The
reader hashes archived Python as data and makes no Docker or subprocess calls.
It checks saved control identities, source/image bindings, isolation settings,
results and cleanup receipts. It cannot establish current live container absence
or private-scoring admission. The focused archive/driver/probe/documentation
suite passed 74 tests in 1.13 seconds. Timeout, cancellation, actual owner loss,
isolation negative controls and lost acknowledgement still need qualification.
Independent task custody and the frozen protocol remain unresolved.


Four local synthetic lifecycle controls now have actual execution evidence under
examples/utility/verification-local-runtime-lifecycle-v1. A five-second independent
watchdog removed the running original container on deadline and after actual
SIGTERM cancellation or SIGKILL owner loss. A simulated lost start response was
reconciled against the original ID without retry. All four original IDs were
confirmed absent through live HTTP 404. The lost response is an injected controller
boundary fault, not a demonstrated transport outage or lost create response.
All 88 archived files passed offline verification after relocation. The focused
driver/probe/archive/documentation suite passed 87 tests in 1.48 seconds.
These are local macOS-owner/OrbStack Linux ARM64 controls. They do not admit a
private scorer, qualify Linux x86-64 or satisfy independent scientific confirmation.
Network/host-path negative controls, adversarial output enforcement, production
integration, independent task custody and the frozen protocol remain outstanding.


The local synthetic isolation control passed on the original pinned ARM64
container. Its mounted public canary was readable, the same unmounted host path
and parent-traversal path were inaccessible, root/stage writes failed, and tmpfs
read/write succeeded. Loopback TCP worked. The documentation-only address
192.0.2.1:9 returned ENETUNREACH under the inspected none network. No real home,
credential, label or external-service path was probed. The original container was
removed and its absence confirmed through HTTP 404. All 25 raw execution files
passed offline verification after relocation. Evidence is under
examples/utility/verification-local-runtime-isolation-v1. The final focused
probe/driver/archive/private-access/documentation suite passed 115 tests in
3.95 seconds. Its initial six sandbox failures were forbidden owned-process ps
inspection; the permitted complete retry passed and both logs are preserved.
Private scoring remains unqualified. Adversarial output enforcement, production
integration, independent task custody and the frozen protocol remain outstanding.


The fixed trusted scorer now has a packaged regular-file output wrapper. Three
actual local ARM64 controls passed: 4096-byte output, aggregate stdout/stderr
overrun at 16384 bytes with child SIGXFSZ, and bounded synthetic RMSE 1.0. All
three original containers were removed and confirmed absent through HTTP 404.
No private confirmation data was read. All 66 raw files verified after offline
relocation. Evidence is under examples/utility/verification-local-runtime-output-v1.
The focused output/probe/driver/archive/documentation suite passed 112 tests in
1.95 seconds. The offline wheel matched all 196 core Python files and the extracted
wrapper passed fixed output and authored-score checks. This is output enforcement
for the hash-pinned trusted scorer child, not a generic generated-code sandbox or
Docker stdout quota. Production private-scorer integration/admission, independent
task custody and the frozen protocol remain outstanding. Part 5 is not complete.


A programmatic ContainerRMSEScorer candidate now connects frozen prediction
artifacts, the existing confirmation grant/access service, a fixed API-driven
container runtime and offline original-result recovery. The final runtime binds
staged job/label hashes to the durable access intent before container creation.
Two distinct source versions passed synthetic end-to-end confirmation, returned
RMSE 1.0, removed their original containers and recovered after all synthetic
label copies were deleted with daemon requests forbidden. Earlier source and
harness postcheck failures are preserved. No real confirmation data was used.
The final focused suite passed 161 tests in 11.85 seconds. All 198 wheel core
Python files matched source bytes. The extracted wheel recovered a relocated
result with sockets, process starts, original-root opens and label access denied.
Evidence is under examples/utility/verification-container-scorer-integration-v1.
The candidate has no CLI/registry activation and is not qualified for real private
scoring. Its full new-source failure matrix, explicit service publication of a
recovered pending confirmation, public container cost evidence, independent task
custody and frozen authorized protocol remain outstanding. Part 5 remains active
and incomplete. The macOS profile remains unchanged.


ConfirmationService.recover(grant) now explicitly publishes a verified original
result from a registered scorer recovery method against the same charged attempt
and committed access intent. New utility-confirmation-recovery-v1 provenance binds
attempt, grant, access, scorer and score. No original callback duration or physical
start count is invented. Missing evidence remains charged and refuses retry.
A real synthetic container confirmation was interrupted before suite score commit,
then recovered after all synthetic labels were deleted with daemon access and new
starts forbidden. Its original reservation/access remained unchanged. The container
was removed and HTTP 404 confirmed its absence. No real confirmation data was used.
Focused checks passed 91 tests in 17.35 seconds, documentation checks passed 19,
and Ruff passed. All 198 wheel core Python files matched source. Public journal
and cost replay passed after relocation with private/original-root opens, scorer
calls, sockets and processes forbidden, retaining the orphaned earlier receipt.
Evidence is under examples/utility/verification-confirmation-recovery-v1. The
broader utility regression has a separate log/XML and source pins. Its final status
must be checked independently. Runtime failure-matrix qualification, public
container execution/cost receipts, independent task custody, thresholds and a
frozen authorized protocol remain outstanding. Part 5 remains incomplete.


The explicit-confirmation-recovery utility regression is now terminal: original
session 16460 exited 0 with 567 passed, 26 skipped and no JUnit failures/errors
(593 total cases, 573.25 seconds). All 395 source/test/config pins were unchanged.
Its final log/XML hashes and scope are recorded in
examples/utility/verification-confirmation-recovery-v1/regression-terminal.json.
This validates the complete utility test subset at that source checkpoint, not
the full default or Bayes suites, private-runtime admission or scientific utility.


Optional utility-confirmation-container-execution-v1 public metadata now binds
the original grant/scorer/score/runtime, container/nonce, pinned image, source
hashes and start/stop/cleanup evidence hashes without private paths or arrays.
A real synthetic interrupted confirmation recovered the same metadata with all
synthetic labels deleted and daemon/new starts denied. It reports one container
start, one scoring-child start and 0.18108187522739172 seconds from start request
through stopped inspection. Original callback time remains unknown after recovery.
Nested duration is not added to callback time or called total phase/CPU cost.
The original container was removed and its absence confirmed through HTTP 404.
The focused execution/runtime/scorer/recovery/cost/report/analysis/docs suite
passed 126 tests in 21.73 seconds. The offline wheel matched all 199 core Python
files. New and legacy receipts replayed after relocation with private/original
roots, scorer methods, sockets, processes and optional scientific imports denied.
Legacy shape/digests and unknown starts were retained. Evidence is under
examples/utility/verification-public-execution-v1. Runtime/scorer configuration
drift refuses before further private use. The prior 567-pass utility regression
retains its earlier source scope. Full candidate-runtime failure qualification,
independent task custody, thresholds, unmeasured cost categories and a frozen
authorized protocol remain open. Part 5 is active and incomplete.


The fixed private-container runtime now records ownership before creation and
reconciles only that original name/nonce/ID after lost acknowledgement or pipe
setup failure. A missing name without a known ID remains uncertain, never
no_launch or refunded permission. Explicit stop=True permits original-only
removal; observation/reconciliation reads no label/job arrays and starts no work.
Cleanup retry preserves original snapshots. Actual local lost-ack and pipe-failure
controls each created one object, issued no start, and removed the exact original
ID. A distinct success/recovery control on the same source still returned RMSE
1.0 and replayed after label deletion with API/new starts denied. The combined
suite passed 139 tests in 21.84 seconds; seven creation tests passed after unused
import cleanup, and Ruff passed. All 199 wheel core files matched source; relocated
new/legacy public replay denied private/original roots, scorer calls, sockets,
processes and optional scientific imports. Evidence is under
examples/utility/verification-container-creation-v1. These source-specific controls
do not complete private-runtime admission. Full lifecycle/failure qualification,
independent task custody, thresholds, unmeasured costs and a frozen authorized
protocol remain open. Part 5 remains active and incomplete.


Six actual creator-termination controls now cover SIGTERM/SIGKILL before create
acknowledgement delivery, before pipe setup and after watchdog arming but before
start delivery. Four pre-arm controls reconciled from durable original metadata
after job/label deletion, rejecting data reads and all POSTs. Two armed controls
were removed automatically through owner_pipe_eof, with no observer deletion.
All six original objects remained created/Pid=0, were removed and returned HTTP
404. No scoring workload started or real confirmation data was used. The unchanged
core still matched all 199 files in the existing wheel, which was reused. The
relocated verifier checked all 120 archived files; 71 focused tests passed in
0.85 seconds and Ruff passed. Evidence is under
examples/utility/verification-container-creation-owner-v1. These controls do not
establish active-workload interruption or full candidate runtime admission.
Remaining acknowledgement/resource/privacy qualification, independent task custody,
thresholds, unmeasured costs and a frozen authorized protocol keep Part 5 open.

The owner-control verifier now refuses job/label archive members before file
access. Its final focused suite passed 72 tests in 0.88 seconds. The earlier
71-test record is preserved. Runtime source and actual control evidence were
unchanged by this reader-only guard.


Five actual running-container controls now cover cancellation (SIGTERM), owner
loss (SIGKILL), lost start acknowledgement, the independent watchdog deadline
and the runtime poll timeout. Each observed the same original running PID before
and after pause. All five original containers were removed automatically, with
HTTP 404 observed and no observer deletion or replacement attempt. No scientific
result was accepted. Scoring-child starts remain unknown. The pause-induced hang
does not identify a model computation phase. The four-control 90-file archive and
separate 23-file timeout archive replay without daemon/process access. Their
focused archive/creation/runtime suite passed 49 tests in 0.56 seconds and Ruff
passed. All 199 unchanged core files matched the existing wheel, which was reused.
Evidence and manifest hashes are in
examples/utility/verification-container-running-v1/README.md. Full current-runtime
resource/privacy/output/result-commit qualification, independent task custody,
thresholds, unmeasured costs and a frozen authorized protocol remain open.
Part 5 remains incomplete and private scoring remains unqualified.


Fixed-container live output and saved recovery now use one strict output schema.
Duplicate JSON fields, nonfinite numbers, Boolean/float process counters, unknown
fields and invalid RMSE/failure semantics refuse. Metadata parsing also rejects
duplicate/nonfinite JSON, without returning rejected content in errors. The
initial regression recorded 17 failures/four passes; the final focused suite
passed 131 tests in 12.40 seconds and Ruff passed. One actual synthetic container
on this changed source returned RMSE 1.0 W; recovery after label deletion and
before suite publication retained the original reservation/access with API/new
starts denied. A fresh wheel matched all 199 core files. Its relocated offline
reader recovered that original result and refused rehashed duplicate output with
sockets/processes/API denied. A stdlib import-order failure in the first offline
harness is preserved; correcting the harness started no additional container.
Evidence is under examples/utility/verification-container-output-validation-v1.
Earlier interruption controls and full-suite results retain their old source
scopes. Current-source complete runtime qualification and the independent task,
threshold, cost and frozen-protocol requirements remain open. Part 5 is incomplete.


Completed-result recovery now verifies the original create intent, pending and
acknowledged ownership, exact configuration, all staged hashes and strict
created/exited lifecycle states. Live start/completion share those state checks.
It also refuses symlinked evidence directories, invalid watchdog/receipt schemas,
negative or Boolean durations and projections that agree only by numeric type
coercion. Missing legacy time remains unknown and relocated evidence remains
readable without private arrays or daemon access. Initial regression: 23 failed,
one passed. Final focused suite: 160 passed in 12.59 seconds; Ruff passed. One
actual synthetic container on the changed source returned RMSE 1.0 W and recovered
after label deletion while retaining the original reservation/access. All 199
wheel core files matched current source. The installed relocated reader recovered
the original and refused contradictory start-state/ambiguous-output evidence with
network, process starts and daemon API denied. Evidence is under
examples/utility/verification-container-recovery-chain-v1. The complete utility
regression is recorded separately when terminal. Earlier source-specific controls
are preserved. Full runtime qualification and the independent task/threshold/cost/
frozen-protocol requirements remain open. Part 5 remains incomplete.


The current complete utility regression is terminal: 680 passed, 26 skipped in
570.86 seconds. JUnit records 706 cases, zero failures and zero errors. All 12,426
pinned source/test/example/configuration files remained unchanged. Original
session 25197 exited zero. Exact command, environment, hashes, raw log, JUnit and
terminal receipt are under verification-container-recovery-chain-v1. This updates
the utility regression checkpoint only; full default/Bayes/interoperability and
older actual interruption controls retain their prior source scopes. Complete
runtime admission and the independent study remain unverified.


Current-source lifecycle controls now cover six creator terminations (before
create acknowledgement, before pipe creation and after arming) and five paused
running faults (SIGTERM, SIGKILL, lost start acknowledgement, watchdog deadline
and runtime timeout). Eleven original objects were removed and observed absent;
five containers started, no replacement or scientific result was accepted and
scoring-child starts remain unknown for the running controls. Four pre-arm
objects required explicit metadata-only reconciliation after input deletion.
The other seven were removed automatically, with no observer deletion. All 233
archived files replayed after relocation with sockets/processes/API denied.
The focused archive/recovery/runtime suite passed 71 tests in 0.62 seconds and
Ruff passed. All 199 core files remained unchanged and matched the existing wheel.
The 680-pass/26-skip utility checkpoint retains its source scope without a rerun.
Evidence is under verification-container-current-lifecycle-v1. Earlier controls
remain preserved. Current-source lifecycle coverage no longer relies on older
runtime hashes, but full resource/privacy/failure admission and the independent
task, threshold, cost and frozen-protocol requirements remain open.


A metadata-only readiness audit after lifecycle closure verified all four task
dossiers remain blocked_draft with null confirmation partitions, unknown exposure
and null useful-effect/secondary thresholds. The independent protocol is absent.
Actual CLI help confirms the planned confirm command is not implemented; the
programmatic service is not a substitute. The specific external inputs and
remaining software/platform/host/report work are recorded in
part-5-readiness.md, with machine observations/hashes under
verification-readiness-audit-v1. All 199 core files remain unchanged. No labels,
models, providers, new scoring profiles or independent runs were used. The full
objective remains incomplete; this is no completion or blocked-status decision.


The planned confirmation CLI now dispatches and explicitly recovers through
ConfirmationService using application-owned trusted registrations. It binds the
suite, partition, scorer/outcome and qualification digest, checks sealing before
pinning public control metadata, refuses registration drift and retains original
uncertain charges. No user JSON/import string/flag can register a scorer. The base
CLI has no admitted private profile. The final CLI/confirmation/recovery/cost/report
suite passed 100 tests in 21.53 seconds and Ruff passed. A matching 200-file wheel
ran four separate authored CLI processes: interrupted publication, refused retry,
original recovery and committed replay. Only one callback and one recovery ran;
reservation/access stayed unchanged, network/process starts were denied in the
wrapper and no optional scientific framework loaded. Raw nine initial failures
and three later fixture-assertion failures are preserved. The runtime and worker
payloads did not change. The prior 680-pass utility checkpoint retains its earlier
source scope. Evidence is under verification-confirmation-cli-v1. Actual private
profile admission and independent task/protocol/platform/host requirements remain
open. The full goal is not complete.


Shared-baseline readers now refuse cross-scenario reuse and any alias target with
an existing confirmation reservation/attempt/result. Previously, cross-scenario,
reserved and started target cases could be accepted; separately scored targets
were already rejected later through duplicate-cell validation. Three acceptance
regressions were reproduced after correcting an overly specific diagnostic test.
The final baseline/analysis/report/confirmation/recovery/CLI/cost suite passed
89 tests in 16.35 seconds and Ruff passed. A matching 200-file wheel reconstructed
relocated authored public fixtures with original roots, sockets and processes
denied: valid reuse kept two logical cells/one receipt, while reserved and
cross-scenario cases refused without changing charges. No scorer ran during
reconstruction. Evidence is under verification-baseline-reuse-guards-v1. Runtime
and worker payloads are unchanged. Execution-time baseline sharing, full private
admission and independent task/protocol/platform/host/report work remain open.
The full Part 5 goal is incomplete.


Frozen deterministic baseline confirmation reuse is now an explicit suite-v2
profile. Groups bind source/follower cells, model, default parameters, scorer and
cost shares into the protocol/suite identity. V1 bytes/deserialization remain
exact. The service verifies common sealed state before access and the journal
forbids follower reservations. Only the source scores; ordinary original-result
recovery/replay applies. Successful feasible source results and cost shares are
reconstructed automatically, with reused cells marked. Failed sources remain
recorded and leave followers unscored. The final focused suite passed 131 tests
in 22.25 seconds and Ruff passed. A matching 201-file wheel exercised six CLI
processes with one authored callback/recovery, no follower charge, and installed
relocated export reconstruction. One physical reservation split 0.25/0.75 while
retaining its original total. The installed reader also preserved a saved v1
suite's bytes/digest. Full utility regression is recorded separately when terminal.
Evidence is under verification-baseline-confirmation-v1. This implements
confirmation sharing after sealing a common immutable reference; selection-stage
reference preparation/route integration, actual private profile admission and the
independent study requirements remain open. Part 5 is incomplete.


The complete utility regression for the frozen-baseline-confirmation source is
terminal: 711 passed, 26 skipped in 594.25 seconds. JUnit has 737 cases, zero
failures and zero errors. All 12,475 pinned source/test/example/configuration
files remained unchanged. Original session 4703 exited zero. Exact command,
environment, logs, JUnit, source hashes and terminal receipt are retained under
verification-baseline-confirmation-v1. Full default/Bayes/interoperability and
older actual controls keep their own source scopes. This is no private admission
or independent scientific confirmation. Part 5 remains incomplete.


A task-binding integration defect was fixed before adding selection-reference
caching. Execution validators require the campaign acceptance digest in the
legacy outcome_digest field, while confirmation requires a different OutcomeSpec
digest. The explicit utility-task-scoring-v2 ScoredTaskSpec now preserves the
acceptance binding and separately freezes scoring_outcome_digest. Legacy task
bytes/direct semantics stay exact. Wrong/missing/untagged bindings refuse before
access; a change creates a new suite identity. A bounded authored engineering
fixture actually executed selection, sealed its result and reached an authored
primary-outcome callback without relabeling acceptance. The final focused suite
passed 79 tests in 14.46 seconds and Ruff passed. A matching 201-file installed
wheel exercised four CLI publication/retry/recovery/replay processes. Its offline
reader reconstructed both archived suites with original roots/network/processes
denied and retained legacy bytes/digests. No independent/private confirmation was
performed. Evidence is under verification-task-scoring-binding-v1. The earlier
711-pass full utility checkpoint retains its prior source scope. Selection-stage
reference caching and the independent task/profile/protocol/platform/host work
remain open. Part 5 remains incomplete.


Final archive lint found an unused import in the preserved executed fixture.
An artifact-local Ruff configuration excludes only that immutable execution tree
from development lint while inheriting project rules elsewhere. Source bytes and
the failed log were retained. The provisional terminal lint claim was corrected;
archive-lint-verified.log records a separate successful command. This correction
changes no scientific gate or executed implementation.


Selection-stage baseline reference reuse is now an explicit policy-v2 option.
The source executes once; metadata-only batch-v1.1 followers have zero host and
scientific allowance and carry original child-result/model/state lineage.
Existing batch/policy-v1 shapes and behavior remain. Source order and supplied
model/defaults are checked before dispatch. Prediction and engineering paths share
the reference helper, with mixed execution delegating to them. Lineage is checked
before finish, on offline result reads and at selection freeze. Fault recovery
starts no new science. Frozen cost shares retain original physical receipts;
copy duration is explicitly unknown. The final focused suite passed 82 tests in
66.25 seconds and Ruff passed. A 34-cell case crossed child batches with one
scientific evaluation. Engineering selection/sealing reached one authored
confirmation callback with the separate scoring contract. A matching 202-file
wheel ran installed CLI run/resume/freeze: four logical selections, one scientific
process and one common state. The relocated reader verified all lineages/costs
with original roots/network/processes denied. Evidence and adverse logs are under
verification-baseline-selection-v1. This closes the exposed scripted selection
reference integration gap, not independent task admission or private qualification.
The complete utility/batch regression is recorded separately when terminal.
Part 5 remains incomplete.




The complete utility and batch regression for selection-reference reuse is
terminal: 759 passed, 26 skipped in 655.24 seconds. JUnit records 785 cases, zero
failures and zero errors. All 12,632 source/test/example/configuration pins
remained unchanged. Original session 36509 exited zero. Exact command,
environment, source hashes, log, JUnit and terminal receipt are retained under
verification-baseline-selection-v1. Full default/Bayes and earlier runtime/host
qualification retain their source scopes. This does not admit independent data
or private scoring. Part 5 remains incomplete.

Direct analysis now enforces frozen baseline groups and cost fractions. Both
raw scores and pinned public envelopes reject changed allocations. Failed or
infeasible source scores cannot expand to followers, and followers cannot carry
separate physical scores. Legacy manual reuse remains supported. The regression
first reproduced changed fractions and failed-source expansion, then passed 94
analysis, reuse, selection, reporting, cost and documentation tests in 70.75
seconds. Ruff and whitespace checks passed. One earlier test command named a
nonexistent report test and ran no tests. A subsequent sandboxed selection run
failed process inspection and lacked the required child Python PATH. The final
94-test run supplied both. This small patch has no new installed-wheel or full
default/Bayes qualification. Public declaration checks do not establish original
source provenance. Four task dossiers still lack independent partitions and
scientific thresholds. Part 5 remains incomplete.


The direct-analysis policy patch now has an installed check. A wheel built from
a temporary source copy matched all 202 core Python files. Outside the checkout,
10 baseline-analysis/public-receipt tests passed in 0.79 seconds against the
extracted package with inherited base dependencies. Build/test logs, JUnit, wheel
hash, package origin and source hashes are saved in
verification-direct-analysis-installed-v1. This does not repeat the complete
installed workflow or admit private scoring. The full default regression remains
running separately in verification-current-base-v1 until its terminal record.


The current full default regression is terminal: 2,616 passed, 109 skipped in
2,128.54 seconds. Original session 49934 exited zero. JUnit contains 2,725 cases,
zero failures and zero errors. All 77,844 pinned existing source/test/example and
configuration files remained unchanged. Exact invocation, logs, JUnit, before/after
hashes, terminal record and independently checked totals are retained in
verification-current-base-v1. The separate collection snapshot was informational;
the executed JUnit is the authoritative denominator. This is a default-environment
result, not a fresh Bayes/interoperability or independent platform qualification.
Private scorer admission, independent partitions and scientific thresholds, actual
second-host conformance, Linux x86-64 and the full frozen experiment remain open.
Part 5 remains incomplete.

The final-test input question was clarified after the author found it unclear.
A separate person or pre-existing private dataset is not required by the plan.
The new part-5-confirmation-proposal.md names CAMELS Choptank 01491000, PVDAQ
2107, 24 authored circuit load/ground cases and WIND Toolkit resource years.
It proposes reserved periods, useful-effect margins, secondary limits and the
480-adaptive/560-logical-cell planning matrix. Public metadata checks confirmed
the basin identity and solar driver/AC channels. The solar metadata advertises
2018-2023 support, while actual completeness remains unverified. Catalog and
object-name checks fetched no proposed outcome files. Factual metadata, hashes
and access limits are saved under examples/utility/proposals/confirmation-v1.
The task dossiers and executable protocol remain unadmitted. Prior personal use,
rights, quality, source-specific adapters, protected scoring and numeric execution
caps still need closure before final execution.


The separate engineering_load development adapter exposes scalar ground and
resistor forcing while retaining source current as the only design variable.
It projects the two load ports onto native resistor options, uses the existing
OpenMDAO lifecycle/solver, checks residuals with actual resistances, and preserves
native work counters and source identity. The supplied execute callback uses the
existing supervised executor and batch receipts. No second runner or ledger was
added. One owned authored process completed and its saved result recovered with
new process launch forbidden and exactly one reservation retained.

The interoperability regression passed 29 tests with three framework warnings in
5.79 seconds. The first supervised test assertion used the wrong return-field
name after a successful process; that assertion was corrected. Default import
and documentation checks passed 20 tests with eight optional-framework skips in
2.27 seconds. Ruff and whitespace checks passed. The documented authored example
ran with a constitutive residual of 1.9916793908558716e-16 A. New load solves used
values outside the proposed final grid, and legacy controls used already exposed
nominal cases. No proposed final scenario was evaluated. All 202 core Python
files and the original circuit/engineering files remain unchanged from the full
default checkpoint. This increment has no installed-wheel or complete-suite
rerun. Multi-load native optimization, final scoring/isolation and study admission
remain open. Part 5 remains incomplete.


The native load recipe preserves OpenMDAO SLSQP and total derivatives for
positive-current passive circuits whose supplied scenario set contains the
minimum-ground/minimum-R1/maximum-R2 corner. The circuit equations prove that
this case controls the voltage bound and that its lowest feasible current also
minimizes mean power. Missing corners refuse before model construction. Native
calls retain an exact cap with fresh-check capacity reserved for every supplied
case. The result records each independent fresh solve and leaves strict scientific
acceptance authoritative, including a numerically marginal optimizer proposal.

The related interoperability regression passed 52 tests with six framework
warnings in 28.51 seconds. Native tests independently calculate the circuit-law
current boundary, exercise an exhausted one-call driver with cleanup, and run one
owned native job with reconciled costs and recovery while new starts are denied.
Default checks passed 25 tests with 11 optional skips in 2.00 seconds; final
documentation checks passed 19 tests in 0.91 seconds. Ruff and whitespace checks
passed. All new scientific load cases are authored and outside the proposed final
grid. The original core and ground-only model/driver remain unchanged. No full
suite, installed-profile qualification, private scoring or final comparison is
claimed by this increment. Part 5 remains incomplete.


Installed load development qualification is now recorded under
verification-engineering-load-installed-v1. A fresh wheel matches all 286 packaged
Python files, including 202 core files and 31 utility example modules. From outside
the checkout, the installed callbacks ran two fixed load processes and one native
process on the same two authored cases outside the proposed final grid. Exactly
three original reservations remained, and completed recovery added no starts.
The native record reconciled 13 inner model calls and its solver/derivative work.
Interoperability dependencies were inherited rather than freshly installed.

A separate base-environment reader reconstructed the copied native report and
parent receipts while denying original source/run roots, model imports, process
launches and network access. All 51 copied batch files remained unchanged. This
reader scope does not claim a full suite report or fixed-outcome reconstruction.
Executed harnesses, wheel hashes, public receipts and results are retained. Two
initial setup failures were before batch creation: an incorrect interpreter path
and an owner-private parent check. Correcting those started no duplicate science.
No package/model source code or prior scientific evidence was changed by this qualification.
Protected scoring, independent-data admission and the full comparison remain open.
Part 5 remains incomplete.


The metadata-only source-access review now records exact dataset terms and access
paths under examples/utility/proposals/confirmation-v1. The official OEDI catalog
(11,079,728 bytes, bounded at 32 MiB) identifies PVDAQ submission 4568 as CC BY
4.0. Only its selected factual record and the catalog hash were retained. The
generic OEDI AWS registry instead lists CC BY 3.0 US, so the two scopes remain
distinct. CAMELS DOI metadata links the proposed Zenodo archive and retains a
registration condition under UCAR terms, which is not silently waived.

The WIND Toolkit managed registry declares CC BY 3.0 US and anonymous S3 access.
Anonymous metadata listings succeeded. Annual CONUS objects for 2007-2013 are
v1.0.0, while 2014 is v1.1.0. All eight total 12,295,111,327,536 bytes. This does
not authorize bulk retrieval. The proposal retains its periods and names the
version-comparability and bounded-extraction requirements. No observation files,
weather values, final outcomes, credentials, personal identity or extraction jobs
were submitted or retrieved. Public metadata accessibility does not establish
prior exposure or scientific admission. Task dossiers remain blocked drafts.


The separate hydrology_partitions preparer accepts canonical daily rows under a
strict plan binding source/site, area, latitude, quality flags and four contiguous
windows. It separates development forcing and role-specific fitting/selection
labels from full causal-replay forcing and confirmation-only masked labels.
The reserved label format is consumed by the unchanged fixed RMSE worker.
Precipitation is an explicit P1D interval total, mean temperature is the declared
min/max midpoint, and cfs conversion uses the defined SI factor and basin area.

Immutable owner-private scope claims precede row iteration. They and the manifests
bind the preparer code digest. Data are validated before publication, private
artifacts commit first and the public manifest last. Occupied roots, symlinks,
bad dates, missing drivers and unusable roles refuse. Private error text is
suppressed. Partial artifacts remain and cannot be overwritten by a retry.
The public manifest explicitly withholds source-byte, model, exposure and privacy
admission. The old PET functions' default 31.7 degree latitude remains unsuitable
for silently admitting a new basin.

All 13 new tests passed after correcting the authored fixture to use the existing
portable identifier convention. The first broader regression had six existing
private-access failures because the sandbox denied ps, with 44 passing tests.
With owned-process inspection allowed, the final related regression passed 50
tests. Documentation checks passed 19 tests in 0.86 seconds. Ruff and whitespace
checks passed. No real source observations, scientific models, providers or final
partitions were acquired or evaluated. Raw CAMELS parsing, actual source hashes,
site-specific model behavior and privacy/exposure qualification remain open.
Part 5 remains incomplete.


The separate hydrology_site adapter now binds immutable basin source/site,
latitude and area. It calls the unchanged Hamon/Hargreaves functions with explicit
latitude, retains the soil bucket and conservative reservoir equations, and
refuses polar geometry beyond 66 degrees. Port units, clocks, site metadata,
implementation identity and forcing ordering are checked before physics. Each
fresh handle replays history once, with half-capacity initial soil and an empty
reservoir. Reusing a consumed handle refuses instead of advancing the same dates
twice. The legacy Leaf River adapter and its defaults remain unchanged.

The prepared-development bridge accepts only the exact driver prefix through
selection, with no labels or reserved dates. It verifies the declared temperature
midpoint and returns isolated read-only arrays. Fitting/selection date masks stay
separate from the preparer's label-quality masks. Authored tests independently
reconstruct all daily stores and fluxes for both PET families and exercise the
actual preparation-to-lifecycle path while denying label/private-file reads.

Focused checks passed 32 tests with one optional solar skip. The related
regression passed 77 tests with one optional solar skip in 5.60 seconds, covering
documentation, campaign contracts, preparation and prediction profiles. Ruff and
whitespace checks passed. All 286 packaged Python files in the prior installed
wheel match current bytes, including all 202 core modules. The preceding
hydrology_partitions module also matches its recorded pin. The new site adapter
and partition preparer have no installed-wheel qualification. No real observation
files or final scenarios were acquired or evaluated. CAMELS parsing/source
verification, basin adequacy, conservative learned alternatives and privacy/
exposure qualification remain open. Part 5 remains incomplete.


The new hydrology_camels parser accepts bounded CAMELS-US Daymet forcing and
streamflow bytes. An immutable source record binds the gauge, both SHA-256
checksums and the declared forcing hour. The preparation plan binds that record's
digest. Parsing checks header units, latitude/area, flow gauge/date columns and
the complete daily axis. It does not sort, fill, fetch or extract archives.
The supported -999 flow sentinel becomes missing, quality flags remain explicit,
and observed zero remains valid. Invalid drivers and unknown negative flow refuse.
The complete pair is validated before yielding any normalized rows. When passed
directly to the preparer, parsing follows immutable output-scope claims.

Format references were checked against the eWaterCycle-HBV documentation,
NeuralHydrology's CAMELS-US loader and NCAR's hour-field discussion. The latter
records hour 12 in Daymet files versus hour 0 in documentation. The parser checks
a declared value without moving dates. That check does not resolve the scientific
forcing/flow interval interpretation. No actual observation files were read.

Authored tests exercise source corruption, units, site metadata, gauge/date
alignment, missing values, quality masks, resource bounds and partial-preparation
refusal. One path runs parsed bytes through partition preparation, the site
adapter and physical checks. The first focused regression passed 57 tests. After
adding invalid-flag coverage, the related regression passed 105 tests with one
optional solar skip in 4.00 seconds. Ruff and whitespace checks passed. All 286
previously qualified packaged Python files and the preceding site adapter/tests
remain unchanged. No real-source, installed-package, exposure or private-runtime
admission is claimed. Acquired-source validation, source authenticity/rights and
daily interval semantics remain open. Part 5 remains incomplete.


The new hydrology_learned development profile replaces constant linear release
with a supervised two-coefficient logistic release fraction driven by available
reservoir storage. Its fixed log1p storage feature uses a 100 mm scale. The
nonnegative storage coefficient makes release fraction nondecreasing. Discharge
is bounded by available water and the remainder stays in the explicit reservoir.
PET and the soil bucket remain supplied site equations. The profile exposes all
required stores/fluxes. Its model parameters are capacity and PET family, with
no unused linear recession search parameter.

The immutable training profile binds fitting dates, warmup, quality mask and a
routing-rollout cap. Bounded deterministic SciPy least squares refuses failed or
numerically rank-deficient fits. Every residual evaluation, including derivative
calls, is counted against the cap. Training intents/results are create-only in
owner-private scratch. Failed work retains routing starts, completed work,
partial-work uncertainty, flux preparation counts and elapsed time. An unresolved
intent or an occupied directory cannot start training again. These artifacts are
development evidence, not a new suite ledger or qualified recovery service.

Frozen JSON fits bind coefficients, fixed feature/algorithm, source/environment,
parameters, fitting-data and forcing digests, seed and work/time records. Inference
requires the same fitting-driver prefix and source/model identity, permits a
longer causal replay, accepts no labels and invokes no optimizer. The prepared
training bridge takes fitting artifacts only. It excludes selection and reserved
labels and separates training-prefix drivers from full development drivers.
The old public learned-candidate admission refusal remains unchanged.

The first new-test run passed nine tests and failed four because the generic
artifact writer expects an artifacts directory. The profile now creates and
validates that owner-private parent. All 13 initial tests then passed. The first
broader run had 88 passes, one optional skip and 12 existing process-supervision
failures. Direct inspection confirmed that the sandbox denied /bin/ps. With owned
process inspection allowed, that regression passed 120 tests with one optional
solar skip in 41.86 seconds. Later prepared-artifact and handle tests passed in
the final focused regression: 110 passed, one optional solar skip in 2.09 seconds.
Ruff and whitespace checks passed. All 286 previously qualified packaged Python
files and the three preceding hydrology source/test pairs remain unchanged.

Authored tests recover known coefficients, independently check conservative
states/fluxes, preserve valid zero labels, and reject scope, identity, artifact,
budget and retry violations. They do not establish useful real-data gain.
No real basin was trained and no independent task or training profile was admitted.
Supervised resource/failure qualification, suite training reservations and cost
extraction, source/data admission and training sufficiency remain open. Part 5
remains incomplete.


Hydrology training profile/fit contracts now live in the offline utility layer,
with existing example imports preserved. The JSON profile/fit schemas keep their
prior meanings. The learned adapter emits version 2 training intents/results,
adding a unique attempt ID. Repeated fits with identical model/seed identity now
remain distinct work, while aliases retain the same cost receipt identity.
The model source closure includes the new core contract/reader module.

The new read_training_costs reader accepts committed artifact references plus
frozen expected identity, profile, seed and cell. It validates limits, work/day
counts, partial-work flags and the digest-verified fit's counters and duration.
It emits existing CostRecord quantities, without another ledger. Missing results
and partial work retain unknown quantities. Reconciliation rejects duplicate
charges. V1 development intents/results are not silently promoted to this v2
projection. Parent-commit verification and reservations remain caller obligations.

Tests cover rehashed inconsistencies, limits, schema/type errors, corrupt fit
bytes, unknown work and repeated charges. An actual authored fit was copied and
read in a separate process with model/optional-framework imports, optimizers,
subprocesses, sockets and unrelated Path.open/os.open reads denied. Two actual
fits under the same model identity produced different attempt IDs. The first
reader test incorrectly blocked core SciPy imports made by the generic artifact
reader. Its guard now permits core dependencies while explicitly denying model
imports and scientific execution. One Ruff lambda-style error was corrected.

The focused tests passed 42 tests. The broader related regression passed 129
tests with one optional solar skip in 2.79 seconds. Documentation/preparation
checks passed 39 tests in 1.50 seconds. Ruff and whitespace checks passed. All
286 Python files from the previous qualified wheel, including its 202 core
files, remain unchanged. There are now 203 core Python files. The prior learned
profile tests remain unchanged, while its source has this explicit successor.
The new reader and updated profile lack installed-package/full-suite qualification.
No real basin or independent task was trained or scored. Supervision, parent
commit binding, suite reservations and automatic cost/report integration remain
open. Part 5 remains incomplete.


Successful worker training artifacts now join the authoritative campaign lifecycle
commit. TrainingArtifactBundle declares one primary artifact and at most eight
content-addressed companions, with 4 MiB total companion bytes. The learner exports
its profile, intent and result alongside its fit. Parent capture verifies the
worker output hash, finite duration and training record, then retains every
explicit artifact with its original digest/path. Training-bearing lifecycle
metadata uses version 2 and retains the original worker training reference.
Legacy untrained metadata retains its exact bytes.

Completion and saved-worker recovery share the capture function. The returned
references join the same original-attempt event, without another training ledger
or scientific runner. Recovery copies verified bytes without launching work.
Corrupt, missing, symlinked or mismatched companions refuse capture. An actual
authored fit was captured and reconstructed with scratch reads denied. Supervised
scalar transport fixtures carry a separately authored training envelope through
normal completion and event-loss recovery, retaining one scientific reservation.
They do not qualify learned-model training inside that worker.

Initial focused checks passed 45 tests. The campaign/recovery/process regression
passed 81 tests in 83.16 seconds with owned-process inspection allowed. Later
corruption, metadata, documentation and preparation checks passed 28 tests with
two process cases deselected in 1.45 seconds. Ruff and whitespace checks passed.
Three previously qualified core files changed: adapter contracts, campaign
artifacts and campaign controller. All 283 other Python files from that wheel
remain unchanged. Prior raw evidence is preserved. A new full base-suite run is
the next verification step, with no new full-suite result claimed here.

No training profile, real basin or independent task was admitted. Failed-worker
training receipt capture, fitting grants, supervised learned execution, automatic
training-cost-to-event validation and suite reservations/reporting remain open.
The transport handles successful completed envelopes only. Inner work without
such an envelope remains unknown. Part 5 remains incomplete.


The original full base-v2 regression is terminal. Exec session 9523 and its pytest
process 35048 exited zero. Pytest reported 2,721 passed and 120 skipped in
2,202.17 seconds. Independently parsed JUnit contains 2,841 cases, zero failures,
zero errors and 120 skips. The JUnit and log hashes match the terminal record.
All 8,007 pinned existing files remained unchanged. An independent post-run file
set comparison found no added or removed source/input files. These pins exclude
historical development/verification archives, unlike the earlier wider v1 pins.
Source-before, exact command/environment, log, JUnit, terminal and independently
verified summary are retained in verification-current-base-v2.

The long three-route accounting case was observed live through its original
pytest PID and operation lock. Its authored test specifies 114 scientific starts;
114 start/finish/supervisor receipt files were observed without interpreting them
as independent outcomes. The run was never restarted. No tested file was edited
while it ran. Read-only follow-up findings under the verification directory bind
the exact tested source hashes and identify fitting grants, per-attempt scratch,
trained selection closure, parent-bound cost integration and failed-training
terminal capture as remaining work.

The regression qualifies default-environment software behavior at this checkpoint.
It does not establish real-basin training, independent task admission, optional
Bayes/interoperability coverage, another platform/host or private scorer admission.
The completion/readiness/handoff pointers now name this result. Those documentation
edits follow the terminal checkpoint and do not change runtime/test bytes. Part 5
remains incomplete.


Trained selected-state version 2 now seals the supplied routing fit, profile,
intent, result, bundle and parent lifecycle. Its offline verifier binds those
bytes to the selected model sources, parameters, fitting prefix, initialization,
execution seed, interface and original training work. The fit must come from a
successful original training result. Parent/worker portable references and
training cost/duration must agree. Companion totals retain the parent's 4 MiB
limit, rejected before closure reads. Model imports, fitting, subprocesses,
sockets and unrelated reads are denied in the actual copied-closure reader test.

The versioned reader is used by suite freeze, confirmation grants and baseline
readers. Archive retains the whole closure along with model sources. A hydrology
family and explicit frozen_trained_inference capability request are required at
the barrier. This is a request, not executor admission. Existing untrained writers
keep v1, which cannot omit a fit for the learned routing profile. Original v1
record shapes and existing scientific workflows remain separate.

A trained frozen-baseline follower retains the verified source cell's fit and
seed through the existing reference journal, even when its logical seed differs.
An authored four-cell/two-seed reference test archived one selected state and
introduced no work during reference dispatch or freeze. This validates metadata
reuse, not training cost matching or a real study. Ordinary trained cells must
match their own assigned seed. Missing capabilities and wrong families/seeds
refuse. Existing private scorer and worker registrations remain unchanged.

Initial focused checks passed 53 tests. A broader sandbox run passed 89 and failed
nine baseline/process tests because ps was denied. With owned-process inspection
allowed, the related run passed 169 tests with two skips. A deliberate rehashed
units test then demonstrated missing offline interface validation. Explicit daily
units, timing, dimensions, dtype and site checks now reject that case. The first
new cached-reference fixture used batch v1.0 and correctly refused reference cases;
its fixture now uses the existing required v1.1 format. All 28 new sealing tests
passed. Final related regression passed 215 tests with two skips in 92.26 seconds,
covering legacy selection, baseline reuse, confirmation/recovery/private readers,
CLI and the learned model/cost paths. Ruff and whitespace checks passed.

The earlier full base-v2 checkpoint retains its preceding parent-transport source
scope. The new module brings core Python files to 204. No fresh full default,
optional-environment or installed-package qualification is claimed for this
increment. No real basin, independent data, learned worker or private scorer was
admitted. Fitting grants, per-attempt supervised training, failed-worker receipts,
automatic cost-to-event binding and the independent matrix remain open. Part 5
remains incomplete.

Five newly introduced long lines were wrapped after the related regression.
AST equality was verified for both affected modules, preserving surrounding
legacy formatting. The final focused check is recorded in the successor source
inventory. No model, receipt, task threshold or frozen historical record was
rewritten.


## Original-event training cost reconstruction

The existing campaign cost reader now joins successful profiled training to the
first event that committed its exact evaluation and lifecycle. The fit, bundle,
profile, intent and work receipt must all belong to that event. It verifies model,
configuration, seed and original work through the frozen selection reader, even
when scientific acceptance rejects the evaluation. No new ledger was introduced.

Frozen inference adds no training start. Origins outside the verified batch and
cross-cell reuse without allocation remain explicit unknown preparation work.
Generic unprofiled artifacts retain unknown work and duration. The existing frozen
baseline reference allocation now includes original training receipts once.

The authored helper performs an actual fit inside the supervised worker and uses
the existing publication path. Its first four tests failed because direct script
execution shadowed registered model sources. A separate declared launcher then
revealed an installed examples package lacking the new profile. The launcher now
explicitly uses the runtime registration's repository root. Source-location checks
remain intact. The corrected initial four tests passed in 10.72 seconds.

Verification: 52 focused tests passed in 24.79 seconds, including saved-worker
recovery without relaunch, rejection cost retention, frozen inference, closure
corruption, later-event borrowing refusal and a cold relocated reader. A broader
campaign/baseline regression passed 34 tests in 119.17 seconds. After removing the
copied source/forcing/label bundle from the cold reader fixture, that test and
documentation contracts passed 20 tests in 4.04 seconds. Ruff and whitespace checks
passed. Logs are preserved in verification-training-campaign-costs-v1.

These are authored software checks. No learned runtime registration, fitting grant,
failed/interrupted worker receipt, real basin, private scorer or independent study
was admitted. External/shared preparation allocation remains incomplete. The full
default checkpoint predates this increment. Part 5 remains incomplete.


## Versioned trusted fitting grants and separate attempt scratch

Campaign schema 1.1 now declares the daily-prefix-supervised-v1 training profile,
allowed trusted adapter IDs and one exposed fitting data contract. Version 1.0
retains its exact fields and digest serialization, rejects a training field and
passes no fitting payload. The profile requires daily NPZ observations on an exact
forcing prefix, matching calendar/timestamp/warmup, and explicit scoring masks.
The worker zeros unscored labels in its supervised payload.

The parent commits the fitting grant with action_reserved. It binds the campaign,
model, configuration, adapter, fitting contract, forcing, seed, attempt and nonce.
The worker checks the original reservation before opening fitting labels. Recovery
checks the same permission without loading labels before retaining successful
training artifacts. Training refuses confirmation, diagnostics and altered forcing.
Trusted attempts now have fresh scratch directories. Generated attempts retain
in their existing isolated scratch paths. Output/job locations remain unchanged.

The authored adapter helper no longer injects fitting arrays or replaces the
lifecycle driver. It uses the real worker grant path. Two actual fits retain
separate intents, scratch, receipts and charges. Forged identities, permissions
and rehashed but uncommitted grants refuse before label reads. No supplied public
learned runtime registration has been added.

The first grant tests exposed an incorrect requirement that physical time
semantics match across variables. Precipitation totals, temperature samples and
mean discharge retain their own declared semantics. The grant instead checks
calendar, daily axis, timestamp and warmup; observation/prediction semantics are
already checked by CampaignSpec. That corrected integration passed 38 tests.
A subsequent test failed because its manually authored second reservation omitted
the existing writer lock. It now uses the lock; no store guard was changed.

Verification: 68 fitting/controller/recovery tests passed in 113.95 seconds;
43 batch/CLI/cost/generated-boundary tests passed in 74.59 seconds; 19 documentation
tests passed in 0.64 seconds. The final fitting-grant read bound was aligned with
the 4 MiB campaign metadata limit, then all 11 fitting and supervised-training
checks passed in 36.03 seconds. One subsequent line wrap was AST-equivalent.
Ruff and whitespace checks passed. Logs and source hashes are preserved in
verification-fitting-grants-v1 and source-inventory-fitting-grants.json.

The prior full default suite predates this increment. No installed or optional
qualification, independent task admission, real source observations, OS privacy,
public learned runtime, frozen-fit confirmation dispatch or failed/interrupted
training capture is claimed. Training and inner-work caps still need complete
suite/task admission. Part 5 remains incomplete.


## Registered learned routing and frozen inference

The fixed hydrology-learned-routing-v1 adapter now reads a declared
routing-runtime.json profile containing immutable site/training metadata and an
optional trained selection. No caller supplies an import path or factory. Training
requires the existing fitting grant. Frozen inference requires a verified v2
selection and all six declared training references, with no fitting permission.
The runtime copies verified JSON artifacts into the fresh attempt scratch before
ordinary lifecycle capture. Frozen campaigns can omit fitting data entirely.

Actual registered worker tests exercise training, saved-worker recovery without
relaunch, selected-state verification, identical frozen outputs and no new fitting
intent/result or training start. External preparation remains unknown in accounting.
The authored helper remains for the separate transport tests, but the registered
worker tests use the normal module command and supplied factory.

The first manual probe used an unresolved temporary path and refused at the
existing symlink guard before registration. The first registered tests then exposed
a declared preparation module that was not loaded. The fixed factory explicitly
loads its known source list; the source-location guard remains unchanged. Frozen
inference next exposed the missing artifacts parent directory in fresh scratch.
The runtime now creates and verifies that owner-private directory before copying.
No adapter or artifact guard was relaxed.

The first corrected routing/artifact/grant regression passed 59 tests in 47.69
seconds. Subsequent engine-provenance hardening requires the entire current engine
for this initial runtime, since historical allowlists predate the fitting/utility
code. Final runtime/controller/recovery checks passed 58 tests in 99.35 seconds.
An explicit old-allowlist omission test and all registered worker/documentation
checks passed 24 tests in 16.53 seconds. One worker condition was wrapped with AST
equality verified. Documentation checks, Ruff and whitespace checks passed.
Logs and source hashes are preserved in verification-routing-runtime-v1 and
source-inventory-routing-runtime.json.

This is local authored source-checkout coverage. No installed package, optional
profile, other platform/host, real basin, private scorer or independent study was
qualified. Trained route selection writers, private frozen inference dispatch,
failed/interrupted training capture, complete resource caps and independent task
admission remain open. The full default checkpoint predates this increment.
Part 5 remains incomplete.


## Terminal evidence for stopped registered training

Stopped supplied routing workers now retain TerminalTrainingEvidence when a
successful model lifecycle is unavailable. The same original evaluation commit
includes the grant, profile, available intent/result and any completed JSON fit.
The public cost reader verifies the original evaluation and first reservation
commits. It cannot borrow missing permission or work from later events.

Actual rollout-budget failures preserve their work counts and duration. A completed
fit remains charged if later inference rejects invalid forcing. An intent without
a result retains one training start and unknown work/duration. An absent intent
retains unknown training work. Invalid raw receipt bytes are retained under an
invalid descriptor and block accounting. No mutable training scratch is read until
the worker's stop is verified. Generic/unverified training retains explicit unknowns.

Recovery of this supplied profile accepts only original stopped supervisor proof
for model failure or timeout, with matching process identity, nonce, finite duration
and no live process-group members. Ordinary failures require matching worker
start/finish records and nonzero exit. An early timeout may stop the wrapper before
its start record exists; its original stopped supervisor proof still establishes
the outer charge, while training work remains unknown. Conflicting proof leaves
the reservation unresolved. Recovery never launches a replacement worker.

The first six terminal tests passed in 19.66 seconds. A related 32-test regression
passed in 80.54 seconds. Early-timeout recovery initially required an unavailable
worker start record. That case was corrected using the existing original stopped
supervisor proof, without inferring training work. An earlier broad run recorded
49 passes and two failures in 141.87 seconds: the early-timeout case and a source
hash refusal caused by editing controller.py while the run was active. The source
provenance guard was preserved. A fresh run kept runtime sources unchanged.

Final stable-source verification passed 68 terminal/controller/recovery/cost tests
in 143.10 seconds. All 11 terminal tests, including later-event borrowing refusal,
passed in 30.99 seconds. The final 19 documentation checks passed in 0.58 seconds.
Ruff and whitespace checks passed. Cold relocated accounting forbids model imports,
optimizer/subprocess/network execution and reads outside copied public evidence,
with source/label bundles and scratch removed. New method formatting was checked
for AST equality. Evidence and hashes are in verification-training-terminal-v1
and source-inventory-training-terminal.json. Core Python files now total 206.

This does not qualify active-fit kill behavior, cancellation recovery, other
training adapters, private scoring, installed packages, another platform/host or
independent data. Trained route integration, full resource caps, shared preparation
allocation and task admission remain open. The prior full default checkpoint
predates this increment. Part 5 remains incomplete.


## Trained state writing and bounded scripted route execution

Scripted prediction and mixed coordinators now write v2 selected states for the
supplied learned routing profile. The writer locates the selected evaluation's
original lifecycle commit, requires the complete training closure in that event,
verifies the fit and archives its bytes before the common freeze barrier. Untrained
states keep v1. This adds no private scorer or learned-alternative admission.

A route must bind the fitting profile in its scientific grant and request the
hydrology frozen-inference capability. The fitting policy enters its numerical
recipe identity only when training is configured, preserving legacy payloads.
CaseBinding records positive training-start and routing-rollout reservations.
Zero-training bindings retain their original serialized fields. Before child
creation, the parent reserves a possible fit for each scientific attempt and the
profile maximum rollouts for each fit. Missing route/profile/global allowances
refuse before science. Actual work remains reconstructed from original receipts.

Actual authored baseline, conventional, single-agent and multi-agent scripted
routes each trained through the normal registered worker and froze exact v2 states.
A failed fit produced no eligible selection while retaining its work. Recovery
after a saved scientific response reused the original fit without another launch.
Frozen baseline followers across different logical seeds shared the original fit,
reserved no additional training and allocated one physical receipt once. A mixed
engineering/hydrology rehearsal used both existing executors and one barrier.
These are supplied-model rehearsals, not a learned-candidate discovery comparison.

Verification: the initial four tests passed in 17.68 seconds. The broader
coordinator/controller/baseline/mixed regression passed 50 tests in 210.59 seconds.
The separate mixed rehearsal passed in 7.16 seconds; three pre-dispatch refusal
tests passed in 2.89 seconds. Formatting of changed functions/imports was checked
for AST equality in three modules. The final trained-execution, sealed-state and
registered-runtime regression passed 43 tests in 53.79 seconds. Final documentation
checks passed 19 tests in 0.83 seconds. Ruff and whitespace checks passed. Evidence
and hashes are in verification-trained-execution-v1 and
source-inventory-trained-execution.json. Core Python files remain 206.

The preceding full default checkpoint retains its earlier scope. No fresh full,
installed, optional or other-platform qualification is claimed. Private scoring,
learned-alternative admission, active-fit kill/cancellation coverage, remaining
resource measurements and independent task admission remain open. Part 5 remains
incomplete.


## Cancellation after a durable fitting intent

The supplied training recovery path now accepts an original cancelled supervisor
proof only when a cancellation intent is pending. It verifies the same owned
process, nonce, stop and job/grant identity as the existing failure/timeout path.
Known stopped training evidence is committed with cancelled_after_recovery; partial
reconciliation retains all available training/stop references. Other unresolved
work stays charged. No fit or replacement worker is launched during reconciliation.
The cost reader recognizes that original cancellation commit.

Actual registered workers were cancelled after writing their fitting intent, with
no training result yet present. Normal and pre-commit-loss recovery retained one
training start, unknown work/duration and one scientific charge. A conflicting
supervisor nonce left the original attempt unresolved with no retained evaluation
or new launch. The test observes the training-stage intent, not optimizer-step
counters, and does not infer how much math completed before termination.

The first authored 4,000-row tests reached cancellation but exceeded the existing
4 MiB campaign-metadata bound during accounting. That bound was preserved; a
2,000-row series passed both normal/recovery cases in 30.75 seconds. The negative
fixture initially reopened an unpinned batch, then incorrectly used a specification
digest rather than the manifest hash including creation time. Both trust guards
refused. The fixture now retains the original creator pin before scientific work.
All three corrected cases passed in 40.95 seconds. The earlier broad run recorded
54 passes and that fixture failure in 184.02 seconds. A new unchanged-runtime run
passed all 23 cancellation/terminal/recovery tests in 99.38 seconds. Final 19
documentation tests passed in 0.59 seconds. Ruff and whitespace checks passed.
Recovery formatting was verified with AST equality. Core Python files remain 206.

The private-scorer trace confirms another implementation gap: the current fixed
scorers accept prediction vectors, hash those vectors into their identities, and
perform no scientific model inference. The new frozen-prediction increment records
a versioned two-stage reservation, protected driver-only grants, fixed replay,
physics checks, explicit nested identity/receipt bindings and original-result
recovery. It is a plan, not a private runtime registration or data admission.
Opening it in the default Markdown viewer failed with LaunchServices -10661; no
installation or global configuration was changed. Deliver its local file link.

Evidence and hashes are in verification-training-cancellation-v1 and
source-inventory-training-cancellation.json. No fresh full default, installed,
optional or other-platform qualification is claimed. Protected inference/scoring,
learned-alternative and independent task admission, optimizer-step/other-kill
profiles and the complete scientific comparison remain open. Part 5 is incomplete.


## Composite confirmation grant and frozen replay metadata

CompositeConfirmationGrant now dispatches from utility-confirmation-grant-v2.
It requires exactly two reserved scientific starts and time covering inference,
model stop grace and the existing fixed vector scorer lifecycle. Training/host
calls remain forbidden. Legacy grants retain their fields, canonical bytes,
one-start rule and original error wording.

FrozenRoutingInference binds the selected state, runtime profile, known-exposure
NPZ forcing metadata, original fitting seed and bounded time/output. Metadata
validation checks the driver interface, historical daily prefix, warmup, variable
semantics, site and original training profile. It permits a chronological extension
and new scoring mask. It opens no driver arrays or labels and imports no model.
The task must request the protected routing capability; that request is not runtime
qualification or data admission.

Current vector-only services refuse composite execution and recovery before
reservation/access. The offline score validator refuses a legacy score receipt for
a composite attempt. An authored ledger test retained two charged reservations
when that unsupported receipt was rejected. No composite score was recorded.
A cold subprocess validated the grant with every NPZ read, model import, optimizer,
subprocess, socket and out-of-scope file access denied.

The initial fixture omitted ArtifactRef.metadata and recorded seven failures plus
one pass in 20.54 seconds. Supplying its required empty metadata fixed that setup.
Resource variants now share one prepared state rather than performing unnecessary
repeated fits. The grant/scoring/recovery/cost regression passed 59 tests in 26.77
seconds. All six new grant tests passed in 15.62 seconds. Changed grant formatting
was AST-equivalent. Final composite/CLI/vector compatibility passed 35 tests in
19.57 seconds, and 19 documentation tests passed in 0.60 seconds. Ruff and whitespace
checks passed. Evidence is in verification-composite-grants-v1 and source hashes
in source-inventory-composite-grants.json. Core Python files now total 207.

This implements the contract/preflight portion of the frozen-prediction increment.
The supervised composite executor, numerical driver-prefix verification, physical
output checks, nested identity/receipt chain and protected runtime remain open.
No private scorer registration, data admission, image acquisition, installed or
other-platform qualification or independent run is claimed. The prior full default
checkpoint retains its earlier scope. Part 5 remains incomplete.


## Candidate frozen routing inference execution

The fixed supplied inference worker now executes selected v2 routing state on
explicitly granted authored drivers. Original composite reservation/access and
source/lock pins are checked before driver access. One atomic suite claim prevents
reuse of the same grant in another workspace. Work and driver scopes cannot
contain, or be contained by, public source/suite scopes. No driver-root or label-root
path is passed to the worker. This does not establish an OS privacy boundary.

The worker checks the numerical fitting prefix, preserves the original fit/seed,
retains all states/fluxes, applies finite/nonnegative/capacity/balance checks and
emits a bound prediction vector only on scientific success. Historical outputs
match the original authored fit exactly. No fitting intent/result is created.
Model, infrastructure and timeout failures retain distinct statuses and no vector.
Original stopped-process/result evidence supports recovery after both driver copies
are removed. Corrupt jobs, results or stop proof refuse. Cancellation permits
observation of original completion, never a fresh inference.

The first test run recorded five failures and one pass because worker attempt/control
directories were missing. Adding the directories yielded six passing tests. Later
checks covered one global grant claim, loss after saved completion and cancellation
recovery. The final scope/regression command passed 41 tests in 53.28 seconds.
Nineteen documentation tests passed in 0.58 seconds. Ruff and whitespace checks
passed. Evidence is in verification-frozen-inference-v1; hashes are in
source-inventory-frozen-inference.json. Core Python files now total 209.

This implements only the candidate inference stage of the protected prediction
increment. Composite scoring orchestration, nested receipts, private runtime
qualification, memory/CPU limits, preparation deadlines and pre-launch interruption
recovery remain open. Vector-only services still refuse composite execution and
legacy receipts cannot complete composite attempts. No independent data, task
admission, installed/optional/other-platform qualification or full-suite rerun is
claimed. Part 5 remains incomplete.


## Candidate composite inference and vector scoring chain

An explicit candidate CompositeConfirmationService now connects frozen routing
inference to the existing fixed vector scorer. Default vector-only services still
refuse composite execution. The parent registration pins the inference contract,
executor, vector source/runtime, label hash, partition and outcome. Its identity
stays fixed. After inference, an immutable public transition binds the archived
closure to the prediction-dependent inner grant before label access. The inner
one-start grant allocates part of the original two-start reservation; it creates
no extra suite reservation. Failed inference returns its original nonnumeric
status without entering scoring.

Public receipts bind both stages. Readers verify the original job, durable intent,
suite claim, nonce, process/stop/result claims, physical checks, outputs/vector and
nested scorer identity. A cold subprocess reconstructed a copied public suite with
model imports, array loads, optimizer/process/network calls and out-of-scope reads
denied. Both driver scopes, original sources and private scoring scope had been
removed. These are verified trusted producer records, not an independent OS stop
or privacy attestation. The scorer test fixture explicitly supplies authored
execution metadata; it does not qualify a container runtime.

Saved score recovery launches neither stage and reads no labels. Missing inner
completion stays charged and unresolved. Cancellation between stages blocks new
scoring. Accounting retains known inference starts/duration before outer score
publication. Pending scorer starts remain unknown. Complete inner metadata reports
its separate starts/duration. Overlapping callback/worker durations must not be
summed as exclusive cost.

The first actual-chain test passed in 6.42 seconds. An initial regression command
named a nonexistent recovery test file and ran no tests. The corrected regression
passed 81 tests in 102.75 seconds. After cancellation/partial-accounting additions,
81 tests passed and one cancellation fixture failed because its authored journal
event omitted required identity fields. Correcting only that fixture yielded all
eight composite cases passing in 50.52 seconds. Final documentation checks passed
19 tests; Ruff and whitespace checks passed. Logs are preserved in
verification-composite-scoring-v1 and source hashes in
source-inventory-composite-scoring.json. Core Python files now total 211.

A fresh full default checkpoint is being prepared in verification-current-base-v3.
Its focused results above are not a full-suite result. Protected runtime privacy,
memory/CPU bounds, preparation deadlines, pre-launch interruption recovery,
installed/optional/other-platform qualification and independent task admission
remain open. No new images, providers, remote hosts, independent labels or final
comparison runs were used. Part 5 remains incomplete.


## Full default checkpoint and extracted composite wheel reader

The original full-suite process exited zero: 2,812 passed and 120 skipped in
2,495.24 seconds. JUnit records 2,932 cases, zero failures and zero errors. All
480 pinned files matched at completion, with no added/removed core or test Python
files. Pins cover core/test Python, direct utility example Python, current increment
docs and configuration. They do not establish an exhaustive input/fixture/archive
snapshot. Verification-current-base-v3 preserves the command, original session,
log, JUnit, source pins and verified summary. It covers the current 211-core-file
implementation through composite orchestration. Earlier full checkpoints remain
unchanged and retain their own broader pin sets.

While that source snapshot remained fixed, a wheel was built in a temporary copy
from 340 pinned inputs. All 211 core Python files matched the wheel exactly.
The optional build frontend was unavailable; the existing setuptools backend built
the wheel without installing dependencies. Extracted imports and CLI help passed
outside the checkout with optional/model imports prohibited. One additional bounded
authored composite fixture supplied public evidence for cold-reader validation.

Cold replay and cost reconstruction used only the copied public suite. The actual
utility report and verify commands passed with model imports, array loads,
optimizer/process/network calls, private/original scope reads and public writes
denied. All 329 public file hashes remained unchanged. Complete cost evidence
stays false. The fixture uses authored scorer execution metadata and does not
qualify a container or private inference boundary.

The wheel and public fixture were transported through saved archives into another
fresh temporary directory. Safe tar extraction omitted the directory modes, so the
first attempt correctly refused the nonprivate store root before verification.
Restoring 0700 directories and 0600 files in that new authored fixture allowed the
same guarded replay/cost/report/verify check to pass. Raw failure and success logs,
exact reader script bytes, wheel, public fixture and hashes are preserved in
verification-composite-wheel-v1. No source guard was weakened.

This is extracted-wheel reader evidence with inherited base dependencies, not an
installed preparation/run/resume qualification. Skipped/optional environments,
Linux, a second host, private runtime memory/CPU/privacy, preparation deadlines,
independent task admission and the final scientific matrix remain open. No new
images, installation, live providers, remote hosts or independent inputs were used.
Part 5 remains incomplete.


## Extracted learned baseline workflow and saved-state reader

The matching 211-core-file wheel now supports one actual authored learned baseline
through seven CLI operations outside the checkout. Input construction uses pinned
test helpers with explicit copied source metadata. The scientific process uses the
fixed supplied wheel registration. Preparation correctly reports missing task
admission/incomplete real task families and starts_authorized false. Only the
separately explicit exposed scripted-development command starts science.

The first harness's launch audit refused because its current directory was above
the extracted package. That original suite retains its charged attempt and launch
intent without a completed worker record. No retry or overwrite was attempted.
The complete public snapshot, script and logs are preserved. A fresh fixture with
the package directory as cwd completed validate, prepare, run, resume, freeze,
report and verify. One scientific worker performed one authored fit. It produced
v2 selected state; resume launched no worker. Accounting retains one training
start, complete cost evidence false and utility not attempted.

A copied public suite then reconstructed v2 state and original training cost, and
passed the report/verify CLI under guards denying model/optional imports, array
loads, optimization, processes, network, original/private scope reads and public
writes. All 311 public file hashes stayed unchanged. These are trusted original
producer records, not independent OS attestation. Artifacts are in
verification-learned-wheel-workflow-v1. No core/test/configuration bytes changed
from the full default checkpoint during these checks.

This is one extracted-wheel authored baseline with inherited base dependencies.
It does not qualify package installation, the full four-family workflow, protected
scoring/runtime, other platforms/hosts, independent task admission or scientific
utility. No installation, new image, provider, remote work or independent inputs
were used. Part 5 remains incomplete.


## Offline inference environment input package

The administrative inference_environment helper now prepares an immutable inputs-only
package for the existing default Linux x86-64 dependency selection. It follows
locked dependency names from the fixed core roots, excluding unrelated development
packages. It does not perform a new solve or independently recheck version
constraints. Archive URLs, SHA-256, compressed sizes, licenses, dependency strings
and locked virtual platform assumptions remain explicit. The pure wheel's original
filename, project/Python metadata and all 300 Python-source hashes are retained.
Unsafe ZIP members, changed bytes, duplicate/unknown selections, unsupported local
projects and wrong architecture refuse before publication.

The first tests found a missing artifact directory: three failures and 14 passes.
Creating that directory and checking output ancestors fixed preparation. The final
25 focused tests passed in 1.05 seconds. They cover offline/no-extraction behavior,
wrong inputs, publication loss, symlink parents, no overwrite and cold reconstruction
from an explicit trusted digest. The actual package contains 49 archive pins and
265,399,717 compressed bytes. No archive was fetched or installed. Uncompressed
size remains unknown. Exact producer source bytes and raw test results are retained
in verification-inference-environment-v1.

A fresh verification harness initially could not find examples.utility from its
nested script directory. Giving that reader an explicit repository import root
fixed only the harness. With model/optional imports, array loads, network,
subprocesses and ZIP extraction denied, the actual saved package verified against
its reviewed digest. It still reports starts_authorized false and runtime_qualified
false. No scientific worker or environment assembly was invoked.

The input review proposes 1 GiB memory, one CPU, 16 pids, a 128 MiB workspace, no
network, read-only root and a maximum 60-second model timeout. These are not measured
or admitted controls. The fixed scorer profile is ARM64, while this locked package
targets Linux x86-64. Base-image identity/compatibility and assembly remain open.
V1 inference also binds its identity to the host interpreter and workspace, so a
versioned guest contract is needed. No scorer allowlist, grant or old job was
changed. These example/test additions postdate the full default checkpoint. Part 5
remains incomplete; private runtime and independent task/scientific admission stay
open. No new images, installations, providers, remote jobs or independent inputs
were used.

Final review added strict schema-version typing and exact JSON type comparison for
the proposed resource review. A boolean CPU count cannot masquerade as integer one.
The final combined check passed 46 tests (27 preparer cases and 19 documentation
cases) in 0.99 seconds. The stricter cold reader still verifies the original pinned
package. Its exact producer source remains preserved separately from the newer
reader/preparer source. No prepared input, policy or authority flag was rewritten.


## Candidate guest inference identity and relocated transport

FrozenGuestInferenceJob now dispatches through utility-frozen-inference-job-v2.
V1 retains its exact serialized fields, host Python identity and path-bound scope.
The new unqualified profile pins environment/lock/wheel/source, immutable image ID,
Linux x86-64 CPython version/build and proposed limit identities. Its scope binds
grant/executor/nonce without host directory names. The job, intent and claim hashes
must agree before any model or driver access. Source inventory identity is checked.

The fixed worker checks observed runtime, pinned environment and installed wheel
code before selected-state/model/driver reads. Authored observations exercise
relocation and mismatch refusal; those tests stop before model state access and
claim no actual Linux/guest execution. Missing/extra/changed sources, interpreter,
claim, intent, source/image/lock/limit bindings, promotion and old wheel metadata
refuse. A fresh cold process decoded the job with models, runtime probes, file
reads, arrays, subprocesses and sockets denied. V1 supervisor archives reject v2
jobs instead of accepting their proof as a guest/container execution receipt.

The first related regression passed 30 tests in 59.08 seconds. The broadened
execution/input/composite/cost regression passed 83 tests in 114.03 seconds. The
later cold/input check passed 47 tests in 6.51 seconds. No code source changed during
those runs. V1 actual model outputs, physical checks and saved-result recovery
remain covered; no model ran under a simulated guest qualification claim.

A fresh wheel built in copied inputs contains 212 core Python files with exact
byte parity; 342 build inputs are pinned. Offline preparation/reconstruction
produced successor input package 5eee3a23d3574a7f3c160f9ebfbedd9f1670f7db4e7b79f1edeef1168aeeb60b,
with 302 wheel source hashes and the same 49 archive pins/265,399,717 compressed
bytes. The original package remains unchanged and verifies. Its old wheel lacks
v2 guest sources, so it is not relabeled as the new runtime. No archive was acquired,
installed or extracted; no image or guest scientific execution occurred.

The new package review distinguishes candidate guest source presence from the
still-unqualified launcher/receipt chain. Original OCI creation/start/stop proof,
guest execution/archive receipts, actual image/environment assembly and enforced
privacy/resource controls remain open. The worker cannot attest its own OCI image
ID. No default executor, confirmation service, CLI or private runtime registration
activates this profile. These changes postdate the full default checkpoint. Part 5
is incomplete; independent tasks and the full scientific comparison stay open.


## Candidate guest execution archive and cold projection reader

Guest receipt records now link the v2 job/environment and original suite claim to
launch/runtime/image/policy, start, stopped state, cleanup and bounded result
capture. The policy fixes command, environment/thread controls, resource proposals,
user, root/workspace permissions, no network/mounts/devices/capabilities, no stdin
and no host logging. Typed records reject changed or unbounded policy projections.
No daemon or OS enforcement is supplied by that schema.

The reader requires explicit source, lock, executor and runtime pins. It verifies
all original links and the saved environment metadata, not only its digest.
Successful captures retain fixed physical checks, full output hashes and a bound
finite vector. Scientific/model failures keep their statuses. Deadline expiry,
cancellation, OOM/dead/failed exits and missing/malformed/limited captures cannot
publish scoring vectors. Unknown lifecycle time stays null rather than becoming
zero or a new clock sample. Contradictory/missing proof remains unverified.

All OCI/API capture records in this increment are authored producer projections.
They are not actual daemon observations. Their hashes preserve claims, not an
independent attestation of image identity or OS control. Guest relocation/cold tests
read public bytes only, with model imports, runtime probes, arrays, subprocesses,
sockets and unrelated file access denied. No actual image or guest model ran.

The first 35 reader cases passed in 6.56 seconds. Lint then required removing an
unused import and giving the imported pytest fixture an explicit alias. The broader
compatibility regression passed 133 tests in 124.32 seconds. Adding explicit saved
environment reconstruction/refusal led to 72 final guest/archive tests passing in
13.98 seconds. Source was held unchanged during each run. Authored public records,
reader inputs, output and raw logs are under verification-guest-receipts-v1.

The existing local supervisor archive still refuses guest jobs. The new archive
has no default service/launcher integration. An actual qualified owner must validate
raw API observations and enforce the original selection/access barrier, image,
privacy/resource policy and no-retry rules before publishing these projections.
Image/environment assembly, actual lifecycle qualification, independent tasks and
full scientific comparison remain open. Core Python files now total 213; the last
full default checkpoint predates this reader. Part 5 remains incomplete.

## Candidate owner checks for saved guest OCI observations

`utility/guest_observations.py` supplies the fixed candidate create request and
checks saved image, creation, start, stop and cleanup documents before projecting
existing guest receipts. The command, environment, owner nonce, image, mounts,
network, namespace, capabilities, resource settings and restart history must match.
Malformed labels, contradictory lifecycle states, missing timestamps, terminal
state in a running snapshot and foreign cleanup refuse. Canonical raw-document
hashes enter the receipt chain. Unknown elapsed time remains null.

The authored positive captures reach the cold archive reader with subprocesses,
sockets and new monotonic clock samples denied during projection/verification.
Timeout, cancellation, OOM and dead-container evidence cannot publish scoring
vectors. These tests do not execute a guest or establish actual OS isolation.

The initial sandboxed run stopped in the shared development-baseline fixture with
scientific work uncertain: 67 setup errors, before new observation checks ran.
That charged attempt remains unreconciled and was not retried. Fresh fixtures with
owned-process supervision passed 72 cases in 9.44 seconds. The broader guest,
environment, v1 local inference, composite and confirmation-cost regression passed
208 cases in 125.25 seconds. Code stayed unchanged during both successful runs.
The shared fixture executes one ordinary authored development baseline; the OCI
captures are authored. Evidence, source snapshots and public captures are under
`examples/utility/verification-guest-observations-v1/`.

This adds one core module, bringing the current count to 214. The full default
checkpoint predates it. No default launcher/service or existing scorer allowlist
changes. Next runtime work is original owner acquisition and durable lifecycle
handling, followed by actual image/resource/privacy qualification. Independent
partitions, task-owner gains/tolerances and the scientific matrix remain open.
Part 5 remains incomplete.

An explicit line-length check required splitting one tmpfs string literal without
changing its value. The final guest observation/archive check passed 124 cases in
13.87 seconds. Nineteen documentation cases passed in 0.67 seconds. Relocated
public-capture replay also passed with subprocesses, sockets and clock sampling
denied. Its initial symlink-path refusal and corrected canonical-root harness are
preserved. No artifact path boundary or scientific gate changed.

## Candidate guest owner journal

`GuestOwnerJournal` now binds an owner directory to the original suite inference
claim and fixed launch identity. Its create-only lease precedes initialization.
Immutable events record create intent, original unstarted creation, start intent,
original start/stop, cleanup intent and original cleanup. Shared OCI validation
now exposes creation/start and lifecycle helpers, preserving the completed
projection contract. The journal requires the existing writer lock and rejects
out-of-order or repeated transitions, changed claims/leases, foreign observations,
corrupt/gapped events and oversized evidence. Mutable caller data cannot change a
committed record. Original suite reservations remain charged.

Before/after fault injection covers all seven commits. A committed create/start
intent without its observation remains uncertain. Loss after lease publication
does not authorize a second owner directory. Reopening reads saved evidence only.
Completed records feed the existing guest archive reader; unknown original time
remains null. Relocated copies support replay but cannot write, even with access
to the original suite. Cold replay in a fresh process denied model imports, array
interpretation, process launches, sockets, new clocks and unrelated/writable reads.

The first focused owner/observation run passed 110 cases in 25.14 seconds. Two
additional archive-handoff/cold-process cases were included in the broader guest,
local inference, composite and confirmation-cost regression: 221 passed in 145.63
seconds. Sources stayed unchanged during those runs. Authored journal/capture
fixtures and source snapshots are preserved under verification-guest-owner-v1.
A separate relocated archive replay also passed. No actual container ran.

This is the durable evidence component, not a launcher or staging implementation.
A future owner must hold its lock across intent and the single external dispatch.
Actual daemon acquisition/dispatch, input transfer, watchdog and early-abort cleanup,
interrupted-initialization reconciliation and runtime qualification remain open.
No default executor/service or scorer allowlist changes. There are now 215 core
Python files, beyond the last full default checkpoint. Independent partitions,
owner-approved gains/tolerances and the scientific matrix remain open. Part 5 is
incomplete.

## Candidate frozen guest input package and original start binding

The guest input preparer now builds a fixed bounded transfer package after checking
the original suite/owner locks, lease, frozen selection, composite reservation and
access receipt. Public source/model/environment and wheel-code identity checks
precede driver access. A create-only input intent precedes the driver read. Loss
retains that intent and refuses a new preparation attempt. Recovery reads only a
completed manifest and saved archive, without original driver/source scopes.

Membership is derived from the frozen job/selection: worker job/intent/claim,
environment, lock, selected state/runtime, six fit/provenance metadata references,
inventoried core/model Python sources and one normalized driver artifact. No
fitting/comparison arrays, labels or undeclared contents are copied. Canonical tar
members have fixed uid/gid/modes. Limits are 1024 files, 4 MiB per file, 32 MiB
payload and 40 MiB transfer bytes. The cold reader verifies exact membership,
content, original bindings and wheel/source agreement. Updated tar/manifest hashes
cannot admit links, extra fitting payloads, duplicates, extensions or trailing data.

Owner start intents now pin completed package digests when preparation has begun.
An incomplete package blocks the start commit. Journal replay verifies the original
package; changed/missing inputs cannot support completed lifecycle evidence.
The optional field is omitted from legacy records. The previously archived owner
fixture still replays with its original event hashes. A future actual dispatcher
must require the package binding, not accept a legacy evidence-only start record.

The first package check passed 15 cases in 10.03 seconds. Archive/path/custody checks
then passed 33 cases in 16.04 seconds. The broader guest/environment/v1 inference/
composite/cost regression, including wheel-source and fresh cold-reader checks,
passed 284 tests in 159.43 seconds. After package/start integration, the final
package/owner/observation/archive regression passed 203 tests in 51.71 seconds.
Code stayed unchanged during each run. The common authored fixture executes an
ordinary development baseline; no guest, image or independent data executes.
Cold checks deny model imports, arrays, process launches, sockets, new clocks and
unrelated/writable reads. Evidence is under verification-guest-inputs-v1.

Core source count is now 216, beyond the last full default checkpoint. Actual
transfer/dispatch, watchdog and early-abort handling, initialization reconciliation
and OS/resource/privacy qualification remain open. No default executor, service or
scorer allowlist changes. Independent partitions, owner-approved gains/tolerances
and the scientific matrix remain open. Part 5 remains incomplete.

## Candidate tmpfs stdio bootstrap and successor offline inputs

Investigation found that the proposed transport cannot use daemon archive copies
for the worker tmpfs. The design correction and primary sources are appended to
the frozen-prediction increment. The new versioned stdin policy retains the original
resource/isolation limits and fixed commands. Original direct-worker records remain
readable. The bootstrap validates the complete bounded request before file writes,
checks observed interpreter/installed wheel before model access, invokes the fixed
worker once and streams canonical bounded outputs before the tmpfs disappears.
No uploaded source executes. Headers, membership, identities, file paths and byte
caps are checked. Fragmented reads and short writes preserve every byte. Python
diagnostics and raw exception text do not enter the framed result.

Saved captures reconstruct without original streams, data scopes, models, runtime
probes, arrays or new clocks. Noncanonical original worker bytes refuse instead of
being relabeled. Failed/truncated/foreign output never publishes a completed
capture. A completed capture cannot be replaced by a fresh stream. The stdio result
feeds the existing guest archive reader with original worker duration retained and
unknown container time still null. Lifecycle observations remain authored.

The first focused run exposed invalid authored completion durations and a negative
host test that did not handle the Linux-only identity constructor's expected macOS
refusal: 10 failures, 15 passes. The corrected check passed 25 tests in 17.34 seconds.
The broader related regression passed 316 tests in 178.83 seconds. A final 30-case
bootstrap check passed in 25.92 seconds, including fresh cold reading with model
imports, arrays, processes, sockets, clocks and unrelated/writable reads denied.
Positive orchestration invokes an authored worker stub under authored validation
hooks, not a real model under simulated guest qualification. The real host refuses
before extraction or worker access. Source was held unchanged during each run.

A preserved capsule replays after relocation and from a freshly extracted wheel.
The latter uses inherited host dependencies and is not package installation or
Linux qualification. The offline wheel includes 217 core Python files with exact
parity to 348 copied build inputs. Successor environment package v3 has identity
9402879f689a26da4dcb07573e3f007efbc7cd4fa3451f6e0c41ae40667f0966,
307 wheel Python sources and unchanged 49 archive pins/265,399,717 compressed bytes.
Both older packages still verify. The first admin build harness import-path failure
occurred before building; its script/log and the corrected explicit-source-root
harness are preserved. No dependency archive was fetched, extracted or installed.

Evidence is under verification-guest-bootstrap-v1. Actual attach/start, Docker
multiplexing, deadline/watchdog/owner-loss cleanup, early-abort handling and
image/OS/resource/privacy qualification remain open. No image or guest ran, and no
default service or scorer allowlist changed. The full checkpoint predates this
217-core-file state. Independent tasks, useful gains/tolerances and the scientific
matrix remain open. Part 5 is incomplete.

## Candidate bounded Unix attach transport

The transport now opens one explicit Unix stream endpoint, sends the fixed attach
request, requires HTTP 101 and validates bounded non-TTY Docker frames. It preserves
prefetched/fragmented stdout and discards bounded stderr. Only one request matching
expected job/launch/package identities may be written, followed by stdin half-close.
Failed or partial writes consume that connection's attempt. Nothing reconnects,
starts or retries a container. Original monotonic deadlines cover every stage and
EOF, without renewal on progress. Cancellation is polled during idle I/O. Short
connection timeouts remain unverified, not invented original-deadline expiry.
Moby's current stdin source supports binary transfer with the chosen non-TTY/
StdinOnce configuration; design sources are recorded with the increment/evidence.

The first focused check passed 48 tests in 9.52 seconds. The broader related
regression passed 368 tests in 208.37 seconds. Final protocol/native checks passed
53 tests in 9.28 seconds, including trailing daemon error after a complete result,
known multiplexed media type and portable short POSIX temporary socket paths.
Core transport bytes stayed unchanged. Real owned Unix sockets exercised exact
input, observed stdin EOF, multiplexed stdout into the existing capturer, idle
deadlines and backpressure after actual writes. Timers/cancellation close local
FDs but do not attest container termination. Positive peers/results are authored;
no daemon, container or real guest model ran. The baseline fixture is ordinary
authored development execution. Cold relocated capture replay also passed with
models, attach, processes, sockets and new clocks denied.

Evidence, source snapshots, native proof and saved capsule are under
verification-guest-attach-v1. Current core source count is 218. Prepared environment
v3 and the full default checkpoint retain their earlier source scopes. Actual
identity preflight, durable attach/start integration, watchdog/stop/cleanup and
pinned-daemon/image/OS/resource/privacy qualification remain open. No default
executor/service or scorer allowlist changed. Independent tasks, useful gains/
tolerances and the scientific matrix remain open. Part 5 is incomplete.

## Candidate daemon preflight, original creation and observe-only reconciliation

The API profile now pins endpoint scope, explicit version, canonical server data,
critical implementation files, all core Python sources and owner interpreter.
Bounded Unix HTTP handles content length and chunked JSON without deadline renewal
on header/body progress. Fixed operations read version/image/container data or
create one unstarted container. No API operation retries or starts a container.

Creation requires original suite/owner writers, immutable selection, original
charged access, matching runtime identity and prepared inputs. Server/image and
name-absence preflight is linked into the create-intent event before CREATE.
The original returned response is captured before ID/warning interpretation and
bound to successful created events. Known warnings block reconciliation without
new API requests; a lost response remains explicitly unknown. Missing preflight,
corrupt response, foreign/running container or changed identity cannot be replaced
by fresh metadata. Reconciliation observes the original matching unstarted name
without issuing CREATE. Original suite reservations remain unchanged.

Moby source inspection showed map-based tmpfs settings separate from ordinary
mount points. The reader now accepts an empty Mounts list with the exact bounded
HostConfig.Tmpfs map, while retaining the old authored single-tmpfs projection.
Specified null empty collections normalize to absent binds/devices/capabilities/
ports. All other security/resource checks remain; a host bind still refuses.
Sources and scope are recorded in verification-guest-creation-v1.

The first related focused check passed 158 cases in 40.82 seconds. Review identified
that CREATE warnings needed durable capture before interpretation. Adding that
path led to 74 creation/owner cases passing in 47.07 seconds. The broader related
regression passed 407 cases in 239.59 seconds. Final creation/cancellation/cold-reader
checks passed 39 cases in 34.78 seconds; a native CREATE serialization case passed
in 5.38 seconds. Source stayed unchanged during each run. Real Unix peers tested
fixed requests and content-length/chunked responses only, not a real daemon.
Positive API/creation outcomes are authored; no guest model or container runs.
Fresh cold replay denies models, arrays, processes, sockets, clocks and unrelated/
writable reads. Original creation and prior attach capsules also replay unchanged.

Current core source count is 219. Full default and prepared environment v3 retain
their earlier scopes. Actual start/attach integration, independent watchdog/stop/
cleanup and daemon/image/OS/resource/privacy qualification remain open. No default
service or scorer allowlist changes. Independent tasks, owner-approved useful
gains/tolerances and the scientific matrix remain open. Part 5 is incomplete.

## Candidate independent owner-loss and deadline watchdog

A separate watchdog process now arms from original reviewed unstarted creation,
with an anonymous owner pipe, fixed deadline and child readiness receipt. It can
only inspect and clean up the original CID/image/labels. Durable intents precede
one kill/removal sequence. Resource drift cannot disable owned cleanup. Lost API
responses require observation, foreign ownership refuses mutation and unverified
cleanup remains explicit. Saved terminal outcomes cannot dispatch again. Parent
disarm requires original completed journal cleanup and fresh daemon absence.

The related regression passed 340 tests in 160.83 seconds. The first 14 watchdog
cases include actual local child readiness, deadline, cancellation, owner pipe
closure and invalid disarm on authored Unix peers. A separate owner is actually
killed with SIGKILL. Its detached watchdog survives and observes EOF, records the
peer's stop/absence and terminates. Relocated original evidence replays with
process/socket creation and new monotonic clocks denied. Documentation checks
passed 19 cases. Logs, source snapshots and authored evidence are retained under
verification-guest-watchdog-v1. The expanded final watchdog result is recorded in
that directory's final-watchdog.log/XML.

There are now 220 core Python files. No real daemon, container, image or guest model
ran in these checks. The full default checkpoint and prepared environment v3 keep
their older source scopes. Start/attach integration, reconciliation to the parent
journal, initialization recovery and actual runtime/resource/privacy qualification
remain open. Independent task partitions, useful gains/tolerances and scientific
comparison remain open. Part 5 is incomplete.

## Candidate single-start dispatch and saved-only parent reconciliation

The controller now arms the original watchdog, records attach intent/completion and
binds that evidence into the original start intent. START is sent once. Its returned
status/body projection is captured before interpretation, then frozen stdin is sent
once and half-closed. Complete output capture precedes stop observation and cleanup.
The surviving owner records measured elapsed time. Reconciliation cannot invent
missing original time, start intent or stop evidence, and never issues a new daemon,
attach, input or model request. Original suite charges remain unchanged.

Cancellation callbacks and newly appended suite cancellation events are observed
during transfer. A cancellation after stop observation prevents a complete transport
verdict without rewriting that stop. Manifest-last completion verifies original
capture, journal and watchdog evidence after relocation. An actual owned dispatch
process was killed with SIGKILL after sending input. Its independent watchdog
survived, stopped/removed the authored peer container and terminated. No real
container or guest model ran. Default services and scorer allowlists are unchanged.

A 26-case interruption check passed in 200.15 seconds. Final duration/cancellation/
owner-loss additions passed three cases in 26.70 seconds. The broader guest run
passed 370 cases and failed one in 346.02 seconds: EOF at deadline could be classified
as owner loss. A deterministic reproducer confirmed the race. Giving an expired
original deadline precedence after pipe read fixed it. All 46 final dispatch/watchdog
cases passed in 229.39 seconds. The 19 documentation checks passed. Failed/interrupted
logs, original and successor source snapshots, and final pins remain retained under
verification-guest-dispatch-v1. Full default tests were not rerun for this increment.

Both complete and actual-owner-loss archives replay with model imports, process/
socket creation, array loading, new clocks, writes and unrelated reads denied.
Original creation and watchdog archives also replay unchanged. There are now 221
core Python files. Prepared environment v3 and the full default checkpoint keep
their earlier source scopes. Actual runtime/image/resource/privacy qualification,
inference archive and confirmation-service integration, initialization recovery,
independent task admission and useful gains/tolerances, and scientific comparison
remain open. Part 5 is incomplete.

## Dispatch-bound public guest archive

The v2 archive now binds original dispatch completion, journal chain, START response
and absence to the job, claim, environment, lifecycle projections and capture. Both
writers and the original owner scope are required for publication. The publisher
implementation has an explicit pin. The public grant pointer is create-only and
manifest-last. Interrupted export reuses saved evidence without new science or
host starts. Private plans/paths, driver capsules and raw OCI observations remain
private commitments. Existing V1 records retain their fields and hashes.

Cancellation after stop observation cannot turn a captured result into scoring
outputs. Worker science/model/infrastructure failures remain distinct. Lost START
response and truncated output remain failures, and original deadline expiry stays
timeout. Missing start/stop proof remains charged without an exported started
receipt. Default confirmation execution/recovery and legacy local archives refuse
the candidate. No service registration or scorer allowlist changed.

After correcting the original watchdog artifact scope, the focused export check
passed nine cases. The related guest/archive/local inference/composite regression
passed 93 cases in 186.09 seconds. The final archive check passed 31 cases in 141.94
seconds, including six publication fault points, public-proof corruption, semantic
failures, timeout and closed recovery. A minimal 17-file public bundle passes fresh
cold verification with model imports, process/socket creation, array loading, clocks,
writes, private recovery, publisher source probes and unrelated reads denied.
Original dispatch replay remains unchanged. Evidence and final source pins are
under verification-guest-archive-v2. These are authored peer/result fixtures, not
actual guest execution or OS/privacy qualification. Full default tests were not rerun.

Current core count is 222. The older full checkpoint and prepared environment v3
keep their original scopes. The guest executor facade, composite-service integration,
initialization recovery, installed/platform/host and runtime qualification, independent
task partitions/margins and scientific comparison remain open. Part 5 is incomplete.

## Candidate guest executor facade and initialization reconciliation

The facade now joins original charged access, frozen initialization, input packaging,
creation, single-start dispatch and v2 public archive. Registration binds model/guest,
source/lock, environment, runtime, publisher, fixed policy and facade implementation.
The original deadline covers preparation checks and all execution stages. Cancellation
or expiry after input intent prevents a reserved-driver read. Package completion
cannot reset the deadline before daemon creation. Another workspace cannot replace
an original intended attempt.

Matching partial initialization can finish metadata without source/driver access,
new clocks, daemon calls or science. Unknown files/events, symlinks, changed records
or missing completed owner data refuse repair. Recovery consumes original dispatch
observations and can publish a supported archive without source/driver scopes or
new physical work. The fresh recovery-only constructor holds no source, driver or
API scope and refuses execution. A guarded relocated public fixture retains the
original result with original work/drivers absent.

The first eight facade checks passed. The facade/input/legacy inference regression
passed 64 cases in 136.80 seconds. The later facade/archive check passed 48 cases and
failed its fresh-process harness because the strict read barrier preceded a lazy
public reader import. Diagnostic replay identified controller bytecode initialization.
Metadata reader initialization under model/execution/clock guards now precedes the
strict file-read barrier. All 18 final facade checks passed in 66.12 seconds. The
relocated public replay passed with model imports, execution, arrays, clocks, publisher
source probes, writes and unrelated/private reads denied during verification.
Source snapshots and logs are under verification-guest-executor-v1. Full default
tests were not rerun.

There are now 223 core files. All guest peers/results remain authored. No actual
container, image or guest model ran. Older full-checkpoint and prepared environment
v3 scopes remain unchanged. Composite-service integration, early unstarted-resource
cleanup, strict filesystem timing and actual runtime/privacy, installed/platform/
host qualification remain open. Independent task partitions, useful gains/tolerances
and scientific comparison remain open. Part 5 is incomplete.

## Candidate guest composite service and stage-specific container accounting

The v2 guest registration/service now binds facade registration, inference runtime,
publisher and policy to the existing vector scorer. Vector/local services and the
local scorer refuse the guest path before access. The original parent grant reserves
both scientific starts. Completed original inference/initialization precedes a
create-only handoff to the prediction-specific subordinate grant. Failed inference
cannot start scoring. Cancellation at the boundary reads no labels and starts no
score worker. Recovery never starts a missing inner score.

Public receipt and cost readers distinguish local/v1 and guest/v2 registrations.
Guest success has separate reported inference/scoring containers and a total of two.
A failed inference has no scoring container. Missing inner completion leaves its
count/time and totals unknown. Local counts and v1 records retain their semantics.
A reconstructed guest service with a recovery-only facade recovers an original
completed score without live inference scopes or label files, and refuses execution.

The first nine cases passed. Closing completed authored HTTP peers before the local
score worker removed its fork/thread fixture warnings. The 60-case guest/local
composite, receipt, cost and grant regression passed in 166.67 seconds. All 15 final
guest-composite cases passed in 110.60 seconds. A retained public-only suite passed
fresh score/receipt/transition/cost replay with models, processes, sockets, arrays,
clocks, publisher source probes, writes and unrelated/private reads denied during
verification. Evidence and source snapshots are under verification-guest-composite-v1.
Full default tests were not rerun. All guest results and container proof fields are
authored. The fixed local stdlib scoring fixture runs, but no actual container,
image, guest model or independent labels run through this increment.

Core count remains 223 with changed orchestration/registration/accounting sources.
No default CLI/scorer allowlist changed. Early unstarted-resource cleanup, strict
filesystem timing and actual runtime/privacy, installed/platform/host qualification
remain open. Independent tasks, useful gains/tolerances and scientific comparison
remain open. Part 5 is incomplete.


## Original creation cleanup before watchdog ownership

The candidate facade now attempts scoped cleanup when original creation fails
before watchdog ownership. A create-only plan binds the original charged grant,
runtime, nonce, response and known/discovered container ID. The fixed window and
durable kill/removal intents prevent deadline renewal and mutation retry. Original
response warnings remain adverse start evidence while permitting owned cleanup.
The created journal event retains cleanup identity even if its convenience pointer
is lost. Cleanup refuses foreign ownership and blocks journal/scientific advance.

The related cleanup/daemon/executor/watchdog regression passed 99 cases in 142.37
seconds. After the response-pointer fix and native lost-response fixture, the
final cleanup/composite check passed 40 cases in 143.26 seconds. Guarded relocated
saved-owner replay passed without the original suite or daemon. Evidence is in
`examples/utility/verification-guest-creation-cleanup-v1/`. There are 224 core Python
files. These are authored peers and fixture processes, not actual containers.

Unknown CREATE followed by named absence stays unresolved. An uncertain consumed
removal cannot be retried automatically. Existing watchdog ownership prevents a
competing cleanup path, and interrupted startup still needs explicit resolution.
Strict filesystem timing, actual runtime/privacy, current installed/platform/host
qualification, independent task admission and scientific confirmation remain open.
The full default suite was not rerun. Part 5 is incomplete.


## Current guest wheel and extracted offline readers

A fresh copied-input setuptools build now includes all 224 current core Python
files and 314 wheel Python sources. All core bytes agree with the current source,
and 355 build inputs are pinned. Isolated interpreters outside the checkout
loaded that extracted wheel and passed original guarded cleanup replay, original
guest composite score/cost replay and CLI help. This is extracted-wheel evidence,
not installation or runtime qualification. No dependencies were installed.

`examples/utility/prepared-inference-environment-v4/` pins the successor wheel and
the existing 49 Linux archives, totaling 265,399,717 compressed bytes. All three
prior manifests still verify. No archive was acquired, no image built and no
actual daemon/container/provider/model executed. Starts and qualification remain
false. Evidence is in `examples/utility/verification-guest-current-wheel-v1/`.

Installed/platform/host/runtime/privacy qualification, interrupted watchdog startup
resolution, strict filesystem timing, independent admission/approved thresholds
and frozen scientific confirmation remain open. This increment does not rerun
the full default suite. Part 5 remains incomplete.


## Original watchdog startup cleanup verification

Original startup reconciliation now shares the child's cleanup lease and fixes one
cleanup window, reason and mutation intents. Live-child takeover is refused.
Delayed startup resumes cleanup before readiness. Original-owner/control-scope
checks reject copied control directories before lock creation or API calls. The
facade cleans its original unstarted resource after a startup fault or failed
Popen while retaining the original error and charge. No replacement child, model
start, attachment or scientific allowance is granted.

The initial focused/watchdog check passed 30 cases in 52.69 seconds. A delayed-child
regression then exposed readiness after cleanup had begun and was corrected. The
related lifecycle regression passed 105 cases in 344.82 seconds. A separate copied
control-directory test reproduced scope reuse and was corrected. All 34 final
startup/composite cases passed in 146.76 seconds, including killed-child and failed
Popen recovery. The earlier regression scope and failures remain retained. Final
source pins match all three changed core files and the new test module.

Guarded cold replay of the retained original startup-cleanup owner passes after
relocation without its original suite, daemon, sources, models, arrays, sockets,
processes, clocks, writes or unrelated reads. The older public composite score and
cost reader still passes. Evidence and source snapshots are under
`examples/utility/verification-guest-watchdog-reconcile-v1/`. All daemon/container
observations are authored fixture records. There remain 224 core files. The
preceding wheel/prepared v4 input snapshot predates this increment. No full default
or actual runtime/privacy qualification was performed for these changes.

Unknown late creation and consumed uncertain removal still require explicit
resolution. Strict filesystem timing, current installed/platform/host checks,
independent task admission, approved thresholds and the frozen scientific comparison
remain open. Part 5 remains incomplete.


## Candidate offline guest image recipe

The new administrative image preparer verifies exact core/wheel source alignment,
then saves an immutable recipe without acquisition, extraction, installation or
execution. It binds a Linux amd64 Python base image and micromamba archive to the
existing 49 locked packages and current wheel. Official public metadata was read
with bounded requests to verify platform, digest, compressed size and installer
license/dependency facts. No archive or layer was fetched. The proposed remote
payload allowance is 317,657,548 compressed bytes plus 1 MiB of registry metadata.
The proposed one-build allowance is 1,200 seconds and 8 GiB of disk, currently
unenforced. These are not measured unpacked size or runtime claims.

Thirty-nine image/environment tests passed in 1.11 seconds. They cover stale,
missing, extra and symlinked source files, no overwrite, corruption, repinning
that cannot create authority and relocated metadata replay with execution denied.
A fresh copied-input wheel contains all 224 core files and 315 Python sources
from 356 build inputs. Its SHA-256 is
`8d693b02719c1325d7f82ac674e35418e1ab1962bbf1db475211558284b64977`.
The prepared v5 environment retains all four earlier input packages. A fresh
isolated reader loaded the image preparer from the extracted wheel outside the
checkout and verified a relocated recipe while denying processes, sockets, array
loads, clocks, writes and unrelated/source reads. The example index was updated
after the build, changing only that documentation input from the captured build
scope. All captured Python source bytes remain unchanged.

`prepared-guest-image-v1/qualification-proposal.json` declares 26 proposed cases,
at most 20 creations and 15 start intents. All are not attempted. Actual daemon
handlers and separate diagnostic profiles remain missing. Verified context
materialization and bounded acquisition/build runners remain missing too. The
recipe is not a ready execution request and does not enable a default runtime.
Scoring, fitting, providers and independent labels have no allowances in this
proposal. Complete private/composite, platform/host and scientific qualification
remain open. The full default suite was not rerun. Part 5 remains incomplete.


## Offline image context materialization

The new administrative `guest_image_context` tool copies only the recipe's
preexisting pinned payloads and files. It validates all inputs before creating
output and rechecks bytes during bounded streaming copies. An explicit private
parent-directory creation step corrected the first run's three permission failures.
Partial copies cannot be overwritten or resumed. The manifest is committed last.
The cold reader checks the exact closure, rejecting changed payloads/recipes/proof,
extra files/directories, symlinks and authority promotion even after repinning.

The final context/image/environment scope passed 61 cases in 2.68 seconds. Guarded
relocated fixture replay passed with original input scopes removed, file reads
confined to the saved context and writes/processes/sockets/clocks denied. Positive
copies use authored bytes and fixture installer metadata, not real packages. The
production recipe was checked against an empty cache and refused missing inputs
before output creation without acquisition or execution. Its first proof harness
had a script-path import error; both that failure and the corrected result remain
retained. Evidence is in `examples/utility/verification-guest-image-context-v1/`.

The prior image plan and prepared v5 wheel remain unchanged. Their core scope is
224 files and the wheel contains 315 Python sources. The new host materializer is
not in that wheel and has no installed-package qualification. Real archives remain
unacquired. A bounded build runner, actual-daemon handlers and separate diagnostic
profiles remain required. No image/container/model/provider, fitting or independent
confirmation ran. The full default suite was not rerun. Part 5 remains incomplete.


## Actual pinned archives and production build context

The new downloader binds an archive-only request to its source, original target
scope, exact HTTPS origin, filename/length/hash list and original deadline. GET
intents are persisted before requests. Redirects, fallback origins and automatic
retries are prohibited. A cache is consumed before the first GET. Interrupted
attempts cannot renew their allowance. Lost final acknowledgement preserves the
original completion. Cold verification checks the exact evidence/file closure.

The final related check passed 85 cases in 3.12 seconds. Tool approval review then
allowed the concrete 50-file archive-only request. All 49 locked package archives
and the micromamba installer passed exact length/hash checks: 272,387,807 payload
bytes in 8.871 seconds. No code was installed or run from those files. A real
production context was materialized and verified, copying 275,243,466 pinned file
bytes. Both outputs are private and ignored by targeted Git rules. No locks,
historical evidence or existing outputs were rewritten.

A fresh isolated administrative reader verified relocated copies of the real
cache and context with original-scope reads, writes, execution, network, clocks,
source probes and array loads denied after code initialization. Installer headers
also meet the recipe's extraction bounds: 58 members, 18,553,507 declared bytes,
and one regular 18,292,808-byte executable member. No file was extracted/executed.
Evidence is in `examples/utility/verification-guest-archive-download-v1/`.

The preceding image plan and runtime wheel retain their original identities and
224-core/315-source scope. The new host downloader/context helper is not in that
wheel. Archive acquisition does not change its authority/admission fields.
Installation, base-image acquisition/build and execution require their separate
authority. A bounded build runner and actual-daemon/diagnostic handlers remain
required. Installed/platform/host, runtime/privacy and independent scientific
qualification remain open. Full default tests were not rerun. Part 5 is incomplete.


## Reviewable local image-build request

The new administrative build helper verifies the saved production context and
pins an installed client and local Unix endpoint using filesystem metadata only.
It prepares six fixed commands for daemon/builder metadata, one immutable base
pull, base verification, one local image build and final original-ID inspection.
An empty Docker configuration and minimal environment exclude ambient remote
builder selection, credentials, secret forwarding, SSH and image pushes. Driver,
endpoint and target-platform checks precede acquisition. Failed jobs remain
consumed and cannot resume or obtain a fresh allowance automatically.

All 103 related cases passed in 5.43 seconds. Docker/build metadata are authored.
Real owned Python client fixtures cover success, timeout and output overflow.
Cold completion validation uses saved request/source/intents/logs/image metadata
without probing a live client, endpoint, source or clock. It does not independently
attest Docker or validate every incidental client cache file. Local CLI help and
filesystem metadata were inspected without contacting the daemon.

`examples/utility/prepared-guest-build-v1/` contains the concrete request and private
ignored machine bindings. No work directory, daemon call, image acquisition,
installation or build has occurred. The proposed job has one 1,200-second client
deadline, 16 MiB per-command logs, one base pull and one build. Base compressed
layers total 45,269,741 bytes, with actual transport usage/retries unknown. CPU and
memory flags are per-step and daemon-dependent. Disk is not quota-enforced and
client termination does not prove daemon cancellation or owner-loss cleanup.

The runtime plan reserves installation/image assembly/execution for separate
authority. That approval is now the next required action for the concrete job.
The image remains an unqualified candidate even if assembly succeeds. Actual
runtime/private, installed/platform/host, diagnostic and independent scientific
requirements remain open. The runtime wheel retains its prior 224-core/315-source
scope and does not contain this host helper. Full default tests were not rerun.
Part 5 remains incomplete.


## Separate administrative wheel verification

A copied-input host-tools wheel now includes all 224 core files and 318 Python
sources from 359 unchanged input pins. It adds the administrative context,
archive-download and image-build helpers to the packaged-source check without
replacing the frozen guest wheel/environment, real context or prepared build
request. The new wheel digest is
`55fc3857513cb4a7155fc058fe18fac0f3de469ccb7f820264469404cbbcfc9b`.

Five isolated CLI-help checks passed outside the checkout. A fresh extracted-wheel
reader also verified the real 50-file cache, real context and authored build
completion from relocated data only after code initialization. Processes, sockets,
clocks, array loading, model imports, source probes, writes and reads outside the
saved data scope were denied. Package/source directories were outside that scope.
The first tar-based fixture replay refused nonprivate extraction modes. The
corrected harness restored private modes, and both initial and corrected logs
remain in `examples/utility/verification-host-tools-wheel-v1/`.

No dependency installation, daemon call, image acquisition/build or scientific
execution occurred. Dependencies were inherited from the base interpreter. This
is extracted-wheel evidence. The pending image-build request is unchanged and its
work output remains absent. Installed/platform/host, runtime/privacy and independent
scientific qualification remain open. Part 5 is incomplete.

## Current default verification and unresolved runtime step

The complete v5 default suite passed with 3,415 passed and 120 skipped in
3,143.14 seconds. JUnit has 3,535 entries with zero failures/errors, including
seven module-level skips beyond the 3,528 collected tests. All 603 source pins
matched. The 224 core and 243 test Python files had no additions or removals.
See `examples/utility/verification-current-base-v5/verified-summary.json`.

The preceding v4 full run recorded 3,403 passed, 120 skipped, nine failures and
three setup errors. Its saved logs and JUnit remain intact. All 12 affected cases
passed in separate reproductions and in the complete unchanged-source v5 run.
V5 inhibited idle sleep from launch. Its two owned processes exited at completion.
The original v4 temporary fixture tree is absent. Saved observations support a
timing hypothesis but do not prove every failure's cause.

Nineteen documentation checks passed after updating the audit and verification
notes. The handoff now points to the current result rather than calling earlier
source checkpoints current. Optional-environment, installed, Linux, live-host,
private-runtime and independent scientific qualification retain their recorded
limits. No frozen benchmark matrix was rerun.

The prepared build request remains unchanged. Image assembly and diagnostic
execution still need their separate authority. The 26-case proposal is not an
executed qualification and its frozen original metadata is preserved. The next
runtime action is the reviewed image build, followed by actual handler and
boundary qualification under its own fixed scope. New authored metadata cannot
substitute for that execution or the four tasks' scientific admission.


## Approved image preparation failed at plugin discovery

The approved v1 request reached two client commands. The daemon version read
succeeded. The second command reported that Docker could not find Buildx under
the fresh configuration. No base pull, installation or image build ran. The
original work remains consumed and no retry was attempted. Evidence is under
`examples/utility/verification-guest-build-plugin-v1/`.

The administrative helper now emits request v2 with an explicitly pinned
installed Buildx executable. It stages and verifies a private plugin copy while
keeping the Docker configuration empty. Every command verifies original and
copied bytes. Cold readers verify the saved copy without original access. Legacy
v1 reconstruction remains supported. The related regression passed 101 tests
with no skips, failures or errors; repository lint passed. An actual Buildx help
probe passed with fresh configuration and an absent daemon endpoint, performing
no image operations. The two changed full-checkpoint pins are the helper and its
tests. All 224 core files and frozen guest inputs remain unchanged.

The corrected request is `examples/utility/prepared-guest-build-v2/request.json`,
digest `4b292a07a2161f2acb68d08785db6a5c83fd5ef0e17fc06914dbbda6d901eaf5`.
It keeps the same context, base, package archives, six commands and original
limits. Its new work directory is absent. A new approval is required because
the consumed original request forbids retries or a renewed allowance. Runtime,
private scoring and independent scientific admission remain open.


## Approved v2 stopped at endpoint alias validation

The approved v2 image job ran two clients successfully, then rejected Buildx's
`default` endpoint alias because its rule required the literal pinned Unix URI.
No pull or build ran. The original v2 job remains consumed and was not retried.
Read-only context inspection established that the alias resolves to the exact
pinned local socket. The new v3 request includes that inspection before builder
validation, preserving the Docker driver and amd64 checks. Legacy v1/v2 records
retain their original endpoint rules and command lists.

All three actual metadata preflight commands pass. The final related regression
passed 105 tests with no failures, errors or skips, and repository lint passed.
Evidence is under `examples/utility/verification-guest-build-context-v1/`. Only
the administrative helper and its tests differ from the v5 full default pins.
Core source and the frozen guest inputs remain unchanged.

Request `d9bd15a3f74b84126ca6b1d00e487b841350895be1225653952ee6946ca0b759`
is prepared under `examples/utility/prepared-guest-build-v3/`. Its seven commands
share one 1,200-second client deadline and the same image inputs and resource
limits. Its work directory remains absent. Both earlier jobs remain preserved;
v3 needs new approval and has not executed. Runtime/privacy and independent
scientific admission remain open.


## Approved v3 pulled the base and stopped before building

V3 passed its three metadata checks and pulled the pinned Linux amd64 base.
Its base inspection client exited zero, but the config-ID equality check rejected
Docker's manifest-based image ID. The build command never started. The original
job and acquired base remain preserved; no retry or cleanup was attempted.

A public manifest-only fetch returned 1,752 bytes whose hash matches the original
pinned manifest and whose config descriptor matches the original expected config.
V4 carries that proof and accepts the manifest ID only with matching descriptor
digest, size, media type and repository digest. Existing request versions retain
their original rules. All five actual saved pre-build responses pass the new
checks without relabeling v3. The corrected reader requires the saved proof
without network or original-path access. Moby's containerd inspection source
corroborates the observed ID representation.

The related regression passed 114 tests with no failures, errors or skips, and
repository lint passed. Only the administrative helper, tests and small metadata
fixtures changed. Core source and frozen guest inputs remain unchanged. Evidence
is under `examples/utility/verification-guest-build-base-v1/`.

V4 request `c5fe7f7072d84cb436c5fa866cc39fe7b70506692ec4774c68f68424469ce0ec`
is prepared and unexecuted. It keeps the same seven commands and 1,200-second
client deadline. Earlier requests remain consumed, so another job needs new
approval. Runtime/privacy, installed qualification and independent scientific
admission remain open.


## Actual v4 image assembly and cold completion verification

The user approved v4 and all future corrected image-build versions within the
established scope and limits. V4 completed all seven clients in 45.4099 seconds.
It installed 49 pinned packages offline and the frozen wheel, passed the Linux
amd64 build-time core import smoke, and produced immutable candidate image
`sha256:fc19692dff41a699600f76a79a97ed6cdcdf927f28e09984a79f33dcee46c399`.
The final inspected image size is 1,019,479,486 bytes. This used the local ARM64
OrbStack host, not independent x86-64 hardware. The package transaction reported
zero download bytes. Registry traffic and total physical storage were not measured.

Completion `28d422cf3dc61628de0e2db9410a644ab683e31b3e77906c5e5a679a23e0e966`
verified against the original saved proofs. A fresh subprocess also reconstructed
it from 31 private relocated files totaling 74,134,974 bytes, including the pinned
plugin binary. After code initialization, guards denied outside reads, writes,
imports, processes, sockets and clocks. The source imports precede those guards
and dependencies are inherited; this is not installed-package qualification.
No image payload or executable plugin was copied into public evidence.

The completion, public metadata, build output and guarded reader evidence are
under `examples/utility/verification-guest-build-actual-v1/`. Original work remains
ignored and intact. Both the v4 request README and current handoff now report
completion. Nineteen documentation checks passed. No runtime inference, fitting,
scoring, provider or independent confirmation ran. The candidate remains
unqualified for private execution, resource enforcement and owner-loss cleanup.
The 26-case qualification proposal still needs implemented handlers and a fixed
diagnostic policy before its separately scoped actual execution.


## Actual guest Python identity and saved replay

A separate metadata-only probe observed the cached candidate image's Linux
x86-64 CPython 3.12.13 identity, isolated interpreter, UID/GID 1000 and package
0.2.0. The installed identity source matched the frozen wheel metadata. It
recorded one container start in 9.8228 seconds and original-container absence.
No host mount, image pull, model, fitting, label, scoring or provider work ran.
The resource flags are requested settings, not enforcement qualification.

Request `f2df304d9bee6b956c0e9641c2323a9c1446e9610621cd03669ec36dbe535107`
and completion `653357f8bf204e3366d15d68f86c4c2f230db11409cf5f24c2f8526d7727c8d8`
remain preserved. The exported profile digest is
`499c937bedcf48ddc008f81c3b9157128ebe45b1c8bb4f7d33e8ffca4e734c56`,
with boundary `unqualified-candidate`. It binds the actual Python build digest
`b045b35133aee229f091997de805d765ccda1c386ba6b0802f6534008f759cca`.

The metadata controller reserves one create/start, has a fixed program, no
arbitrary command or input paths, a 60-second active allowance and one ten-second
cleanup window. Unknown removal is never retried, foreign ownership blocks
removal, failures retain reserved and known physical work, and consumed work
cannot start again. The saved reader bounds files and verifies original request,
source, launch, output, allowance and producer cleanup metadata without live calls.
It does not independently attest OS behavior or admit private inference.

The first broader restricted run had fixture failures. A PATH-only reproduction
still failed. The same unchanged fixture passed with owned-subprocess permissions,
then 111 related cases passed. After replay/file-bound additions, the final guest,
identity and documentation regression passed 140 tests with zero failures, errors
or skips; repository lint passed. Initial failure logs and all final evidence are
under `examples/utility/verification-guest-identity-v1/`. A fresh guarded process
replayed 12 relocated files with outside reads, writes, imports, processes, sockets
and clocks denied after code initialization. Dependencies are inherited, so this
is not installed-package qualification. The report-only CLI also verified the
actual completion.

Core source and the built guest image are unchanged. This metadata probe is
separate from the 26 planned controls, whose handlers and diagnostic policy remain
open. The implementation plan now records the full remaining sequence through
resource/lifecycle checks, private composite qualification and independent task
admission. No gate or scientific criterion changed.

## Actual fixed resource diagnostics

The separate stdlib worker now checks actual guest identity, cgroup limits,
capabilities, seccomp, namespaces' visible mounts, root/workspace and loopback
before bounded resource actions. The controller permits only six fixed cases,
pins image/client/local daemon/source, records create/start intent and starts an
independent owner-pipe cleanup process before creation. Cleanup takes an exclusive
lease, verifies original ownership and never repeats an uncertain DELETE.

V1 request `0a99d30a1f5df56c3a10fa099ec23a92f66cbce4c6a646c9267fef01d1669206`
created one container and refused before start because Docker merged public base
image variables into its environment. Original cleanup refused and remains
unknown in its record. A separate administrative action verified the exact
unstarted CID, command, labels and expected image environment, removed it once
and confirmed absence. Its original source bytes match the recorded hashes.

V2 explicitly clears the unused inherited variables and saves producer sources
at preparation. Request
`ad457623720c9d9514dc26c76bbae4f9624c9519f400e26391db1f91545db639`
passed all six controls in six creates/starts. Memory produced daemon OOM evidence
and exit 137. The PID case observed EAGAIN at 16, then reaped 15 children. Workspace
returned ENOSPC at 134,217,728 bytes. Read-only root, network and authored host
canary returned EROFS, ENETUNREACH and ENOENT respectively. Each original container
was subsequently confirmed absent. There were no models, fitting, labels, scores,
providers, pulls or host mounts. Combined resource work is seven creations and
six starts. The failed creation is not erased or assigned to a successful case.

Completion `f5395216c48d94a2ada8f5090467178b2f3471d3026197c63e9412f12aa5c103`
replays without live operations. A fresh process verified 108 relocated metadata
files totaling 403,086 bytes under guards after imports. Dependencies are inherited,
so this is source-based replay, not installed qualification. Public evidence
omits machine bindings and the canary path. The original local proofs remain
ignored and intact under `outputs/guest-resources-v{1,2}`.

The original 26-case proposal remains unchanged and unexecuted as a whole. These
separate versioned diagnostic requests do not silently expand its 20-create/15-start
allowance. Actual inference/lifecycle controls, including unexpected owner loss,
remain open. The production frozen-inference environment projection also needs
explicit treatment of inherited image variables before its actual checks. This
increment changes no core source, runtime wheel/image or scientific criterion.
See `examples/utility/verification-guest-resources-v1/README.md`.

All 114 diagnostic/proof tests passed. The final related diagnostic, identity,
build, daemon, interpreter and documentation regression passed 254 tests with no
failures, errors or skips in 38.87 seconds. Repository Ruff checks passed. The
prior full default checkpoint is retained at its original source scope and was
not rerun for this example/helper increment.

## Derivative image with explicit environment and provenance

The actual original image inherited three unused public base-image environment
variables and had no OCI provenance labels. The strict production image/container
checks are unchanged. A separate fixed host helper copies only the verified local
image filesystem into a scratch final stage, declares the seven approved
environment entries and adds the required purpose/environment/wheel labels.
It has no RUN, package installation, host-file copy, pull or push command.

V1 request `e4e49dbdd5d452fbc8f284f6683c7884ff6d1e1782c9f865b048edbf3f3e8a28`
completed four read-only clients. The API transport then refused its 1,200-second
tag-check deadline before sending the GET. No tag/build mutation occurred. V1 is
consumed. V2 caps the read-only GET to ten seconds within the original deadline.

V2 request `2d6da06f53091a337c2804501b6798fc07f1a86594b7d34a05ebb50b6d904c61`
completed nine clients, one previously absent local source tag and one build in
29.9822 seconds. The new image is
`sha256:516cb2702eb45d99264dc90622fea8de4de987f68b4266ba8c86da4c312390de`.
Inspected size is 440,613,645 bytes, not measured physical disk use. Its actual
inspect passes the existing strict image check with the declared environment and
wheel metadata. The saved build log resolves the original source digest. A later
reader additionally validates that resolution. The local ARM64 OrbStack host,
runtime wheel and 224 core files are unchanged.

Completion `008aa6f0d4c850548cbc5c8ecd173ce1a031679d7d3151b9a961d8ff3331afe0`
replays from saved data. The fixed metadata probe then observed Linux x86-64
CPython 3.12.13 and the expected installed identity source in one container start,
completed in 5.8893 seconds and confirmed absence. Identity completion is
`332206006452b9f4291cd6608093729249500d43bde08bcfaba78ec0961a7e30`.
Its profile digest is
`f63507160485327f5660abc895aaf2462d64bf12af1bf2f9f09685ab2667716e`,
with boundary `unqualified-candidate`.

Fresh guarded processes replayed the image from 41 relocated files (178,952
bytes) and identity from 12 files (117,131 bytes). Imports precede guards and
dependencies are inherited. This is source-based metadata replay, not installed
or OS qualification. All 315 declared wheel files still match current declared
host sources. New host helpers are outside that frozen wheel's source set.
No model, fitting, scientific label, score or provider ran in these operations.
See `examples/utility/verification-guest-image-environment-v1/README.md`.

The original image and its six resource results remain intact. They do not
qualify the derivative. Its diagnostic requests must bind the new image and
explicitly account for its inherited OCI labels before creation. Its resource,
six preflight and fourteen inference/lifecycle controls, full-chain private
qualification and independent task admission remain open. The original 26-case
proposal and every consumed attempt remain unchanged.

The final related regression passed 285 tests with zero failures, errors or skips
in 39.82 seconds. It includes the 30 image/proof tests, identity, resource,
daemon, interpreter and documentation checks. Added metadata-size checks caught
an intermediate helper name collision, reproduced and fixed before the final
run. The failed reproduction and preceding 281-case checkpoint are retained.
Repository Ruff and `git diff --check` passed. Full default and installed-package
qualification retain their earlier recorded scopes.

## Derivative resources and first actual frozen guest inference

The fixed diagnostic catalogue now binds the derivative image explicitly. Its
seven environment entries and inherited OCI labels must match before creation.
The original image retains its exact prior configuration. Unknown images and
unexpected inherited values refuse. All six derivative controls passed with six
creates/starts and original-container absence. Completion is
`e899a83865a1ae3619af3fcfbbf68b204525566f168350ffa258582556a6df8b`.
Both resource profiles retain 13 creations and 12 starts, including the original
refused creation. A guarded reader verified 108 relocated files (405,034 bytes).

The production guest executor then completed one actual frozen inference over
a previously selected authored fixture. Its forcing was marked exposed and the
original fit/seed retained. No fitting-label array files were copied into the
suite/source snapshot. Two fixture preparations refused before driver-copy
intent or daemon/model activity: intermediate directory modes, then missing
declared model Python sources. Their snapshots and source versions are preserved.

The successful request is
`9cd0645ff9ef5240f6052164eca77b6b5d9bdfe6fc1998af5b8b759ec7d88ea8`.
Completion is `3bd33aff622278fefda714cd2ab7bbf0404f3bf7a4b913f8e13a15ec5d24c9bd`.
One container start passed all four physical checks. Maximum daily balance
residual was about 3.55e-14 mm against the existing roughly 1.70e-8 mm threshold.
Lifecycle duration was 1.6112 seconds, model child 0.0191 seconds. These are single
observations, not speed comparisons. Original-container absence was recorded and
confirmed by a separate read-only GET. No fitting, scorer or provider ran.
The composite grant reserves two starts; only inference was attempted. No score
or finished parent confirmation was inferred.

Fresh recovery from the portable public archive verified 97 files (841,273 bytes)
without the original source, drivers or work. Model imports were blocked from
startup; file-content reads outside proof, writes, imports, processes, sockets,
array loading and clocks were denied after metadata initialization. An initial
descriptor-read guard refused legitimate scoped FD reads. The corrected guard
checks relocated file inodes, retaining the original refusal. Dependencies were
inherited. This verifies source-based metadata recovery, not independent physics
recomputation, whole-package installed qualification or OS attestation.

The final related regression passed 417 tests with zero failures, errors or skips
in 286.71 seconds. Core source and the frozen runtime wheel remain unchanged.
Evidence is under `verification-guest-resources-v2` and
`verification-guest-inference-smoke-v1`. The original 26-case proposal is unchanged.
This separate smoke does not satisfy its numerical-parity case or complete the
preflight/failure matrix. Full-chain private qualification and scientific
admission remain open. Part 5 remains incomplete.


## Native reference and six preflight refusals

One native inference reuses the completed guest inference's exact fit, seed, axis
and exposed drivers. No guest rerun, fitting or scoring occurred. All seven
outputs passed fixed symmetric tolerances (absolute `1e-10`, relative `1e-12`).
The largest difference was `2.1316282072803006e-14`. Prediction JSON was not exact,
but its vector passed and selection/model/partition metadata matched. Saved
arrays, original producer, native job/result and stopped/verified supervisor
report are retained in `verification-guest-prediction-parity-v1`. The saved reader
recomputed the results after relocation without process or network access.

Six fresh frozen fixture copies tested changed source, model, seed, daily axis,
partition and cancellation before access. Exact expected exceptions/messages
were saved before execution. Guards counted and denied every NPZ/driver open, API
request, socket creation and process launch. All counters stayed zero and all
refusals matched. `verification-guest-preflight-controls-v1` retains the requests,
intents and results. Original parent composite reservations remain charged and
unfinished. The original 26-case proposal and all earlier attempts are unchanged.

These controls establish preflight behavior and numerical platform/transport
parity over exposed authored inputs. Remaining adverse lifecycle cases, private
scoring, four-family task specifications and independent confirmation are open.

The parity/preflight regression passed 154 tests in 117.24 seconds, with zero
failures, errors or skips. Documentation rechecking passed 19 tests. Ruff and
`git diff --check` passed. All 224 core and 315 declared wheel Python sources
still match the frozen runtime inputs. The incremental source inventory is
`examples/utility/source-inventory-guest-parity-preflight.json`. The earlier full
default checkpoint retains its original scope and was not rerun. The
`examples/utility/qualification-state-guest-v1.json` evidence map distinguishes
13 separately evidenced cases from 13 remaining adverse daemon cases without
changing the original proposal or resetting any attempt.


## Actual cancellation after creation and before start

Two [actual local cancellation controls](../../examples/utility/verification-guest-cancellation-controls-v1/README.md)
passed against the derivative image using fresh copies of the exposed frozen
fixture. Each created one container and started none. Cancellation after the
original `created` event used production creation cleanup. Cancellation at the
persisted `start_intent` used the production watchdog, which reported cancellation
and absence. Both paths verified original ownership and deleted once without a
kill. Separate actual GETs observed both exact container IDs absent. No fitting,
model, scoring or provider work ran. Parent reservations remain charged.

The saved production cleanup readers verified the original plans, observations,
mutation intents and absence records. A 93-file public archive retains owner and
API proof, including the original transfer tars with known exposed meteorological
drivers. It includes no fitting or private labels. Fresh guarded replay passed
from copied proof and verified archive extraction without separate suite/source/
driver roots. After initialization it permitted only saved content reads and
blocked writes, imports, clocks, array loading, sockets and processes. The initial
cold invocation failed to import example helpers. Both its log and the corrected
results remain. No package-installation or OS attestation claim follows.

The successor `examples/utility/qualification-state-guest-v2.json` preserves the
original proposal and v1 evidence map. It records 15 separately evidenced cases
and 11 remaining adverse daemon cases. Running cancellation, owner/watchdog
loss, adverse output, lost responses and the private inference/scoring chain
remain open. Scientific task specifications and independent utility remain
separate requirements.

The cancellation/watchdog/dispatch regression passed 136 tests with zero
failures, errors or skips in 323.84 seconds. Its reader revision
predates the added after-create transfer verification. The final reader/control
checks passed all 10 tests, including corrupted transfer refusal, and the saved
archive guard passed again. Exact scopes and reconstructed preceding reader
snapshots are retained in the checkpoint summary. Documentation checking passed
19 tests. Ruff and `git diff --check` passed. All 224 core and 315 declared runtime
Python sources remain unchanged. The full default checkpoint was not rerun.
The source successor is `examples/utility/source-inventory-guest-cancellation.json`.


## Producer acknowledgment loss after real CREATE and START

Two [actual local acknowledgment-loss controls](../../examples/utility/verification-guest-response-loss-v1/README.md)
passed using the exposed frozen fixture. A wrapper saved successful real daemon
responses, then withheld them before the executor received them. This is producer
response loss, not a network outage. Two containers were created and one started.
Both original containers and the watchdog PID were confirmed absent. CREATE loss
retained `create_intent`; production nonce-bound cleanup found and removed the
original resource without another CREATE. START loss retained `start_intent`; the
production watchdog cleaned the original started resource after exception-driven
owner-pipe closure. This does not establish actual owner-process-kill behavior.

Both original grants refused redispatch with zero API requests. No model result
was observed. The one START remains charged and inference elapsed time remains
unknown. Parent reservations stay unfinished. There was no fitting, private
scoring or provider work in these actual controls. Saved transfer, raw withheld
response, ownership, cleanup and absence proof replayed from a verified 92-file
archive under a fresh guard without separate suite/source/driver roots. After
initialization the reader denied external content reads, writes, imports, clocks,
array loading, sockets and processes. Dependencies were inherited before guarding.

`examples/utility/qualification-state-guest-v3.json` preserves the preceding maps
and original proposal. It records 17 separately evidenced cases and nine remaining
adverse daemon cases. `examples/utility/guest-qualification-accounting-v2.json`
retains 20 creations, 16 container starts and one native reference in its explicit
scope. Three inference starts are charged, including one with unknown model work
and no result. The register excludes build internals and authored test fixtures.
It creates no allowance, refunds nothing and does not complete the original
matrix, private runtime, task admission or independent scientific comparison.

The focused acknowledgment-loss regression passed 36 tests in 37.87 seconds,
with zero failures, errors or skips. This covers the two new helpers, original
cleanup/no-retry controls and documentation. Ruff and whitespace checks passed.
All 224 core and 315 declared runtime Python sources still match the frozen
inputs. The incremental source inventory is
`examples/utility/source-inventory-guest-response-loss.json`. The previous broad
and full-default checkpoints retain their source scopes and were not rerun.


## Exact owned owner/watchdog process loss

Four [actual local process-loss controls](../../examples/utility/verification-guest-owner-loss-v1/README.md)
passed with four creations and two STARTs. Three owners were killed by their
exact Popen handles. The fourth owner killed its own exact ready watchdog handle,
then observed production START refusal and startup cleanup. All original
containers and watchdog PIDs were confirmed absent. No replacement watchdog,
CREATE, START, fitting, scoring or provider call was used for recovery.

Owner loss before watchdog readiness occurred after the saved original plan and
before child spawn. Explicit parent startup cleanup was required. It does not
establish autonomous pre-watchdog cleanup. Running-owner loss occurred after an
actual running START and before input transfer. It does not establish a kill
during model computation. After-capture owner loss preserved the actual model
result and recovered it through the production recovery-only facade without new
inference. Lifecycle time remains unknown. All original starts and unfinished
parent composite reservations retain their charges.

A verified 328-file archive preserves process identities, markers, signal intents,
terminal codes, owner/API/cleanup proof, original known-exposure input tars and
one public saved-result suite. It includes no fitting or private labels. A fresh
guarded reader replayed all four proofs and the captured success without
original work or separate driver/source roots. After initialization it denied
external content reads, writes, imports, clocks, array loading, sockets and
processes. Dependencies were inherited before the guard.

`examples/utility/qualification-state-guest-v4.json` retains the original proposal
and preceding maps. It records 21 separately evidenced cases and five remaining
adverse daemon cases: running cancellation and four adverse-output controls.
The scope limits above remain part of their evidence. The new cumulative register,
`examples/utility/guest-qualification-accounting-v3.json`, retains 24 creations,
18 container starts and one native reference across its listed operations. Five
inference starts are charged. Three model completions are observed and total
model work remains unknown. This does not admit a private runtime, complete the
whole matrix or establish independent utility.

The exact-process-loss regression passed 33 tests in 22.71 seconds, with zero
failures, errors or skips. The final source inventory is
`examples/utility/source-inventory-guest-owner-loss.json`. Ruff and whitespace
checks passed. All 224 core and 315 declared runtime Python sources remain
unchanged. Earlier broad/default checkpoints retain their source scopes and were
not rerun for these host helpers.


## Running cancellation and saved nonnumeric failure

An [actual running guest cancellation](../../examples/utility/verification-guest-running-cancellation-v1/README.md)
passed with one creation and one START. It required an original observed running
state, then cancelled before input transfer. The production watchdog recorded
cancellation and absence. A separate actual GET confirmed the original container
absent, and its watchdog PID was confirmed absent. This is not evidence of
cancellation during model computation.

The original receipt recovered as `infrastructure_failure`, with no model result
or prediction vector and with unknown lifecycle time. The original START stays
charged, the parent reservation stays unfinished and redispatch refused without
an API request. No new model, fitting, scoring or provider call was used for
recovery. A verified 157-file archive retains the original transfer, owner/API/
cleanup and public failed-receipt proof. Fresh guarded replay required no original
work or separate source/driver roots. After initialization it denied external
content reads, writes, imports, clocks, array loading, sockets and processes.

`examples/utility/qualification-state-guest-v5.json` preserves the original proposal
and prior maps. It records 22 separately evidenced cases with their scope limits.
Four adverse-output cases remain: physical veto, invalid numeric output, oversized
stdout and malformed stdio. The new cumulative register,
`examples/utility/guest-qualification-accounting-v4.json`, retains 25 creations,
19 container starts and one native reference in its explicit scope. Six inference
starts are charged. Three have model completions and three have no model result.
Total model work and missing lifecycle time remain unknown. The broader G1-G8
requirements, private qualification and independent comparison remain open.

The running-cancellation regression passed 28 tests in 18.69 seconds with zero
failures, errors or skips. Ruff and whitespace checks passed. All 224 core and
315 declared runtime Python sources remain unchanged. The incremental inventory
is `examples/utility/source-inventory-guest-running-cancellation.json`. Earlier
broad/default checkpoints retain their source scopes and were not rerun.


## Four-task proposal preparation and reference rules

The [v2 preparation package](part-5-confirmation-preparation.md) now carries the
existing public-data choices, proposed gain/secondary policies and all 24 authored
engineering cases. The `confirmation_choices` helper prepares it without models,
observations, providers or execution authority. Positive, unit/metric-matched
development-baseline references can be bound to proposed absolute margins. The
reference remains unadmitted until its receipt is qualified. Zero, nonfinite,
wrong-scope, wrong-route and underflowing values refuse.

Four dossiers now link the proposal and retain explicit policies. They remain
blocked drafts with unknown exposure, null partitions and null frozen thresholds.
Their preceding bytes are preserved. No separate person acting as custodian or
pre-existing private dataset is required. The trusted preparation/scoring boundary
and all G1-G8 evidence requirements remain in force.

A bounded anonymous solar metadata GET returned the same 64,652-byte site-2107
snapshot and hash. No observation CSV was requested. Missing explicit channel/
device joins, absent module/inverter and string topology, mixed intervals and
unqualified `L` timing remain specific blockers. Live PVDAQ documentation and
wind registry metadata were inspected. The live solar submission page returned
429, so its prior pinned rights record was preserved. No new rights, untouched
evidence, quality or coverage was inferred. See the package metadata review.

The confirmation-choice preparation regression passed 38 tests in 0.95 seconds
with zero failures, errors or skips. It covers reference identity/units/scope,
invalid and zero/underflow margins, all 24 engineering combinations, no dispatch
or model imports during preparation, published source reconstruction, blocked
dossier fields and existing preparation/documentation contracts. Ruff and
whitespace checks passed. All 224 core and 315 declared runtime Python sources
remain unchanged. The incremental inventory is
`examples/utility/source-inventory-confirmation-choices.json`. Earlier broad and
full-default checkpoints retain their scope and were not rerun. The first unit
run had five artifact-directory fixture setup failures; those tests were fixed
before the passing runs. No scientific work was involved.


## Solar interval, state and role partition preparation

The [solar input increment](../implementation-plans/part-5-solar-input-increment.md)
implements normalized average coarsening without disaggregation, explicit UTC
support, causal bounded-age temperature/wind holding, unit conversion and
interval-energy integration. Missing labels preserve valid weather driver state.
Driver gaps reset segments and require declared warmup. Scoring uses a common
eligibility mask. The original prototype's all-fields masking was corrected before
source or model use because it would have broken driver continuity at missing AC.

A separate four-window preparer claims both empty private scopes before reading
rows. Public files contain only development drivers/labels. The private bundle
retains the full forcing prefix and confirmation labels. Private-first/public-last
commits, source/plan hashes, fixed artifact bounds, generic unchained errors and
consumed failures are tested. The native preparer remains trusted code, not an
OS boundary. Source bytes, exposure, scientific adapter and private qualification
remain false. No actual observations, models, fitting, scoring, LLM or data fetch
were used. Site timing/hardware, raw parser and model/scorer admission remain open.

The final authored regression passed 74 tests in 1.06 seconds with zero failures,
errors or skips. Ruff and whitespace checks passed. All 224 core and 315 declared
runtime Python sources remain unchanged. The new source successor is
`examples/utility/source-inventory-solar-inputs.json`. The helpers are outside that
frozen guest wheel. Prior default/platform checkpoints retain their scopes. The
full Part 5 G1-G8 requirements, four adverse guest-output cases and independent
comparison remain open.

A final provenance correction binds each aligned row to its exact plan and
alignment implementation. Partitioning rejects a different unit/time/age policy
or implementation even when timestamps match. The preceding 74-test source is
preserved in `verification-solar-inputs-v1/source-snapshot`. The final v2 regression
passed 76 tests with zero failures, errors or skips. Its current source successor
is `examples/utility/source-inventory-solar-inputs-v2.json`. No actual observations,
models or source qualification were added by these identity checks.


Verified solar bundle readers now enforce sealed chronology, role masks, warmup,
energy and exact public forcing replay. The public reader opens only public files;
the reserved reader requires a trusted caller and grants no access authority.
The [solar input increment](../implementation-plans/part-5-solar-input-increment.md)
records 85 passing tests and an installed 228-source copied-input wheel on native
macOS with relocated authored bundles. No dependency installation, actual data,
model, fitting, scoring or provider calls occurred. The first wrong-directory
build was excluded and never installed. All 224 core and 315 frozen guest sources
remain unchanged. Source, exposure, scientific and private admission stay open.
The full Part 5 goal remains incomplete.


The solar source metadata reviewer now resolves the documented `sensor_name` CSV
header and verifies AC units, aggregation, identity conversion and explicit device
keys. It refuses ambiguous identities and retains absent equipment joins as
blockers. The pinned 2107 source still cannot supply a qualified hardware mapping.
The [solar increment](../implementation-plans/part-5-solar-input-increment.md)
records 102 passing related tests. The official DOE walkthrough also exposed four
public November 2017 example rows, now recorded without values in the exposure
register. No proposed-period observations or observation CSV were accessed.
Models, fitting, scoring and provider calls did not run. All 224 core and 315 frozen
guest sources remain unchanged. No task or private-runtime admission changed.


One actual authored guest-to-fixed-scorer chain completed through the production
composite service: two containers, one inference start and one scoring start, no
fitting or provider calls. Both original containers were observed absent. The score
matches independent arithmetic on public predictions, and saved confirm/recovery
reused it. A guarded fresh reader reconstructs the one score and both stages of
costs from 103 public files. The inference guest uses local ARM64 emulation for
amd64; the fixed scorer is ARM64. This is neither independent x86 hardware nor
private-runtime admission. The [execution evidence](../../examples/utility/verification-guest-composite-actual-v1/README.md)
keeps the prepared caps, original receipts, failed setup/read attempts and checks.
The cumulative accounting successor is `guest-qualification-accounting-v5.json`.
The four adverse-output cases and full independent Part 5 comparison remain open.


The actual composite regression is terminal: 62 passed in 201.28 seconds, zero
failures, errors or skips. The earlier restricted run retains 21 passes, eight
failures and 33 setup errors. A fresh scope with local supervisor/Unix-peer access
passed without source changes. Nineteen documentation tests, repository lint and
whitespace checks also passed. The guarded public reader's fourth initialization
configuration passed before any unguarded suite replay. All preceding failed logs
remain preserved. Current source pins are in
`examples/utility/source-inventory-guest-composite-actual.json`. Core and frozen
guest source bytes remain unchanged. The evidence map v6 adds the actual chain
separately and keeps all four adverse-output cases open.


The unchanged guest now has actual finite-input numeric-overflow evidence. The
frozen Hamon worker received a changed authored inference suffix while retaining
all selected-prefix rows and the exact fitting prefix. It returned `model_failure`
without arrays or predictions, cleaned its original container and replayed without
new execution. One inference start remains charged; no fitting or scoring ran.
The two-start parent reservation remains unfinished and model time stays unknown.
The [numeric-control evidence](../../examples/utility/verification-guest-numeric-control-v1/README.md)
records 73 passing related tests and guarded cold failure replay from 96 public
files. Evidence map v7 leaves three adverse-output cases open: physical veto,
oversized stdout and malformed stdio. Accounting v6 preserves all earlier uncertain
work. All 224 core and 315 frozen guest sources remain unchanged. No private-runtime,
independent-data or overall Part 5 completion claim is supported.


Two separately named output producers now have actual local-daemon evidence through
the production readers: malformed result magic was rejected, and an actual stream
crossing the stdout bound was rejected. Both original containers were cleaned up.
These are diagnostic starts, not model/scientific starts. No frozen image or normal
inference command allowlist changed. The [output evidence](../../examples/utility/verification-guest-output-diagnostics-v1/README.md)
records 166 passing related tests, caller-pinned offline reconstruction and guarded
cold replay after explicit checkout initialization. Setup refusals and failed
fixtures remain preserved. Evidence map v8 leaves physical veto without actual-daemon
evidence and keeps all three literal fixed-worker cases open. The original full
proposal and runtime/private admission remain incomplete. Accounting v7 retains
30 creations and 24 starts while preserving all earlier scientific charges and
uncertainty. The Part 5 real-task comparison remains unexecuted.


The final output reader also rejects duplicate container IDs across the two cases.
Twenty final controller/reader tests and guarded cold replay passed after this
check. The preceding 166-test source snapshot is retained, and the final source
inventory succeeds the separately preserved v1 inventory. No actual diagnostic
was repeated for this correction. Original fixed-worker scope remains incomplete.


The [WIND source increment](../implementation-plans/part-5-wind-source-increment.md)
adds a conditional, read-only range reader restricted to 2007-2011. One HEAD and
14 GETs inspected 2007 source metadata using 917,504 body bytes. Exact range hashes
and opaque ETag consistency pins are preserved, without claiming a full-object
hash. Captured ranges reproduce the metadata offline with no new HTTP requests.
No weather dataset values were indexed, but adjacent raw 2007 bytes may be present
in those ranges, so the exposure register records their acquisition. No reserved
year, model, fitting, scoring or LLM provider was accessed. Nineteen optional HDF5/range
tests passed; base checks passed 56 with one expected h5py skip. Actual point
extraction needs a new profile for the observed 2 MB chunks and qualified grid,
time, fill/scaling and direction semantics. The provider documents a 2014 physics
change, which remains a comparability blocker. No task or independent protocol was
admitted, and all 224 core and 315 frozen guest source files remain unchanged.


One actual 2007 WIND development point is now acquired through a separately pinned
large-read profile. A geographic-only scan of all 2,488,136 coordinates selected a
cell about 283.79 m from the proposed point, before either weather stage started.
The three stages used 175 requests and 137,311,517 body bytes. All 8,760 hourly
speed/direction rows pass the predeclared raw-fill/domain checks. The [point evidence](../../examples/utility/verification-wind-point-2007-v1/README.md)
contains the compact public raw/decoded data and request/accounting metadata.
Neighbouring raw chunks remain in the local acquisition cache and are recorded as
exposed. Full cached-source replay reproduces geography and every point array;
a separate compact guarded reader verifies decoding/calendar/accounting without
HDF5 or the raw cache. Thirty-nine HDF5/range/controller tests passed. No model,
fitting, scoring, LLM, install or reserved-year access ran. Direction semantics,
physical binding, other years, protected scoring and independent admission remain
open. Frozen core/guest sources and task thresholds remain unchanged.


The [2007 hourly wind development check](../../examples/utility/verification-wind-hourly-2007-v1/README.md) completed two wake calls
and one curve-reference call. Direct/wrapped scalar outputs agree, including
30.107811267852263 GWh for the fixed square baseline. The explicit 80 m hardware
uses all hourly pairs. Raw wind-from semantics and hourly integration remain
recorded development assumptions. No candidate improvement or private/independent
admission follows. The guarded reader checks saved parity and costs without
models. Thirty-six focused tests, 108 broader regression tests and 19 documentation
checks passed, with six optional-runtime skips in the regression. Frozen 224 core
and 315 guest sources remain unchanged. Other years, source comparability, raw
direction evidence, independent exposure and protected confirmation remain open.


The 2007 hourly wind profile now runs through the shared supervised scientific
executor and engineering study controller. One baseline and four frozen Sobol
trials completed with five charged, stopped observations and no pending work.
The baseline matched standalone parity at 30.107811267852263 GWh. The best trial
returned 30.068129320901953 GWh, so saved application of the frozen acceptance
rule retained the baseline. The 40 m corner domain is a development qualification
domain, not the final conventional recipe. Original completed replay added no work.
A guarded archive reader verifies hashes, inputs, five saved process/watchdog
receipts, outcomes and retention without models or current process inspection.
Eighty-nine related tests passed with one optional wind-runtime skip. Core 224
and guest 315 sources remain unchanged. Private execution, raw direction semantics,
other years, source comparability, independent exposure and the full Part 5 study
remain open. No task status, independent partition or absolute margin was admitted.

[Shared-controller wind evidence](../../examples/utility/verification-wind-hourly-study-v1/README.md).


A source-pinned solar CSV parser now feeds the existing interval, custody and
reader path. It requires declared headers, clocks, durations, availability, units
and quality codes. Role claims commit before source access. The authored canary
case preserves reserved separation and consumed failures. Thirty-nine focused
parser tests and 93 related solar tests passed. A guarded public reader opens
neither raw CSV nor reserved artifacts. No site observations, model, fitting,
scoring, provider or dependency installation ran. Site clock/equipment facts,
independent exposure and task admission remain unresolved. Frozen core/guest
sources remain unchanged. Current inventory: `examples/utility/source-inventory-solar-csv.json`.

[CSV preparation evidence](../../examples/utility/verification-solar-csv-v1/README.md).


The authored solar CSV workflow now has a bundled module example and a separately
verified 231-Python-file wheel. It prepared inputs and ran public/trusted-reserved
readers outside the checkout, with source fallback rejected. Source access followed
both role claims. The terminal guard refused an explicit reserved read in the public
phase. The CLI also completed. The 95-test regression passed. Dependencies were
inherited from native macOS; no fresh-environment, Linux, guest/private or full
installed-workflow qualification follows. Task admission and the independent study
remain open. Current inventory: `examples/utility/source-inventory-solar-csv-installed.json`.

[Installed CSV evidence](../../examples/utility/verification-solar-csv-installed-v1/README.md).


New operating-scenario preparation now seals a private draw before selection and
requires the complete barrier for trusted private reading. A suite-level claim
prevents replacement draws through new output scopes. Committed private completion
can recover public publication without new entropy. The authored actual control
generated 24 input rows, refused early access and later verified private derivation;
no model output or scoring ran. Only public commitments and the authored barrier
are archived. The guarded reader requests no private source or entropy. Fifty-six
related tests passed. The original grid proposal remains unchanged and unevaluated.
The alternative source proposal is not task admission or protected execution.
Actual data hashes still need final execution-grant binding before selection.
Frozen core/guest sources and all full Part 5 gates retain their prior limits.

[Operating-source preparation evidence](../../examples/utility/verification-engineering-generated-scenarios-v1/README.md).


Exact generated-source hashes now seal into a caller-pinned engineering binding
before selection. The existing scorer digest binds that record without a grant
schema change. Private opening requires the active reservation and access receipt,
then a permanent source-read intent. The authored service control read once and
replayed its constant fixture score without reopening or rescoring. One callback
start remains charged; zero model/solver calls ran. The guarded reader reconstructs
public binding/access/score identities without private data. Seventy-five related
tests passed. The fixture's scorer identifier is not a qualified native code closure.
Protected coupled-model scoring, physical checks, complete costs and real admission
remain open. Core/guest sources and the original grid proposal are unchanged.

[Exact source-binding evidence](../../examples/utility/verification-engineering-source-binding-v1/README.md).


The coupled scoring kernel now evaluated a fixed 0.05 A design across 24 previously
exposed control cases. All required checks passed. The run retained 24 model starts,
390 nonlinear iterations, 6,360 component calls and 1,950 component-linearization
calls. The initial derivative-counter description was corrected from source
inspection without changing raw evidence or rerunning models. Fourteen new kernel
tests and 44 related tests passed. Metadata-only cold verification imports no
scientific runtime and reads no private inputs or outputs. This is not the complete
registered protected callback, independent confirmation or a task/gain admission.
OS deadline/RSS, full cost, installed/Linux and full Part 5 limits remain open.

[Coupled scoring evidence](../../examples/utility/verification-engineering-load-scoring-v1/README.md).


The engineering load callback now connects the sealed source to the existing
confirmation service. It validates the selected model/current and reserves 24
inner model starts plus 2,400 solver iterations before source access. The actual
development control used fresh generated cases and an authored selected state.
All 24 native solves passed required physical checks, with 395 nonlinear
iterations, 6,440 component calls and 1,975 component-linearization calls. Saved
receipt replay opened no source and ran no solve. A fresh guarded reader verified
public source, receipt and work commitments without private inputs or model
execution. These cases are now recorded as exposed. Protected runtime, full cost,
real task/gain admission, installed/Linux and full Part 5 gates remain open.

[Coupled callback evidence](../../examples/utility/verification-engineering-load-callback-v1/README.md).


The engineering work-cost reader now projects caller-pinned native callback
receipts into existing `CostRecord` entries. It verifies the charged grant,
selection, source binding, policy and score. Missing proof keeps costs unknown;
failed cases retain completed counters without inventing total work. Stable
physical IDs reject duplicate charging. Durable work survives a missing suite
score commit without rescoring. An installed macOS reader outside the checkout
reconstructed the preceding 24-solve counters under an active public-only guard
and rejected modified evidence. No new native solve ran. Generic process cost,
common-report ingestion, CPU/RSS, human/setup costs and all scientific admission
gates remain open. The frozen core/guest sources remain unchanged.

[Installed work-cost evidence](../../examples/utility/verification-engineering-load-costs-v1/README.md).


The current core now integrates pinned engineering work into accounting and
comparative report-inputs v3. A core-only installed reader reconstructs the native
control without example or optional framework imports. Default report bytes match
the preceding installed wheel. Current source has 225 core Python files, with
three existing core files changed and one added. The preserved v5 guest wheel
remains historical evidence and does not qualify this checkout. A fresh full
default regression is running under source pins and sleep inhibition. No new
native model or private source access was needed for this integration.

[Common report integration](../../examples/utility/verification-load-cost-report-v1/README.md).


The successor guest input package now binds 225 current core and 316 declared
Python sources. It preserves v5 non-code package data explicitly, including the
historical blocked task dossiers, and leaves the original v5 inputs unchanged.
A local installed reader reconstructs common reports with examples/frameworks
denied. The offline image context reuses the existing 49-archive cache. A guarded
reader verified a relocated context and refused a changed payload. A fresh bounded
build request is prepared, with no Docker dispatch, new model or private access.
Image dispatch waits for the active full default run. New image/runtime controls,
independent task admission and full Part 5 completion remain open.

[Successor wheel and context](../../examples/utility/verification-guest-wheel-v6/README.md).


A commit-pinned provider dictionary now resolves the generic solar L/C/R alignment
codes. The saved site metadata has L on its 26 listed devices, while the
selected AC metric still lacks its device join. Two bounded listings found only
the existing system JSON in the selected metadata prefix. No observations were
requested. Clock/support/availability, hardware topology, quality, rights and
exposure still block admission. No frozen proposal, dossier or threshold changed.

[Solar source review](part-5-solar-interval-source-review.md).


The current-source default attempt finished with 4,047 passed, 122 skipped and one
bare-python PATH failure. Exactly that case passed with the project interpreter
on child PATH and fresh bytecode lookup. All 11,997 source/configuration pins and
both core/test source sets remained unchanged. This is passing evidence for 4,048
unique non-skipped cases across two executions, not a clean single full-suite run.
The original failed JUnit/log and corrected one-case recheck remain separate.

The v6 base image and explicit-environment derivative now built from the
source-aligned 316-source wheel. One metadata container observed isolated Linux
x86-64 CPython 3.12.13 and the expected identity-module bytes, then cleanup recorded
its exact CID absent. Saved build/derivative/identity records replay with live
operations denied. The derivative and identity proofs also replay after relocation.
No scientific, fitting, scoring, private-label or provider operation ran in this
image increment. The new image remains an unqualified candidate under local
ARM64-hosted emulation. Historical controls were not transferred to it.

The cumulative explicit runtime register now lists 31 creations and 25 starts.
BuildKit internals remain excluded. Older unknown inference and synthetic-label
quantities remain unknown. Current-image resource/inference/lifecycle/private
qualification, independent task admission and the full Part 5 study remain open.

[Default checkpoint](../../examples/utility/verification-current-base-v6/README.md),
[current image evidence](../../examples/utility/verification-guest-image-v6/README.md),
[cumulative register](../../examples/utility/guest-qualification-accounting-v8.json).


Six fresh resource probes now passed against the v6 image. The observations were
OOMKilled at 1 GiB, EAGAIN at process count 16, ENOSPC at 128 MiB, EROFS for root,
ENETUNREACH for network and ENOENT for the unmounted host canary. Each original
container was confirmed absent. No scientific model, fitting, scoring, private
label, provider, image pull or host mount was used. Related tests passed 136 cases.
A guarded reader verified relocated evidence and rejected altered cleanup data.

The cumulative explicit runtime register now records 37 creations and 31 starts.
Older unknown work remains unknown. Historical controls remain bound to their
original image. The v6 inference, lifecycle and private-scoring matrix, independent
physical host qualification, task admission and full Part 5 study remain open.

[Current resource evidence](../../examples/utility/verification-guest-resources-v6/README.md),
[cumulative register](../../examples/utility/guest-qualification-accounting-v9.json).


The v6 image now completed one frozen learned-routing inference and a same-fit
native reference. All four physical checks passed. All seven outputs agreed at
the unchanged tolerances, with maximum absolute difference about 2.13e-14. The
original container was confirmed absent. A fresh guarded reader recovered the
relocated 98-file public proof. A separate reader recomputed saved numerical
parity without model execution. Both used inherited dependencies.

A separate current-source authored fixture required one fit (27 routing rollouts,
2,160 days, cap 120) and one baseline evaluation. The baseline's physical start
quantity remains unknown. A post-fit diagnostic error recovered metadata without
refitting. The old source-bound fixture remains intact and now refuses against
the mismatched wheel before creating output or copying drivers. Neither inference
ran fitting or scoring. All inputs are exposed synthetic development fixtures.

Cumulative explicit runtime accounting now lists 38 creations, 32 starts and two
native references. Older unknown quantities remain unknown. Scoring and parent
confirmation are unattempted for the v6 run. The v6 lifecycle/private matrix,
independent physical host qualification, task admission and Part 5 remain open.

[Current inference evidence](../../examples/utility/verification-guest-inference-v6/README.md),
[cumulative register](../../examples/utility/guest-qualification-accounting-v10.json).


Five fresh v6 lifecycle controls passed: two unstarted cancellations, cancellation
of an actually running guest before input transfer, and two producer-side lost
acknowledgments after real successful CREATE/START responses. Five containers
were created and two started. All original containers were confirmed absent.
Both starts remain charged with unknown model work/time and no observed model
result. Parent reservations remain unfinished. No new fitting or scoring ran.

Three public proof archives passed fresh relocated replay with model imports
blocked. After initialization, guards denied runtime activity, arrays, clocks,
writes and outside content reads. The archive helper's missing source snapshot
was repaired using its already pinned digest, without rerunning any control.
The related tests passed 27 cases. Runtime code did not change.

The cumulative runtime register now lists 43 creations and 34 starts, including
12 charged inference starts and two native references. Five started attempts have
no observed model result. Earlier unknown quantities remain unknown. The v6
owner/watchdog process-loss and private-scoring controls, cancellation during
model computation, independent task admission and Part 5 completion remain open.

[Current lifecycle evidence](../../examples/utility/verification-guest-lifecycle-v6/README.md),
[cumulative register](../../examples/utility/guest-qualification-accounting-v11.json).


Four actual v6 owner/watchdog process-loss controls passed. Three exact owned owner
handles were killed with SIGKILL. A fourth owner killed its own ready watchdog
handle before START. Four containers were created and two started. Every original
container and all three recorded watchdog PIDs were confirmed absent. One result
captured before owner death replayed without a model or container restart. The
other started guest has no model capture. Both lifecycle durations remain unknown.

A 351-file public proof passed fresh relocated replay with model imports blocked
and, after initialization, processes, network, arrays, clocks, writes and outside
content reads denied. A separate changed-owner-PID proof was rejected. The focused
regression passed 73 tests. Runtime code, the existing fit and frozen criteria did
not change. No new fitting or scoring ran.

Cumulative explicit runtime accounting now lists 47 creations and 36 starts,
including 14 charged inference starts and two native references. Known model
inference starts have lower bound eight, with total work still unknown. Six
started attempts have no observed model result. The v6 private-scoring and full
matrix gates, independent physical host qualification, task admission and Part 5
completion remain open. Interruption during model computation is not qualified.

[Current process-loss evidence](../../examples/utility/verification-guest-owner-loss-v6/README.md),
[cumulative register](../../examples/utility/guest-qualification-accounting-v12.json).


A fresh current-v6 composite completed one guest inference and one separate fixed
scorer over exposed authored inputs and synthetic labels. Both original containers
were observed absent. The score matched independent public-vector arithmetic.
Saved confirm/recover reused the original receipt. No new fitting, real observation,
provider call or retry ran. The new two-start reservation completed; older unfinished
or uncertain reservations remain unchanged and charged.

A 103-file public proof excludes the private label blob and root path. A fresh
isolated process outside the checkout used the existing installed 225-source
core-only wheel. Every installed Python payload matched current source. Before
its first suite replay, guards denied new imports, models, execution, network,
clocks, array loading, writes and outside content reads. The original receipt,
score and both stages' costs reconstructed exactly. Dependencies were inherited.
This is native macOS offline-reader evidence, with Linux amd64 inference under
local ARM64 emulation and a separate pinned Linux ARM64 scorer. No runtime or
private-boundary admission follows from this successful synthetic chain.

Cumulative explicit runtime accounting now lists 49 creations and 38 starts,
including 15 charged inference starts and two scoring starts. Known model inference
starts have lower bound nine; total work remains unknown. Six started attempts
lack a model result. The private adverse-case matrix, independent physical host
qualification, task admission and full Part 5 study remain open.

[Current composite evidence](../../examples/utility/verification-guest-composite-v6/README.md),
[cumulative register](../../examples/utility/guest-qualification-accounting-v13.json).


A separate supplied-scenario native recipe now supports up to 24 circuit cases
without requiring a combined worst corner. It chooses the case requiring the
largest source current at the common voltage threshold, retains native coupled
SLSQP/derivatives and checks every supplied case freshly. The passive-circuit
monotonicity reduction and actual diode-option check are documented. The older
combined-corner recipe is unchanged. Exact scientific acceptance stays separate.

An authored 24-case supervised job used 35 inner solves within a 40-call cap.
Twenty-four separately reserved scientific processes then passed all original
checks. The batch retained 25 physical reservations. Saved native/scenario recovery
launched nothing and added no reservations. An isolated installed core-only
base reader verified relocated native and parent receipts, reconstructed costs
and the saved scenario mean, with models/runtime/original roots denied. The
optional environment passed 22 tests. Base/documentation checks passed 33 tests
with eight expected optional skips. No core source changed.

These cases were exposed synthetic development inputs. No proposed final grid
or private generated source was opened. The new recipe is not installed/platform
qualified and is outside the frozen v6 inference image. Task admission, protected
engineering scoring and the actual comparative study remain open.

[Robust native engineering evidence](../../examples/utility/verification-engineering-robust-native-v1/README.md).


The robust supplied-load recipe now has selected-source installed execution
outside the checkout on macOS ARM64, Python 3.12.16 and inherited OpenMDAO 3.41.0.
The wheel contains all 225 core modules, seven domain modules and the exposed
24-case authored fixture. Installed and staged payloads match the wheel. A startup
hook denies original checkout content while allowing inherited dependencies.
This is a diagnostic harness, not a private execution boundary.

One native process used 35 inner solves within a 40-call cap. Twenty-four fresh
scientific processes passed strict checks. The current and mean power matched
checkout results at tolerances frozen before execution. All 25 reservations have
verified stopped receipts. Saved native/scenario recovery launched nothing.
A separate installed core-only base reader verified 385 relocated evidence files,
reconstructed costs and matched the aggregate to all committed scenario scores
with models/runtime/original roots denied after initialization.

The fixture is now bundled and explicitly known exposed in the draft exposure
register. Earlier unknown history and all blocked task admissions remain unchanged.
No independent or proposed final scenario source was opened. Linux, private
engineering scoring, a full release and the actual comparative study remain open.
The frozen v6 inference image and its separate accounting register are unchanged.

[Installed robust engineering evidence](../../examples/utility/verification-engineering-robust-installed-v1/README.md).


A separate coupled-engineering dependency image now contains seven checksum-pinned
PyPI wheels on the exact v6 filesystem. Linux dependency requirements were checked
before acquisition. The bounded stage used 14 GETs, 14,243,480 archive bytes and one
local offline build. The base routing image and project wheel are unchanged.

One isolated Linux amd64 container under local ARM64 emulation evaluated 24 exposed
authored cases at the macOS control's fixed current. All powers/voltages matched
that reference in this observation, and strict voltage/residual checks passed.
Effective memory/PID/CPU/tmpfs and isolation settings were observed. The original
controller nevertheless exited nonzero because its cleanup helper tried to parse
an empty DELETE response as JSON. A separate read-only exact-CID check confirmed
absence. No DELETE, model or container was repeated. The original failure remains.

A caller-pinned stdlib-only reader verified 87 relocated original receipt/source
files, reconstructed public comparisons and rejected altered cleanup semantics.
It imported no models and contacted no runtime. This is metadata/provenance replay,
not independent OS attestation. The new environment still lacks a fixed private
packet worker, sealed-source/container callback integration and the full resource/
interruption matrix. Private admission and the independent study remain open.

Cumulative explicit runtime counts are 50 creations and 39 starts. The known
fixed-model forward-start lower bound is 33, including 24 coupled evaluations
nested in the new container. Total work and older unknowns remain unknown.

[Engineering container stage](../../examples/utility/verification-engineering-container-stage-v1/README.md),
[cumulative register](../../examples/utility/guest-qualification-accounting-v14.json).


A separate coupled-load worker now validates a hash-pinned, strictly bounded
24-case packet and invokes only the existing engineering kernel. A POSIX child
shares one hard-limited 16 KiB file for stdout/stderr. Only score and aggregate
work counts are exported. Invalid or truncated output yields no result. Packet
source-binding hashes do not themselves authorize source access.

Final interoperability checks passed 36 tests, including 24 exposed authored
OpenMDAO solves. An earlier 24-case development check also ran. These 48 model
starts are recorded separately from the unchanged v14 guest accounting scope.
No new containers ran, and no real or proposed confirmation sources were opened.
The frozen v6 wheel and dependency image do not contain this new worker.

Sealed-source access, a registered container entrypoint, versioned runtime/cost
receipts, deadlines, owner-loss cleanup and Linux resource qualification remain
open. Private admission and the full Part 5 study remain incomplete.

[Worker evidence](../../examples/utility/verification-engineering-load-worker-v1/README.md).


The engineering worker now has a fixed Linux stdin entrypoint in a separate
immutable source-overlay image. It verifies its own/source hashes and effective
resource settings before reading the bounded packet. The command binds the
expected packet hash. Child numerical libraries receive only fixed single-thread
settings after the inherited environment is cleared.

One actual isolated Linux amd64 container under local ARM64 emulation completed
24 exposed authored cases. Its 0.27174569156641054 W score matched the saved macOS
reference within the frozen tolerance. The response exported no case identifiers
or forcing arrays. Exact-container cleanup succeeded. A controller binding error
before any daemon call was retained and corrected before the single start.

The copied 67-file proof passed a relocated stdlib replay with model imports,
processes, network, clocks, writes and outside file reads denied. Altered cleanup
semantics were rejected even with a recomputed test manifest. Base and related
checks passed 80 tests with one optional skip. Full lint passed. The full default
suite was not rerun.

The v15 runtime register has 51 creations, 40 starts and a known forward-model
start lower bound of 57, including 48 coupled evaluations nested in two public
control containers. Older unknown work remains unknown. Source authorization,
versioned runtime/cost registration and the worker's resource/owner-loss matrix
remain open. No sealed source was read. Private admission and Part 5 completion
remain false. The frozen v6 routing image and wheel are unchanged.

[Fixed Linux worker evidence](../../examples/utility/verification-engineering-fixed-worker-stage-v1/README.md), [v15 register](../../examples/utility/guest-qualification-accounting-v15.json).


The coupled-container callback and core metadata path now have versioned source,
runtime and work bindings. A registered runtime must pass preflight before the
one authorized source read. The packet binds the original grant, selected model,
source, kernel and current. Offline costs verify the sanitized worker output and
container execution against the committed score. Existing native formats retain
their cost IDs and behavior. Recovery uses the original completion pin and never
refreshes changed work bytes, reopens cases or calls runtime preflight.

The focused suite passed 133 tests and full lint passed. An installed core-only
226-module wheel reproduced CLI report/verify and JSON/Markdown accounting under
model/example import and runtime/file-access guards. The integration runtime was
an authored double. No new physical model or container ran, and the v15 register
is unchanged. These checks do not qualify actual runtime enforcement. A reusable
live owner still needs to connect the new callback to the saved Linux worker.

Current core source now differs from the frozen images: load_costs.py changed and
load_container_costs.py is new. Those image/wheel bytes are preserved. Source and
runtime admission, resource/owner-loss qualification and the independent utility
study remain open. Full cost evidence and Part 5 completion remain false.

[Container callback evidence](../../examples/utility/verification-engineering-container-callback-v1/README.md).


The generated-source coupled callback now uses a reusable explicit local container
owner. A versioned transport pin covers the CLI, Unix endpoint, daemon profile and
helper sources. The owner checks the fixed image before source access, sends the
bounded packet through stdin and requires exact-container cleanup. It does not
save a plaintext packet file. Ordinary lifecycle work shares a 60-second deadline.
Owner-loss supervision remains unqualified.

One actual Linux container under local ARM64 emulation evaluated 24 fresh cases
sealed before authored selection. The fixed 0.05 A current produced a feasible
0.24701566460811183 W aggregate, with 388 solver iterations, 6,328 component calls
and 1,940 component linearizations. A prespecified score-publication fault was
recovered from the original pin with further runtime/source access blocked.
Saved replay added no events. The source is now exposed and excluded from
independent confirmation. This was not optimization or a comparative utility test.

The focused suite passed 115 tests and full lint passed. An installed 226-module
core-only wheel reconstructed the actual report/verify and cost data under guards.
The public archive excludes generated forcing rows and seed. Original execution
receipt joins passed outside the checkout, and altered cleanup was rejected.
The v16 register has 52 creations, 41 starts and a known forward-model-start lower
bound of 81, including 72 coupled evaluations. Older unknown work stays unknown.

Resource/owner-loss qualification, independent host coverage, real task admission
and the independent study remain open. Full cost evidence and private admission
remain false. Frozen image/core snapshots were preserved. The full default suite
was not rerun for this increment.

[Live coupled confirmation evidence](../../examples/utility/verification-engineering-container-live-v1/README.md), [v16 register](../../examples/utility/guest-qualification-accounting-v16.json).


The coupled owner now arms an independent owner-pipe watchdog after container
acknowledgment and before START. Cleanup checks exact original ownership, uses a
separate lock and has no creation, start or model operation. Normal completion
also requires the watchdog's own absence observation.

Two actual SIGKILL controls passed after readiness: unstarted, and running before
input. In both, the watchdog removed the original container and exited. Exact
container and recorded watchdog PID absence were separately observed. No packet
or source was submitted. The focused suite passed 74 tests and full lint passed.
The v17 register has 54 creations, 42 starts and the unchanged known model-start
lower bound of 81. Unknown work remains unknown.

Pre-acknowledgment creation loss, loss during computation, watchdog loss and the
full resource matrix remain unverified for this owner. The earlier live source
confirmation used the preceding owner implementation. These controls establish
no new scientific result or complete runtime qualification. Private admission
and the full Part 5 study remain open.

[Coupled owner-pipe evidence](../../examples/utility/verification-engineering-owner-loss-v1/README.md), [v17 register](../../examples/utility/guest-qualification-accounting-v17.json).


The coupled owner now monitors watchdog liveness before dispatch, during transport
and process-exit waiting, and after client completion. A lost supervisor revokes
result authority. Valid output cannot be published after watchdog loss, and the
owner still cleans the exact original container.

Two actual watchdog SIGKILL controls passed with the owner alive: ready before
START, and running before input. The owners detected loss, refused result
publication, removed the original containers and rejected watchdog completion.
Exact container and recorded watchdog PID absence were separately observed. No
packet or source was submitted, and no model result was observed.

The focused suite passed 77 tests and full lint passed. The v18 register has
56 creations and 43 starts. The known model-start lower bound remains 81, with
72 coupled evaluations. Unknown work stays unknown. Core and frozen image bytes
were preserved. The full default suite was not rerun.

Loss during computation, pre-acknowledgment creation loss and the full resource/
interruption matrix remain unverified. Earlier controls retain their original
helper versions. Runtime/private admission and the independent study remain open.

[Watchdog-loss evidence](../../examples/utility/verification-engineering-watchdog-loss-v1/README.md), [v18 register](../../examples/utility/guest-qualification-accounting-v18.json).


The current supervised coupled owner now has a complete live development
confirmation using a fresh generated source sealed before authored selection.
One source read and one container produced 24 feasible model evaluations at the
fixed 0.05 A current. The aggregate was 0.24921646466397246 W, with 390 solver
iterations, 6,360 component calls and 1,950 component linearizations.

Parent cleanup and normal watchdog disarm were both observed. The watchdog
independently confirmed absence and exited without a second DELETE. A
prespecified score-publication fault was recovered from the original pin with
further source/runtime access blocked. Saved replay added no events. The source
is exposed and excluded from independent confirmation, and its result is not a
utility comparison with earlier generated draws.

A 68-file public archive excludes forcing rows, seed and packet. Receipt joins
passed outside the checkout and rejected altered normal disarm. The existing
226-module installed core reconstructed report/verify and cost data under guards
without another build or installation. Current code/tests match the preceding
77-test checkpoint by hash. No full default suite was rerun.

The v19 register has 57 creations, 44 starts and a known model-start lower bound
of 105, including 96 coupled evaluations. Unknown work stays unknown. Creation
acknowledgment loss, interruption during computation and the full resource matrix
remain unverified. Independent host coverage, real task admission and the
independent study remain open. Full cost evidence and private admission are false.

[Current supervised confirmation](../../examples/utility/verification-engineering-supervised-confirmation-v1/README.md), [v19 register](../../examples/utility/guest-qualification-accounting-v19.json).


The coupled watchdog now arms for the original prospective name before CREATE.
The owner must publish the acknowledged CID and receive a verified watchdog
binding before START. Existing known-CID plans retain their earlier schema.
An intent without an observed object stays unverified.

Four live controls passed their prespecified outcomes: owner loss before CREATE,
owner loss after daemon creation before CID binding, intent-only uncertainty and
normal CID binding/disarm. Two containers were created, none started. Three exact
owner PIDs were killed. Both observed CIDs and all four watchdog PIDs were
separately observed absent. No packet or source was submitted. The intent-only
watcher correctly refused to call current absence a confirmed creation outcome.

The focused suite passed 82 tests and full lint passed. The v20 register records
59 creations, 44 starts and the unchanged known model-start lower bound of 105,
including 96 coupled evaluations. Unknown work stays unknown. Core and frozen
image bytes were preserved, and the full default suite was not rerun.

Unbounded daemon delay, interruption during computation and the full resource
matrix remain unqualified. Earlier scientific controls retain their original
helper versions. Runtime/private admission and the independent study remain open.

[Prospective creation supervision](../../examples/utility/verification-engineering-creation-watchdog-v1/README.md), [v20 register](../../examples/utility/guest-qualification-accounting-v20.json).


Eight fresh fixed diagnostics now passed on the exact coupled image, with owner
code and production catalogues unchanged. Memory reached OOMKilled/exit 137 at
1 GiB, process creation reached EAGAIN at 16 PIDs, and scratch reached ENOSPC at
128 MiB. Root, network and the unmounted host canary returned EROFS, ENETUNREACH
and ENOENT. Two fixed-worker probes also observed the shared 16 KiB stdout/stderr
cap, including SIGXFSZ on overrun. No child bytes became a score.

All eight original containers were confirmed absent. No scientific packet,
source read, model evaluation, image build or installation was involved. These
were fixed diagnostic entrypoints on the exact image, not the scientific scoring
path. Effective CPU quota was observed, but CPU saturation and model RSS were
not measured. Existing source/test checkpoints were preserved.

The v21 register has 67 creations and 52 starts. The known model-start lower bound
remains 105, including 96 coupled evaluations. Older unknown work stays unknown.
Scientific-owner interruption/resource qualification, independent physical host
coverage, task admission and the independent utility study remain open.

[Exact-image resource/output evidence](../../examples/utility/verification-engineering-image-resources-v1/README.md), [v21 register](../../examples/utility/guest-qualification-accounting-v21.json).
