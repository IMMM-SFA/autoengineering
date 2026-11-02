# Part 4 implementation plan: scientific interoperability

__Status: proposed implementation, 2026-10-27.__ This document expands
[Part 4 of the development plan](../development-plan.md). It specifies integrations,
implementation increments and acceptance evidence. It does not implement adapters, select a
winning optimizer, authorize live agent runs, or establish scientific utility.

Deliver a reusable BMI adapter, one external search-policy integration selected through an
Ax/Optuna comparison, a solar workflow, and an OpenMDAO coupled engineering example. Investigate
all six named systems. Admit DAKOTA and Ray only when a recorded modeling need justifies them.
Each admitted integration must match direct execution, preserve recovery and failure meaning,
and either demonstrate a measured benefit or remove a documented integration burden.

## 1. Starting point and boundaries

The implementation target is the existing `agentic-architecture` worktree. At planning time its
HEAD is `b393726`, with substantial uncommitted Part 3 implementation and documentation. The
[Part 3 final audit](../reviews/part-3-final-audit.md) records completion for its bounded macOS
ARM64 delivery. That audit is prior evidence, not a fresh qualification of Part 4. Before
implementation, inventory and hash the actual working sources and preserve all unrelated edits.
Do not reset the worktree to HEAD or assume its commit contains the delivered Part 3 code.

Current interfaces provide these starting points:

| Existing code | Reuse and required change |
| --- | --- |
| `adapters/contracts.py` | `ModelAdapter` preparation, validation, training, execution, inspection and cleanup. Add implementations without inventing a second lifecycle. |
| `campaign/records.py` | Immutable model/data/port identities. Current ports support scalars or daily time series, with explicit time semantics. Broader time/grid support requires versioned contracts. |
| `examples/local_models/bmi_chain.py` | A working example driver with scalar float64 exchange, equal time units, start zero and unit steps. Extract behavior with parity tests before generalizing it. |
| `optimization/backend.py` | `OptimizerBackend.suggest`, `recommend`, diagnostics and identity/state records. External ask/tell APIs need a bridge to this protocol. |
| `optimization/controller.py` and `ledger.py` | Authoritative action/result commits, budgets and compatible recovery. Preserve their ownership. |
| `campaign/studies.py` | Child-study identity, fitting evaluation, physical attempt accounting and pending-result reconciliation. Extend explicitly for the selected policy. |
| `agents/` and trusted adapter registration | Workers request existing operations. They do not install frameworks, register arbitrary factories or write scientific results. |

Read [the optimization guide](../optimization.md), [campaign guide](../campaigns.md) and
[agent guide](../agents.md) before changing these boundaries. The public `optimize` interface
currently admits `random`, `sobol` and `botorch`; this plan does not claim any new policy is
already public. The old replacement loop and frozen BO protocols retain their current behavior.

Part 4 is local scientific integration work. General distributed infrastructure, new agent
hosts, unrestricted spatial coupling, automatic dependency installation and new independent
confirmation studies remain outside its required delivery. Preserve the Part 3 data-exposure
history and `confirmation_not_attempted` outcome. No previously inspected data become a holdout.

## 2. Integration decisions and primary sources

The following official documentation was inspected on 2026-10-27. Documentation versions are
not dependency pins. Implementation must record the exact tested package/binary versions,
licenses, supported APIs and resolved environments before claiming compatibility.

| System | Source-supported capability | Planned disposition and decision gate |
| --- | --- | --- |
| BMI / PyMT | [BMI](https://bmi.csdms.io/en/stable/) defines model control, variables, time and grids. [PyMT](https://pymt.readthedocs.io/en/latest/) supplies coupling tools around BMI. | Required BMI subset first. Evaluate PyMT separately for a concrete time/grid exchange need; a BMI adapter alone does not establish PyMT compatibility. |
| OpenMDAO | [Core features](https://openmdao.org/newdocs/versions/latest/features/core_features/index.html) cover components, solvers, derivatives, scaling and recording. | Required whole-problem evaluator and direct/native-driver comparison on a coupled example. |
| Ax | [Experiment and trials](https://ax.dev/docs/experiment/) separates experiments, trials and generation. Its internal components page warns about API changes. | Prototype through a supported public client API in a pinned version. Do not build against internals merely because the conceptual documentation describes them. |
| Optuna | [Ask-and-tell tutorial](https://optuna.readthedocs.io/en/stable/tutorial/20_recipes/009_ask_and_tell.html) supports externally managed evaluation. | Prototype serial suggestions and observations, including conditional model-family choices. Compare against Ax before support selection. |
| DAKOTA | [Simulation interfaces](https://snl-dakota.github.io/docs/latest_release/users/usingdakota/inputfile/interfaces.html) connect parameter requests to external simulation responses. | Investigate sensitivity/UQ requirements. Implement only for a named decision that current tools do not adequately support. |
| Ray Tune | [Tune documentation](https://docs.ray.io/en/latest/tune/index.html) describes trial execution, resources and tuning workflows. | Investigate scheduling overhead and ownership. Implement only after measuring a sequential bottleneck and proving controller-owned reservations and recovery. |

Save one decision record covering all six systems. For each, record adopted, deferred, rejected
or blocked; evidence paths; license/dependency findings; integration burden; and a concrete
revisit trigger. Neither Ax nor Optuna is preselected. If both fail mandatory contracts, retain
the failed prototypes and mark the external-optimizer deliverable blocked.

## 3. Ownership and durable contracts

Keep physical models, agent tasks, framework trials and scientific experiments as separate
objects connected by explicit identifiers.

| Responsibility | Owner | External framework permission |
| --- | --- | --- |
| Campaign acceptance, data grants and final selection | Campaign controller | Supply evidence only |
| Study/action identity and immutable configuration | Optimization controller | Receive a mapped external trial ID |
| Search suggestions | Selected policy bridge | Propose a configuration inside the frozen space |
| Physical start, capacity reservation and retry authorization | Campaign/execution service | Execute only a reserved attempt |
| Numerical methods, coupled solves and derivatives | Registered model implementation | Run inside its qualified execution boundary |
| Result commit and recommendation | Autoengineering ledger/controller | Receive a projection of committed outcomes |
| Trial cache, framework checkpoint or recorder | Optional integration | Preserve as digest-bound evidence, never a competing scientific authority |

Add proposed immutable records in `src/autoengineering/integrations/contracts.py`:

- `IntegrationSpec`: schema version, framework/version, adapter or policy ID, supported mode,
  configuration digest, dependency/environment identity and capability requirements.
- `ExternalTrialLink`: campaign/study/action IDs, external experiment/trial ID, proposal digest,
  attempt IDs, observation digest, checkpoint reference and synchronization state.
- `IntegrationReceipt`: implementation/source identity, platform, direct-reference evidence,
  tolerance definition, capability checks, limitations and qualification result.

Names are proposed. Reuse existing records where their meaning matches. Reject unknown fields,
duplicate keys, nonfinite values, traversal and mutable nested configuration. Bind integration
versions, settings, variable mappings, seeds and checkpoint format into study identity. An
upgrade, changed mapping or changed sampler creates a new study; it cannot silently resume one.
Keep secrets and machine-specific credential paths outside serialized records.

Extend identity construction and trusted factory registration together. The package must not
import an optional framework during ordinary base imports, CLI help or report reconstruction.

### External optimizer transaction protocol

Start with one outstanding action and no external automatic execution or retries.

1. Persist proposal intent and the committed ledger prefix before a stateful external ask.
2. Obtain a suggestion, validate its canonical configuration and persist its external ID and
   resumable state before admitting the Autoengineering action.
3. Reserve and launch physical work through the existing controller. An external trial entry
   alone never authorizes a model start.
4. Commit the scientific result before telling the external framework. Persist a tell intent
   bound to the exact result digest, then save a synchronization receipt.
5. Resume by reconciling pending intents, action/result commits and external state. Reuse saved
   proposals and outcomes rather than asking again or rerunning a committed evaluation.

Faults between every pair of these steps must be recoverable or explicitly blocked. Select a
supported persistence or deterministic reconstruction strategy during the prototypes. A seeded
sampler alone is not proof that its state can be reconstructed. If an ask mutated state before
its ID was saved, reconcile a durable nonce/checkpoint or stop with `reconciliation_required`.
Do not promise a generic exact-once external transaction that the framework cannot provide.

A tell with the same action/result digest must not add another observation. Conflicting tells
must fail. A missing or corrupt checkpoint must never trigger silent optimizer reset. Record
framework state with its version and digest; do not load arbitrary user-supplied pickle files.
Newly sampled trajectories need not be identical across versions or hardware. Recovery must
preserve already committed decisions and avoid duplicate physical starts.

### Failure and incomplete-trial semantics

Keep existing `success`, `scientific_infeasible`, `model_failure`, `timeout` and
`infrastructure_failure` meanings. Only complete feasible successes enter final recommendation.
A finite objective does not override failed scientific checks. Where an external framework has
fewer failure states, save its coarse projection alongside the full authoritative reason.
Never substitute a large penalty, zero, infinity or invented metric for a failed attempt.

Pruning and cancellation are not members of the current `EvaluationStatus` enum. Keep pruning
disabled in the initial integration. Before enabling it, design a versioned incomplete-result
contract and compatibility readers, including accounting, reporting and optimization behavior.
Do not relabel an old ledger or map a pruned trial to an ordinary model failure. Cancellation
retains existing control/attempt evidence and unresolved-work accounting until stop is verified.

## 4. BMI and interface semantics

Implement `adapters/bmi.py` around registered factories, not arbitrary worker-provided import
strings. A fresh model instance belongs to one attempt. Its prepare context supplies immutable
parameters, declared input artifacts, seed and private scratch space.

The first supported capability profile is scalar numeric exchange and fixed daily stepping.
It matches the current campaign contract. Validate actual BMI metadata against the declared
port contracts before advancing a model: input/output names, dtype, scalar grid rank/size,
units, start/end/current time, step size and declared timestamp meaning. Numeric BMI time needs
an explicit origin and mapping to the campaign's dates. BMI metadata does not establish whether
a value is an interval total, interval mean or instantaneous observation; require that mapping.

Specify the execution order: set forcing for the declared interval, advance once, collect the
corresponding output and attach its start/end timestamp. Check that advancement is monotone,
reaches the expected time and never silently overshoots. Validate output size and finiteness.
Copy values at exchange and result boundaries so `get_value_ptr` storage cannot mutate prior
outputs or another component. Preserve input arrays and baseline instances.

Cleanup must handle initialization failure, partial setup, run failure and cancellation. Finalize
every initialized instance even if another finalizer fails. Preserve the primary failure and
record cleanup failures separately. BMI does not imply portable checkpoint support. Unless a
model explicitly qualifies restoration, a killed attempt cannot resume halfway through its state.
Any authorized restart is a new charged attempt, not an unrecorded retry.

No implicit unit conversion, broadcasting, interpolation, calendar change or regridding is
allowed. A needed transformation is a named, versioned component with source and data identity.
For solar subdaily inputs, implement a new time-contract version only after freezing interval,
timezone, daylight-saving and aggregation rules. Do not relabel hourly values as daily ones.
Unsupported multidimensional grids, adaptive steps and mismatched calendars fail before execution.

Use existing local BMI models as the first direct/wrapped parity fixtures. Preserve their
historical output and runner. Add compatibility wrappers rather than rewriting checked evidence.
Investigate one independent BMI implementation to expose assumptions specific to local classes.
If its dependencies or semantics are unsupported, report that limitation explicitly.

PyMT admission is a separate gate: select a concrete model pair and exchange problem, verify its
units/time/grid behavior directly, then wrap and compare it. Do not recreate PyMT's spatial
exchange methods inside Autoengineering. Defer this extension if the scalar/daily profile meets
the selected examples' needs.

## 5. Ax/Optuna prototypes and policy selection

Place bounded prototypes under `examples/interoperability/optimizer_comparison/`. Use the same
trusted evaluator, objective direction, constraints, seed list, candidate families, initial
points, data access and physical evaluation ceiling for both frameworks and a Sobol reference.
Separate framework algorithm settings from shared scientific rules. Disable pruning, parallel
execution and framework-owned retries during this comparison.

Exercise a small continuous case, an integer/categorical case and one conditional family case.
Represent conditional spaces explicitly. The existing flat search space must not silently treat
inactive parameters as active scientific decisions. Initially use a versioned branch mapping
with canonical inactive defaults and deduplication by active configuration, or separate child
studies for families with a frozen allocation rule. Both prototypes must use the same choice.
If neither representation is faithful, add and test a versioned conditional-space contract before
claiming mixed-family support. Check round trips, bounds, type distinctions and exhausted spaces.

The comparison manifest must specify concrete limits before execution: seeds, starts, repairs,
wall time, memory and total attempts including failures. Measure startup/import time, suggestion
and tell overhead, total runtime, feasible objective history, failure handling, recovery behavior,
dependency footprint and integration code required. Repeat cheap timing measurements and retain
individual samples. Do not select a framework from its single strongest objective result.

Apply gates in this order:

1. Public API and license suitability for Python 3.12 in isolated optional environments.
2. Faithful configuration, objective, constraint and failure mapping.
3. Durable resume, duplicate-message handling and no duplicate physical starts.
4. Base-package independence and acceptable resource requirements.
5. Demonstrated value on the chosen example or documented reduction in integration burden.

Record selection before implementing the supported adapter. Retain the other prototype as an
experimental comparator or archive it with the decision. The selected policy implements the
existing backend protocol, derives recommendation from the authoritative ledger and emits
truthful diagnostics. Update strict run-file parsing, CLI choices, policy identity and campaign
child-study construction together when promoting it to public use. Add a named optional extra
and Pixi environment only for the admitted integration. Do not widen all existing solve groups.

## 6. OpenMDAO coupled execution

Implement `adapters/openmdao.py` as a wrapper around a trusted `Problem` factory. Treat the
complete coupled solve as one campaign component. Preserve its internal nonlinear/linear solver,
connections and convergence checks. Do not flatten feedback into the package's feed-forward DAG.

Map external design variables, outputs, units, shapes, objective direction, constraints and
scaling explicitly. Setup a fresh problem for each attempt unless a separately qualified reset
path proves isolation. Run model evaluation without invoking a hidden inner optimizer. Record
solver configuration, convergence/residual diagnostics and dependency/source identity. Always
close recording resources and clean scratch files through the adapter lifecycle.

Start with a small analytic or Sellar-style coupled fixture for wiring, derivatives and failure
injection. Then select one real engineering model with available inputs, a usable license,
physical constraints and affordable execution. Save the selection rationale before comparison.
A synthetic fixture alone does not satisfy the required coupled engineering example.

Compare three routes: direct model evaluation, wrapped evaluation at identical configurations,
and native OpenMDAO optimization versus the selected Autoengineering policy. Use identical
bounds, constraints and starting conditions where algorithms allow. Preserve native derivatives
rather than disabling them to favor the wrapper. Report solver iterations, derivative work,
model/component calls and total time as well as top-level evaluations. A driver run is a separate
study; it must not hide hundreds of model solves inside one charged evaluator call.

Freeze per-output absolute/relative tolerances based on units and solver tolerances. Check
constraint residuals and convergence as well as objective agreement. Nonconvergence is a model
failure unless a separately declared scientific constraint defines another meaning. Finite
nonconverged outputs cannot pass. Derivative inconsistencies and unit/scaling errors must be
visible before comparing optimizer performance. If a native driver cannot honor a hard physical
budget, label the comparison as unmatched and do not use it for a fixed-budget benefit claim.

## 7. Solar integration and bounded development evidence

Use the existing pvlib/OEDI chain as the second practical integration target. Inventory cached
inputs, license/access conditions, quality flags, timestamps, measured AC observations and prior
exposure. Reuse cache verification; no download or changed cache bytes should occur implicitly.
Select a bounded thermal/electrical alternative task with supplied implementations.

First reproduce the direct baseline on the exact same data. Then run through the admitted
adapter and selected search policy. Keep data filtering, units, clipping behavior, loss terms,
capacity constraints and aggregation identical. Include night-time behavior, missing intervals,
nonfinite values and an attractive but physically invalid configuration in tests. Any training
belongs to fitting data and carries its own cost and artifact identity.

If the required resolution exceeds the current daily contract, complete the versioned time
extension before admitting this example. A documented daily aggregate is acceptable only when
the scientific objective itself is daily and energy/power aggregation is validated. Do not
silently change the task to fit an interface.

Record quality, constraint violations, model starts, failed work, optimization overhead, wall
time and adapter development burden. Separate direct/wrapped parity from optimization benefit.
Use deterministic/scripted campaign execution first; Part 4 does not require new paid LLM calls.
Part 5 owns independent confirmation, generalization and repeated agent-utility comparisons.

## 8. Conditional DAKOTA and Ray work

### DAKOTA sensitivity or uncertainty study

A trigger requires a named model decision, uncertain inputs with justified ranges/distributions,
and an explanation of why existing sensitivity or sampling tools are inadequate. Save the
chosen method, estimator, seed, sample budget and failure treatment before running. For sensitivity,
define the reported quantity and parameter domain. For UQ, state distribution assumptions and
separate input variability from model discrepancy and measurement uncertainty.

If admitted, build an external-driver bridge using strict parameter/result parsing, unique
private attempt directories and bounded subprocess supervision. DAKOTA may request evaluations,
but the Autoengineering broker owns capacity and result commits. Check response ordering,
missing/truncated output, process failure, duplicate requests and cancellation. Disable automatic
retries or route every retry through new charged attempts. Every uncertainty or sensitivity
sample must retain its physical attempt link.

Validate first against an analytic reference with known behavior, then direct DAKOTA execution
on the named example. Report failed samples and method validity rather than silently dropping
failures. No trigger means a documented deferral, not a placeholder adapter advertised as support.

### Ray execution adapter

A trigger requires profiling a representative serial workload and a numerical target for useful
speedup or throughput after scheduler overhead and memory use. Compare a simple bounded local
process pool before adding Ray. Start with local resources; remote clusters require a separate
execution decision and resource authorization.

If admitted, Ray workers execute pre-reserved attempts and return bounded receipts to a single
scientific writer. Freeze resource requests, maximum concurrency, completion-order policy and
retry policy. Use zero framework retries initially. Disable Tune search/scheduler behavior that
would become a second optimizer or acceptance authority. If Tune cannot support that ownership
cleanly, document the mismatch and evaluate Ray Core separately without claiming Tune support.

Qualify driver/worker loss, actor restart, duplicate completion, cancellation, unavailable
resources and checkpoint corruption. Bound queued and running reservations together. A framework
checkpoint does not prove a scientific result committed. Preserve task identity and data grants
across restart. Do not mount private comparison/confirmation labels in worker environments.
Concurrency is admitted only after serial recovery gates pass; faster execution alone is
insufficient when failure recovery duplicates work or loses accounting.

## 9. Implementation increments and deliverables

All paths below are proposed unless linked as existing. Deliver in dependency order. DAKOTA and
Ray investigations are mandatory; their implementations depend on the stated triggers.

| Increment | Work and deliverables | Acceptance gate |
| --- | --- | --- |
| 4.1 Inventory and decisions | `docs/decisions/part-4-integrations.md`, source inventory, six-system API/license/dependency review, capability matrix and frozen prototype limits | Every system has a concrete need, candidate interface, owner map and adoption/deferral criteria. Existing behavior and unsupported cases are recorded. |
| 4.2 Integration records and recovery | `integrations/contracts.py`, trial links, checkpoint policy, synchronization receipts and fault fixtures | Strict serialization/identity tests; ask/tell fault recovery; duplicate/conflicting messages; no reset or duplicate physical start after crash. |
| 4.3 BMI adapter | `adapters/bmi.py`, direct/wrapped fixtures, explicit daily/scalar profile and optional broader time contract | Metadata and output parity; no aliasing; invalid units/time rejected; all initialized models finalized; restart accounting retained. |
| 4.4 Optimizer prototypes | Ax/Optuna/Sobol comparison example, manifests, raw results and decision | Both prototypes exercise the same spaces/failures/recovery; selection follows frozen gates. Failure of both leaves this increment blocked. |
| 4.5 Selected optimizer | `optimization/external_backend.py` or framework-specific equivalent, optional dependencies, strict CLI/config support and campaign bridge | Complete supplied-candidate calibration, fresh/resume parity, ledger-grounded recommendation, base imports without the framework. |
| 4.6 Coupled engineering | OpenMDAO adapter, synthetic contract fixture and real engineering example with native reference | Direct/wrapped outputs and feasibility agree within frozen tolerances; convergence and derivative work visible; costs include inner work. |
| 4.7 Solar workflow | Cached-input campaign, resolution contract, baseline and alternative comparison, evidence report | Direct/wrapped parity, physical rejection control, matched data access and truthful development-only claims. |
| 4.8 Need-driven extensions | PyMT decision, DAKOTA sensitivity/UQ decision, Ray profiling/decision; adapters only when triggered | Every admission passes direct parity, recovery and documented benefit/burden gates. Each deferral names missing need/evidence and revisit condition. |
| 4.9 Packaging and audit | Optional environment locks, integration guide, runnable commands, documentation index and final audit | Required paths run from installed artifacts; optional dependencies absent from base; platform and incomplete scope stated explicitly. |

Begin 4.3 after the metadata portion of 4.2 is settled. Prototype design can proceed alongside
BMI work, but policy promotion depends on 4.2 recovery evidence and 4.4 selection. Solar depends
on the needed time semantics and selected policy. OpenMDAO direct parity can precede optimizer
comparison. No extension bypasses the shared ownership, accounting or source-identity gates.

Each increment closes with source hashes, commands, exit statuses, results and unresolved items.
Keep statuses `implemented`, `verified`, `blocked`, `deferred` and `not_attempted` distinct.

## 10. Verification and evidence design

Use deterministic fake framework APIs and fake executables in the base suite. Optional real
framework tests run in dedicated environments. Ordinary tests must not download model inputs,
start live agents, provision compute or rerun frozen historical benchmarks.

| Test group | Required cases |
| --- | --- |
| Records and configuration | Unknown/duplicate fields, mutable nested input, wrong framework version, changed mapping, invalid digest, missing optional dependency |
| BMI lifecycle | Partial initialization, finalizer error, shared pointers, extra/missing variable, wrong dtype/grid, no time advancement, overshoot, unsupported interval/calendar |
| Search translation | Min/max direction, bounds, integer/category types, conditional activation, inactive-value deduplication, constraints, empty feasible set and exhausted search space |
| Synchronization | Crash before/after ask, action commit, result commit and tell; lost acknowledgment; corrupt checkpoint; conflicting trial/result IDs |
| Budgets and failures | Failed starts, uncertain cost, budget exhausted before dispatch, cancelled worker still running, external retry attempt and unrecorded inner solves |
| OpenMDAO | Coupled convergence, scaled/unscaled output agreement, invalid derivatives, fresh/reset isolation, native record linkage and recorder cleanup |
| Solar | Verified cached bytes, time alignment, power versus energy, night-time zeros, missing data, physically invalid candidate and fitting-data separation |
| Optional execution | DAKOTA malformed response and sample failures; Ray worker loss and duplicate completion; unsupported features reject before a model starts |
| Packaging/reporting | Base import/help without extras, wheel install, missing/corrupt evidence, offline report rebuild, no framework or model invocation during reporting |

For parity, save reference configurations and full relevant outputs, not only final scores.
Freeze tolerances before inspecting wrapped differences. Use `abs(actual-reference) <= atol +
rtol*abs(reference)` for numerical comparisons where appropriate, with separate feasibility and
convergence checks. Scientific tolerances must be justified in the example protocol. Passing
schema tests or matching a rounded objective is insufficient.

For benefit or burden reduction, record the direct workflow before integration: manual steps,
custom glue, execution cost and recurring failure points. The admission report must show what
changed using retained artifacts. A measured neutral or adverse performance result is valid;
claim only the documented interoperability benefit if that is what the evidence supports.

Every development run needs a resolved manifest with concrete seeds, candidates, trial and
physical-start ceilings, wall-time/memory limits, data hashes, versions and output directory.
Use a fresh output root and reserve confirmation/comparison capacity before search. Preserve
failed attempts and unknown usage. This plan supplies no blanket authority for expensive runs,
new installations, remote work or reuse of exhausted Part 3 allowances.

Run focused tests after each increment, then `pixi run lint` and `pixi run test` before integration.
Run `pixi run -e bayes test-bayes` when shared optimizer behavior changes and that environment is
available. Existing solar environments need their relevant open-chain tests. Add explicit optional
integration tasks during implementation and document their actual names after they exist.
When using the main checkout's interpreter for a linked worktree, set the source path explicitly
and print the imported package path before testing.

Qualify macOS ARM64 first and Linux separately. Record an untested platform as unverified even
if dependency resolution succeeds. A required integration blocked on one platform may have a
narrower documented delivery, but cannot be described as qualified on both.

## 11. Completion audit and handoff to Part 5

The final audit must link each increment to executable evidence, exact implementation and
environment identities, direct-reference comparisons, retained failures and known limitations.
Update the development plan only after those gates pass.

Part 4 completion requires all six investigations, a qualified BMI subset, a selected supported
external optimizer, the real coupled engineering example, the solar path and reproducible
installed reports. Every admitted integration needs parity, failure/recovery evidence and
measured benefit or documented burden reduction. PyMT extensions, DAKOTA and Ray may remain
explicitly deferred when their need gates are unmet. Missing any required integration is partial
completion, not a reason to narrow the parent scope retrospectively.

The Part 5 handoff contains development exposure records, candidate catalogue, conventional
optimizer baselines, cost definitions, unsupported semantics/platforms and the unresolved
scientific questions. It must not describe successful interoperability or a development score
as independent prediction evidence, general optimizer superiority or value from multiple agents.
