# Part 5 implementation plan: utility across real examples

__Status: proposed implementation, 2026-10-28.__ This plan expands
[Part 5 of the development plan](../development-plan.md) and the
[Part 4 handoff](../part-4-handoff.md). It defines the software, experimental
protocols, evidence and acceptance gates needed to test scientific utility.
Writing this plan does not authorize confirmation runs, provider calls, remote
compute, data purchases or publication. No Part 5 experiment has run for this plan.

Deliver a reproducible comparison of an unchanged baseline, conventional numerical
workflows, a single agent and the multi-agent workflow on independent real tasks.
Measure quality, feasibility, reliability, human effort and total cost. A useful
outcome can be a finding that agents add cost without improving the result.
Implementation completion and demonstrated scientific utility are separate decisions.

## 1. Starting state and implementation boundaries

Work in the existing `agentic-architecture` worktree. Its planning-time HEAD is
`b393726`; substantial Part 3 and Part 4 implementation is uncommitted. Preserve
those changes and inventory the actual source, configuration and dependency locks.
HEAD alone does not identify the implementation available to Part 5. The
[Part 3 audit](../reviews/part-3-final-audit.md) and
[Part 4 audit](../reviews/part-4-completion-audit.md) describe prior qualification,
not fresh validation of the Part 5 changes.

The current sources provide the following starting points and gaps:

| Existing interface | Reuse and Part 5 work |
| --- | --- |
| `campaign/spec.py`, `records.py`, `controller.py` | Reuse immutable campaigns, scientific acceptance, selection freeze and physical-attempt accounting. Current `eligibility-v1` confirmation checks the frozen selection once; it does not test comparative scientific utility. |
| `campaign/spec.py:AcceptanceSpec` and `CalibrationSpec` | Current metrics are prediction metrics and calibration requires deterministic studies. Add a versioned path for engineering objectives and scenario evaluation, preserving old contracts. Do not call modeled energy an RMSE against fabricated observations. |
| `campaign/studies.py`, `optimization/controller.py`, `ledger.py` | Keep child studies, immutable identity, append-only observations and pending-result reconciliation authoritative. |
| `adapters/contracts.py` | Reuse preparation, validation, training, execution, inspection and cleanup. Training has artifact/cost records, but this does not establish a qualified learned-model workflow. |
| `agents/batch.py`, `batch_science.py`, `batch_native.py` | Reuse permanent reservations and observed physical starts. Existing batches select one host and allow at most 32 cases. A larger suite needs a parent manifest and bounded child batches, not an unrecorded reset of limits. |
| `examples/agent_campaign/comparison_runtime.py`, `native_comparison.py` | Reuse the route comparison and preparation patterns. Extract general facilities without changing frozen Leaf River protocols or their original evidence. |
| `agents/report.py`, `integrations/evidence.py` | Reuse offline readers and digest verification. Generalize reporting without requiring model imports, provider access or private data. |
| `adapters/openmdao.py`, `bmi.py`, interoperability examples | Reuse qualified interface subsets. Keep a coupled solver intact. New variables, time support, training or execution modes require their own qualification. |

Keep the public replacement loop and previous BO benchmarks unchanged. A new suite
is not a replacement run for a failed frozen BO gate. Keep the physical graph,
agent tasks, experiment lineage and suite comparison matrix as distinct records.
There is no web-app deliverable in Part 5.

## 2. Scientific scope and task admission

Create an exposure register before choosing confirmation data. It must record
source/site, dates or scenarios, source hashes, known previous uses, access dates,
people or workers exposed, and whether exposure included labels, diagnostics or
aggregate results. Use `unknown_exposure` when history cannot be established.
Availability in a cache and absence from the latest script do not prove independence.

Known exclusions from independent confirmation include the Leaf River periods
used in earlier development, solar June 1-7, 2018, and the historical 2018/2019
open-chain evaluation periods. The Part 4 circuit and scalar reservoir remain
integration fixtures. Read the handoff for exact scope before adding exclusions.

Admit four task families. Freeze one concrete task in each family after checking
metadata, access, scientific meaning and estimated execution cost. Unavailable
families remain blocked and reduce the supported claim; synthetic substitutions
cannot satisfy real-task coverage.

| Task family | Required implementation and comparison | Confirmation evidence and exclusions |
| --- | --- | --- |
| Observed hydrology | Component replacement and inner calibration, then one simple learned alternative if training data support it. Reuse the current chain only after making hidden fluxes/storage accounting explicit, or adapt another observed system. | Unseen chronological period or new basin with documented exposure. Primary prediction loss plus bias, water balance, nonnegative states, runtime and training cost. Learned alternatives without required flux/state outputs cannot pass a conservation gate. |
| Measured solar | Preserve the measured-POA pvlib/OEDI task and equipment assumptions. Compare frozen thermal/electrical alternatives and permitted calibration. Expand the supplied pool only through reviewed implementations. | Untouched measured AC period or site, acquisition manifest, timestamp alignment, missingness/quality masks, nighttime and physical-limit checks. Use input variables available at the stated prediction time. Measured contemporaneous POA supports conditional AC prediction, not an advance weather forecast. |
| Coupled engineering | Select a real OpenMDAO design problem with a documented decision, meaningful constraints and accessible inputs. The existing circuit can support a newly frozen design/scenario question; its old target fit alone is insufficient. Preserve the native solver, derivatives and conventional driver. | Frozen design specifications and unseen operating/load scenarios. Convergence, constitutive residuals, feasibility and objective under the model. No empirical predictive claim without observations. If the selected case needs arrays or unsupported units, qualify those semantics first. |
| Wind or hybrid system | Choose one of the existing wind layout or HOPP dispatch chains based on executable dependencies and a defined decision. Freeze hardware, allowed layout/dispatch changes and scenario information. | Independent weather/load/price scenarios with spacing, power, energy, battery or dispatch constraints as appropriate. Keep modeled energy/revenue separate from measured predictive skill. A finer discretization alone is a numerical check, not independent scenario confirmation. |

Each task dossier must contain a falsifiable question, baseline, candidate pool,
parameter domains, native/conventional workflow, development and confirmation
partitions, primary outcome and units, constraints, minimum useful gain, secondary
tolerances, data rights, source closure, environment, resource estimate and claim
limits. It must also state whether the task tests new-period, new-site or new-task
transfer. Those are different claims.

For time-dependent tasks, freeze warmup, state initialization, causal carryover,
seasonal coverage, gap handling and evaluation masks. Fit preprocessing, feature
selection and hyperparameters using fitting/selection data only. Include embargoes
where feature windows or overlapping events would otherwise bridge partitions.
A trusted data custodian may run predeclared quality checks, but may not choose
periods based on candidate performance. Record exclusions before scoring.

__Admission gate:__ all four dossiers have a concrete question and an auditable
partition. Missing inputs, rights, physics checks or untouched evidence produce a
named blocker. Do not fill missing thresholds after looking at confirmation results.

## 3. Comparison design

### Shared candidate pool

The primary comparison uses these routes on the same frozen task:

| Route | Permitted decisions | Required accounting |
| --- | --- | --- |
| Unchanged baseline | No model selection, fitting or repairs beyond the frozen task preparation. | Preparation and inference cost; separate reusable reference from measured repeated execution. |
| Conventional workflow | Declared supplied alternatives and parameters using the frozen numerical selection recipe. Include the native engineering driver where applicable. | All starts, calibration, derivatives, solver work and failures. |
| Single agent | Same scientific tools, candidate pool, bounds, data grants and acceptance rules. | All prompts, research, calls, repairs and scientific work. |
| Multi-agent workflow | The same choices through the existing bounded role contracts. | All role calls and coordination, including rejected handoffs and reviewer work. |

Select the conventional recipe on development evidence before confirmation. Use
Sobol as a reproducible reference and the admitted Optuna or native driver when
justified by the task. Do not pick the conventional comparator retrospectively to
make an agent look stronger. Preserve derivative access for a native driver and
record that capability instead of artificially weakening it. Equal-information
comparisons concern available evidence, not forcing every method to use it identically.

Match starting points, candidate implementations, search bounds, data, scientific
checks and hardware conditions. Agent routes share model/version, tool permissions,
research corpus and aggregate host allowances. Give each route fresh journals and
workspaces. No route sees another route's diagnostics or proposal history. Randomize
route order within paired repetition blocks and record cache and machine-load policy.

The conventional, single-agent and multi-agent runs are paired by task, repetition,
scenario and budget regime. A provider seed is not a guarantee of repeatable text.
Record exact prompts, resolved model and observed outputs. The unchanged deterministic
baseline need not be refitted or rerun to manufacture independent repetitions.

### Candidate discovery and role removal

Keep discovery separate from the shared-pool comparison. Initially admit supplied,
trusted implementations. A discovery study may expand candidates only after generated
code admission, isolation, training and scientific checks cover the proposed change.
The current live generated-code path is not qualified for arbitrary new models.

Freeze the discovery information budget and search corpus, retain sources and failed
proposals, and charge research, implementation, admission and calibration. Then freeze
the resulting candidate union and run all applicable routes over that shared pool.
This separates discovery value from selection and optimization value. The pool replay
uses development/selection evidence until all confirmation selections are frozen.
It must not use confirmation feedback to repair candidates or expand the pool.

Add three role-removal routes: no investigator, no implementer and no agent reviewer.
Freeze the mechanical replacement for each omitted role, such as the supplied candidate
catalogue, trusted implementation lookup or mandatory coded checks. Never remove
scientific acceptance or the controller's budget rules. Compare each with the full
workflow under the same aggregate allowance. Record unused allowance and changes in
task sequence. Do not add extra calls to the remaining roles without predeclaring them.

Use an expert workflow where practical. Freeze its allowed information and intervention
set, record active minutes and decisions, and distinguish measured effort from estimates.
An unavailable expert arm is explicitly `not_attempted`, not a zero-effort baseline.

### Repetitions and budget regimes

Propose ten paired repetitions for each adaptive route and each budget regime on each
admitted task. This is a planning default, not a statistical power claim. Use development
variability and the minimum useful effect to freeze the final count and uncertainty
analysis before confirmation access. A smaller affordable study can be exploratory;
wide uncertainty cannot be reclassified as evidence of equivalence.

Run two distinct regimes:

1. __Fixed evaluation budget.__ Match the cap on physical scientific executions,
   including default candidates, fitting, rejected attempts and reevaluation. Keep
   separate caps for training and native inner work. Compare total realized cost as
   an outcome. Equal outer trial counts alone are not a fair computational comparison.
2. __Fixed total cost.__ Freeze a common active wall-time cap on equivalent local
   resources and explicit caps for money, host invocations, training and scientific
   starts. Reserve worst-case bounded work before dispatch. Report resource quantities
   separately. Claim monetary matching only when prices and usage are measurable or
   conservatively bounded; unknown usage prevents a matched-money conclusion.

Freeze actual numeric caps from development profiling. Every executable suite must
contain numbers, units and enforcement modes, including confirmation reserves.
No null or placeholder cap may authorize work. Provider token usage that cannot be
bounded remains an observed quantity; do not claim strict token enforcement.

At ten repetitions, four tasks, two regimes and three adaptive routes, the primary
matrix has 240 adaptive cells, plus baseline reference/confirmation work. Full
three-role ablations add 240 cells if applied to all four tasks. Discovery, expert,
second-host qualification and failure fixtures require separate rows and allowances.
Generate the complete matrix and sum worst-case starts, host calls, duration and
storage before requesting run authority. A smaller, preselected ablation subset is
acceptable only with the corresponding task-specific role-retention claim.

## 4. Data custody, selection freeze and comparative confirmation

Implement a suite-level confirmation protocol rather than broadening the meaning of
`eligibility-v1`. Preserve its reader and original outcomes. Proposed new records and
commands below are design targets, not existing public APIs.

Use the following sequence:

1. Prepare development data and private confirmation artifacts. Freeze their hashes,
   masks, exposure register, scoring code and access grants. The public manifest holds
   references and metadata, not labels, scores or reversible label summaries.
2. Complete every primary and predeclared ablation/discovery selection. Seal each
   candidate's source, parameters, trained artifact, initialization, campaign decision
   and selection-data digest. No selected object may remain mutable.
3. Commit a suite selection manifest naming every planned cell, including failures,
   no-selection outcomes and exhausted budgets. A missing cell cannot be silently dropped.
4. Verify source/environment identity, absence of unresolved selection work, remaining
   confirmation capacity and selection completeness before opening confirmation access.
5. Evaluate only the baseline and frozen selections through a trusted scorer. Score
   duplicates once only when the full model/data/state identity is identical and the
   protocol permits caching. Retain every cell's reference and actual versus allocated
   cost. A stochastic output requires its declared repetition and seed identity.
6. Commit comparative metrics, physical checks, uncertainty and cost evidence. Freeze
   the report and close the suite. Failed confirmation never reopens selection.

A suite state machine should include `draft`, `prepared`, `protocol_frozen`,
`selecting`, `selections_frozen`, `confirming`, `complete` and `blocked`. State names
are proposed suite states, not additions to the scientific result enum. Keep record
validity, execution completion, eligibility and utility verdict separate.

The existing campaign bundle and trusted-process execution do not alone provide a
holdout security boundary. Keep private labels out of worker bundles, prompts,
artifact grants, logs and reports. Test OS/container permissions where generated code
or another untrusted worker is involved. Supply permitted forcing to model execution
and labels only to the trusted scorer. Validate both direct and indirect paths,
including caches, inherited descriptors, exception text and report reconstruction.

Holdout opening and score publication need their own append-only access receipts.
Crash tests must cover access-intent commit, score creation and acknowledgement. Reuse
verified scores after interruption. An uncertain scoring attempt retains its charge
and access history; it must not silently start a new scientific attempt. Repeated reads
of committed evidence are permitted and perform no new scoring or selection.

If anyone uses confirmation feedback to change candidates, masks, thresholds or
analysis, retain the original failure and mark the affected evidence exposed. Further
confirmation requires a newly frozen task or untouched evidence. Protocol amendments
before access create a successor identity and preserve the previous manifest.

## 5. Implementation structure and compatibility

Add a small `src/autoengineering/utility/` package above existing campaign and agent
services. Do not make it another scientific runner or another writable copy of their
ledgers. Use immutable references to authoritative records and one suite writer for
case allocation, selection manifests and reporting state.

| Proposed module or record | Responsibility |
| --- | --- |
| `contracts.py`: `UtilitySuiteSpec`, `TaskSpec`, `RouteSpec`, `ComparisonCell` | Strict immutable schema, ordered matrix, task/outcome identities, pairing, budgets, required capabilities and protocol digests. |
| `exposure.py`: `ExposureRecord`, `PartitionManifest` | Data/scenario provenance, known exposure, split boundaries, preprocessing and access policy. |
| `store.py` and `controller.py` | Append-only suite transitions, child references, reservations, single-writer locking, cancellation and recovery. |
| `preparation.py` | Resolve trusted registrations, check inputs/capabilities, estimate the complete matrix and create a reviewable frozen preparation without dispatch. |
| `costs.py`: `CostRecord` | Join physical attempts, host journals, training, solver counters and human logs without double charging shared work. |
| `confirmation.py`: `SelectionManifest`, `ConfirmationReceipt` | Seal selections, enforce suite barrier, dispatch trusted scoring and preserve access/recovery receipts. |
| `analysis.py` | Paired differences, feasibility/reliability rates, uncertainty and preregistered utility verdicts. |
| `report.py`, `command.py` | Offline JSON/Markdown reports, provenance checks and proposed CLI entry points. |

Names may be refined during implementation, but ownership and evidence meanings are
fixed by this plan. Reject duplicate/unknown fields, nonfinite values, ambiguous units,
symlink/traversal paths and conflicting IDs. Bind sources, locks, scoring functions,
seeds, candidate order, prompts, provider/host profiles, budgets and analysis policy
into the relevant identity. A change starts a new study/suite rather than resuming an
old one under changed assumptions.

Reuse existing bounded child batches. Add a parent reservation across those batches
so splitting a matrix cannot multiply allowances. Host A and host B may use separate
batches under the same parent. Logical cells, physical attempts and remote request IDs
must remain distinct. Report missing/unknown cost rather than treating it as zero.

Add a versioned registered outcome/check contract for engineering scalars and scenario
aggregates. It must specify name, units, direction, finite-output requirements,
aggregation, feasibility checks and evaluator identity. Keep legacy `AcceptanceSpec`
and child-study deserialization exact. Use registered code, not YAML expressions.
Engineering objectives enter selection through the same authoritative acceptance path.

If training is admitted, persist preprocessing and trained artifacts with data/source
hashes, fitting seed, duration and cost. Test that inference reuses the frozen artifact
without retraining. Do not enable noisy-study semantics implicitly: deterministic
seeded training is one profile; stochastic training/replicated scoring requires an
explicit new profile and uncertainty contract.

Proposed CLI surface: `autoengineering utility validate`, `prepare`, `run`, `resume`,
`status`, `freeze`, `confirm`, `cancel`, `report` and `verify`. Final argument spelling
belongs in implementation tests and docs. `prepare` must start no model or provider.
`run` must not automatically expose confirmation labels. `status`, `report` and `verify`
must operate offline without executable factories or optional framework imports.
Existing `campaign` and `agents` commands remain usable independently.

## 6. Outcomes, cost and decision rules

Freeze one primary scientific outcome for each task and a primary contrast of full
multi-agent versus conventional workflow. Single-agent versus conventional and full
versus single-agent are prespecified secondary contrasts. Role removals address role
retention, not a new opportunity to choose the strongest post hoc comparison.

For a minimized loss, define paired scientific gain as comparator loss minus route
loss. For a maximized outcome, use route outcome minus comparator outcome. Persist
raw values and units before normalization. Freeze minimum meaningful gain, permitted
secondary degradation, feasibility requirements and an uncertainty rule in each dossier.
Do not average RMSE, energy and revenue into an unexplained global score.

Report at least:

- Primary and secondary outcomes, constraint residuals, feasible-selection rate and
  unchanged-baseline retention, with denominators including every assigned cell.
- Execution reliability, invalid proposals, retries, timeouts, cancellations, unresolved
  work, no eligible model and insufficient-data outcomes.
- Scientific starts, inner solves, iterations, derivatives, component calls and training
  work, retaining the differing units and cache effects.
- Preparation, research, admission, calibration, training, selection, confirmation and
  reporting durations; active and elapsed wall time; CPU/GPU time and sampled RSS where
  measured; provider usage, spend and unknown quantities.
- Human setup, review, repair and intervention minutes, distinguishing common task setup,
  route-specific work, one-time integration effort and repeated campaign operation.

Keep the sum of exclusive cost categories reconciled to physical receipts. Inclusive
wall-time totals must not add overlapping phases. Show both first-use cost and repeated
use with any amortization horizon fixed in advance. Shared baseline costs need one
physical receipt and explicit allocation, not duplicated starts or free work.

Use paired analysis on the preregistered repetition blocks. Report distributions and
intervals, not the strongest run. Do not treat time samples, repeated calls or many seeds
on one basin as independent real tasks. For time-series error uncertainty, freeze a
block-resampling or other dependence-aware method using development data. Keep that
uncertainty distinct from variation across search/agent runs. Report scenario-level
uncertainty separately from algorithm randomness.

Use the predeclared confidence level, resampling seed and multiplicity policy. A default
95% paired interval is a starting design choice; the final protocol must specify the
exact procedure and treatment of small samples before scoring. Failure rates and
conditional scientific effects are separate estimands: compare numerical quality on
valid paired outcomes, show how many pairs were lost, and report all-route successful
feasible-selection rates on the full matrix. Do not impute failed objectives as large
penalties or zero. Bound conclusions when missing pairs could change them.

Runs stopped by budget remain capped, even if no target was reached. Time-to-target
summaries retain censoring and the number that never reached the target. Incomplete
physical evidence prevents a complete-cost verdict.

Use these verdicts independently of software gate status:

| Verdict | Required evidence |
| --- | --- |
| Scientific gain supported | Gain exceeds the frozen useful-effect rule, required physical checks pass and uncertainty supports the stated task-specific claim. |
| Efficiency gain supported | Frozen scientific noninferiority and feasibility requirements pass, and total cost or measured human effort improves by the declared margin. |
| No useful gain demonstrated | Valid completed evidence does not meet a useful-gain rule. This does not by itself establish equivalence. |
| Inconclusive | Evidence is too sparse, intervals too wide, or cost/exposure unresolved. |
| Failed confirmation | Frozen scientific or feasibility requirements fail. Preserve the selection and failed result. |
| Not attempted / blocked | No confirmation evidence, with the missing prerequisite named. |

Retain an extra agent role only when its paired ablation supports the predeclared
quality, reliability or effort benefit at acceptable added cost. If no such evidence
exists, recommend the simpler route. Four heterogeneous tasks support bounded case
findings; a general superiority claim needs new tasks and broader replication.

## 7. Reviewable implementation increments

Implement in order. Each increment produces code where specified, tests, a source
inventory and a short progress record. Offline engineering and development checks
are separate from the frozen confirmation matrix.

### 5.1 Inventory and task dossiers

Create `docs/reviews/part-5-progress.md`, a source inventory, exposure register and
four draft task dossiers under `examples/utility/tasks/`. Record Part 3/4 limits,
current environment availability and unavailable inputs. Inspect metadata without
opening proposed confirmation labels. Select the wind or hybrid branch and the
concrete OpenMDAO decision. Profile only previously exposed development fixtures.

__Gate G1:__ four admitted task definitions, or an explicit incomplete suite with
named blockers. All known prior exposure is preserved. Numerical caps, thresholds
and final repetition counts have a documented route to freezing before execution.

### 5.2 Strict suite records and durable accounting

Implement contracts, validation, matrix expansion, suite store, parent budgets and
child mapping. Build tiny authored fixtures around existing campaign and batch
interfaces. Add `tests/test_utility_contracts.py`, `test_utility_store.py` and
`test_utility_costs.py` covering mutation, duplicate keys, identity changes, boundary
budgets, concurrent writers and missing/duplicate physical receipts.

__Gate G2:__ matrix totals reconcile exactly; resumed cells cannot obtain fresh
allowances; rejected configurations start no work; old campaign/optimizer records
still replay unchanged. More than 32 cells dispatch through bounded child batches
without bypassing the suite budget.

### 5.3 Outcome semantics, training and task adapters

Implement the versioned engineering outcome path and the four trusted task adapters.
Reuse current wrappers where their capability profiles match. Add the simple learned
hydrology candidate only if its data, causal features, physics outputs and training
budget pass admission. Otherwise demonstrate and retain `insufficient_data` or a
named unsupported capability.

For each task, compare direct execution with wrapped execution on development inputs.
Test units, time/state semantics, convergence, finite outputs, required physical checks,
immutable baselines and cleanup. Check native derivative/inner-solve accounting and
training artifact reuse. Scope new dependencies to optional environments.

__Gate G3:__ every admitted task has direct/wrapped parity at frozen tolerances, a
working conventional baseline and a scientifically interpretable objective. Unsupported
profiles stop before model launch. Attractive but physically invalid candidates are vetoed.

### 5.4 Shared-pool routes, ablations and development rehearsal

Implement route builders and trusted runners in `utility/` and task preparation in
`examples/utility/`. Keep the old Leaf River comparison files and pins intact. Use
scripted workers for offline behavior tests, then qualify any live route separately.
Persist paired seeds, route order and model/host configuration.

Test no suitable candidate, unchanged baseline, missing observations, simpler-model
selection, invalid physics, malformed handoff and budget exhaustion. Use authored
fixtures for deterministic expected outcomes; do not represent these as observed
scientific utility. Rehearse complete task paths on development data and freeze the
conventional recipe, ablation subset, numeric budgets and analysis procedure.

__Gate G4:__ all routes receive equivalent grants and choices, aggregate costs reconcile,
and the complete matrix can pause/resume without duplicate scientific or host starts.
The rehearsal produces a concrete execution proposal with every planned cell and cap.

### 5.5 Private confirmation and failure recovery

Implement selection sealing, access receipts, comparative scorer and offline evidence
reconstruction. Add `tests/test_utility_confirmation.py`, `test_utility_permissions.py`
and `test_utility_recovery.py`. Use synthetic private labels for security tests.

Inject failures before/after reservation, physical launch, result commit, suite commit,
selection freeze, confirmation access, score commit and acknowledgement. Cover tampered
models, altered data, missing artifacts, stale grants, corrupt projections, uncertain
cost, cancellation and owner loss. Exercise leaked-label canaries through prompts,
errors, cache paths and reports. Report-only verification must start no processes that
execute models and must contact no network service.

__Gate G5:__ confirmation cannot run before the complete selection barrier; it cannot
reopen selection; verified saved results replay without rescoring; uncertain attempts
block automatic retries and retain charges. No worker can obtain private labels through
the admitted execution boundary. A passing eligibility check alone cannot become a
comparative utility verdict.

### 5.6 Platform, host and installed-package qualification

Run the required development tests in the base and applicable optional environments.
Build a wheel and exercise preparation, development smoke, resume, report and verification
outside the checkout. Include minimal synthetic fixtures and acquisition manifests without
bundling restricted observations, credentials or bulky private archives.

Qualify macOS ARM64 and Linux x86-64 separately. Use actual execution for platform claims;
resolved dependencies are insufficient. A missing Linux runtime leaves Linux explicitly
unverified and the portable-release gate open. Remote-machine use requires its own authority.

Check a second actual host implementation against the same role/tool contract, permissions,
accounting, malformed-output and interruption cases. A second model behind the same host or a
fake host does not satisfy this requirement. Bind the selected host/version and measured
limitations. Use development tasks for this check; a second-host utility claim requires a
separately frozen comparison. Obtain explicit authority for live calls after preparing their
exact conformance matrix and caps.

__Gate G6:__ installed offline readers work without optional runtimes; qualified platforms
and hosts have actual evidence. Preserve macOS-only or one-host limits if the other checks
remain blocked. Core Part 5 scientific evidence may be reported within those limits, but
cross-platform/second-host release completion may not be claimed.

### 5.7 Frozen execution and independent confirmation

Prepare `examples/utility/protocol.json`, task manifests, the full cell matrix, analysis
specification and expected cost totals. Record clean source provenance according to the
new protocol before execution. Earlier dirty-worktree development remains traceable through
its source inventories. Do not discard it to manufacture clean provenance.

Present the concrete run package for any required paid/live/remote execution authority.
Past Part 3 budgets do not carry into this suite. Execute selection within the frozen caps,
seal all selections, then run confirmation only with the required data and execution authority.
Show progress by task, route and repetition, including spent/reserved/unknown work.

__Gate G7:__ every planned cell has evidence or an explicit terminal/nonattempted outcome,
all selected artifacts are immutable, and independent confirmation is auditable. Failed
and inconclusive outcomes satisfy honest evidence delivery but not a positive utility claim.
A missing required family means the full Part 5 real-example suite remains incomplete.

### 5.8 Analysis, reports and final audit

Implement offline analysis and report rendering from pinned receipts. Save machine-readable
outcomes/cost tables, task reports, paired difference plots, constraint/failure summaries,
quality-versus-total-cost plots and role-ablation results. Add time-series/residual or
scenario views where they clarify a task. Export the underlying numeric data with each plot.
Use light publication styling, accessible earth tones and readable labels.

Create `docs/utility.md`, `docs/reviews/part-5-completion-audit.md` and a handoff stating
which tasks, platforms, hosts and claims are supported. Update the development plan,
documentation/example indexes and current scope statements only to reflect executed evidence.
Record whether each extra role should be retained. Keep raw adverse results and all failed
run directories. No success condition requires agents to win.

__Gate G8:__ a fresh installed reader reconstructs all reported numbers, denominators,
verdicts and figure data from pinned evidence without models, providers or holdout access.
The audit maps every requirement to executed evidence, blocked scope or justified deferral.
Publication, release and push remain separate actions.

## 8. Verification and stop conditions

The planned focused tests are the utility contract, store, cost, confirmation, permissions,
recovery, analysis and CLI modules plus task-specific adapter tests. Test paired alignment,
known analytic intervals, missing pairs, duplicate score references, cost allocation,
censored runs and prevention of aggregate claims from incompatible units. Include output
contract checks for both JSON and Markdown and installed-package resource discovery.

Run existing checks when their implementation is affected:

```sh
pixi run lint
pixi run test
pixi run -e bayes test-bayes
pixi run -e interoperability test-interoperability
```

Run the chosen wind/hybrid environment and source-specific tests as needed. Do not rerun
frozen benchmark matrices to qualify unrelated suite infrastructure. Record exact commands,
exit status, environment and source identity, including skips and unrun checks.

Stop or block the affected cell when required data are unavailable, exposure is uncertain,
scientific checks cannot be evaluated, the runtime is unqualified, budget cannot cover the
next reserved operation, or execution/accounting remains uncertain. Stop confirmation
admission if any required selection is mutable or the protocol changed. Preserve completed
independent work and the original evidence in every case.

The final audit must answer separately:

1. Is the software implemented and verified for the stated environment?
2. Was the full frozen experiment executed with valid data custody and accounting?
3. Which scientific, cost or human-effort gains are supported, absent or inconclusive?
4. Do role-removal comparisons justify each extra agent role?
5. Which platform, host, data and generalization limits remain?

At the time of this plan, G1-G8 are not attempted. The next authorized work is to review
this implementation scope; no numeric experiment result or confirmation success is implied.
