# Part 2 implementation plan: workflow and shared contracts

__Status:__ ready for implementation planning review. This document specifies proposed behavior;
Part 2 package code has not been implemented.

__Parent:__ [Development plan, Part 2](../development-plan.md#2-codify-the-workflow-and-shared-contracts).
__Starting evidence:__ [Part 1 results](../../background-research/agentic-architecture/README.md),
[decision](../../background-research/agentic-architecture/decision.md), and
[prototype](../../examples/agentic_architecture_pilot/README.md).

## 1. Outcome and scope

Deliver a local, deterministic campaign layer that takes a supplied modeling intervention through
admission, optional calibration, evaluation, scientific acceptance, and a durable decision. A fixed
replacement and a parameter search must use the same model identities, adapter lifecycle,
acceptance rules, and result format. A correct result may retain the baseline or report that no
eligible model exists.

Part 1 is accepted as sufficient to proceed. The user explicitly deferred strict token enforcement
and support for other models. Its recorded token overrun and incomplete experiments remain evidence;
they are not blockers for this implementation. The Part 1 artifacts and frozen run specifications
must remain intact. This plan is the current scope decision where its priorities differ from the
historical Part 1 handoff.

| Build in Part 2 | Leave for later work |
| --- | --- |
| Strict campaign specification and immutable scientific identities | New LLM providers, model selection, and strict token accounting |
| Explicit transitions, request validation, durable events, and replay | Production investigator/implementer/reviewer agents and scheduling |
| Model interface and lifecycle contracts around existing models | General model DAG redesign, arbitrary coupled solvers, automatic ML training |
| Separate candidate admission, calibration, and scientific acceptance | Open-ended candidate generation and live literature research |
| Sequential child-study bridge, execution counts, timeout, cancellation | Parallel/distributed execution and cloud workers |
| Local CLI/JSON contract with read-only inspection and evidence reports | Installed host plugins, MCP integration, and a web application |
| Supplied trusted adapters and protected evaluator-owned observations | Admission and sandboxing of arbitrary generated code |
| Deterministic examples and fault tests | Independent utility benchmarks and claims of scientific generalization |

Part 3 will integrate real agent roles and the first production host adapter. Part 2 will leave a
stable tool boundary for that work. Model/provider portability and hard token ceilings do not
appear in Part 2 acceptance criteria. Optional token/cost observations may be recorded when supplied,
but an unknown value is represented as unknown, never zero.

## 2. Starting code and integration boundaries

Inspect these interfaces before changing their consumers:

| Existing code | Reuse | Preserve or address |
| --- | --- | --- |
| `system/component.py`, `system/graph.py` | Component names, declared ports, graph identity, copy operations | Existing port labels do not validate units, dimensions, grids, or time support |
| `research/candidates.py` | Rationale, sources, and conversion to replacement components | `Candidate.name` denotes a target, not a unique implementation version |
| `research/runner.py` | Trusted Python/command execution, parameter mapping, array isolation, failure taxonomy | Do not expose trusted executable configuration as an untrusted worker API |
| `research/loop.py` | Existing behavior and regression coverage | Its thresholds remain annotations and its retention rule remains unchanged |
| `optimization/spec.py`, `run_spec.py`, `space.py` | Immutable study, objective, budget, search-space, and policy records | No second optimizer configuration language with different meanings |
| `optimization/controller.py`, `ledger.py` | Sequential study execution and compatible recovery | The campaign references child records and never rewrites them |
| `optimization/provenance.py`, `yaml_utils.py` | Canonical serialization, hashes, strict YAML patterns | Promote reusable helpers only when needed; avoid depending on private internals |
| `validate/compare.py` | Existing numeric metric implementations | Add explicit campaign acceptance around them, including unavailable checks |
| `examples/agentic_architecture_pilot/` | Behavior reference and failure cases | Preserve these hash-bound files; build the new example separately |

A specific recovery detail matters: the current optimization controller turns a valid pending
action without a saved result into `infrastructure_failure`, with zero recorded child cost. Part 2
must preserve this behavior. Its campaign record must retain the physical attempt and any uncertain
cost instead of interpreting that zero as proof that nothing ran.

Use new `src/autoengineering/campaign/` and `src/autoengineering/adapters/` packages. Keep scientific
execution independent of the eventual host adapter. Do not import Torch, BoTorch, BMI, or a host SDK
from either package's base import. Use the existing Python 3.12/Pixi environment and standard-library
records/protocols with existing PyYAML, NumPy, Click, and Rich dependencies.

## 3. Shared records and identity

### 3.1 Campaign specification

Create frozen records with explicit `to_dict`/`from_dict` methods and a strict YAML loader. Reject
unknown fields, duplicate keys, unsupported versions, malformed dates, nonfinite numbers, booleans
where integer limits are expected, duplicate IDs, and invalid references. Validation precedes model
imports, directory creation, and scientific execution.

`CampaignSpec` version `1.0` contains:

| Field group | Required content |
| --- | --- |
| Identity | Schema version, campaign name, scientific scope, seed, source bundle reference |
| Baseline | System definition, model snapshot, adapter declaration, fixed parameter configuration |
| Data | Named input/observation artifacts, hashes, variable names, units, time axis, split roles, prior exposure |
| Allowed interventions | Target component, admitted implementation IDs, parameter names and bounds, topology policy |
| Scientific task | Objective, hard checks, secondary-metric tolerances, deterministic ranking and tie rule |
| Calibration | Existing study/policy/search-space records, fitting split, fixed child budget and seed |
| Workflow | Required stages, maximum candidates, invalid-request/repair limits, terminal conditions |
| Execution | Trusted adapter registry, timeout, cancellation grace, scientific execution allowance |
| Confirmation | Disabled or a predeclared confirmation protocol and data reference |
| Provenance | Declared transitive source files, environment lock, expected artifact contracts |

Author configuration uses YAML. Programmatic requests/results use JSON. Use canonical JSON to hash
validated records, preserving meaningful list/parameter order. Raw file hashes remain provenance;
semantic identity is computed from the validated specification so incidental YAML whitespace is not
a different scientific task.

Defaults must be explicit after resolution and included in the identity. A field that affects
execution or acceptance cannot be supplied only through an unrecorded CLI option. Invocation limits
may restrict how much of an unchanged campaign runs now; they may not increase its frozen budget.

### 3.2 Records to introduce

| Record | Meaning |
| --- | --- |
| `ArtifactRef` | Relative artifact path, SHA-256, byte size, media/array metadata, producer identity |
| `ModelSnapshot` | Graph digest, component implementation versions, source/dependency bundle, interface contract |
| `CandidateProposal` | Unique proposal ID, target, hypothesis, sources, expected benefit, cost estimate, eligibility evidence |
| `CandidateSnapshot` | Admitted proposal plus implementation, adapter, parameter-space, and source hashes |
| `DataContract` / `PortContract` | Required names, dimensions, units, dtype family, grid/time support, missing-value policy |
| `EvaluationRecord` | Execution status, named metrics/checks, output references, split identity, timings and provenance |
| `CheckResult` | `pass`, `fail`, `unavailable`, or `error`, with value/threshold where meaningful and evidence references |
| `DecisionRecord` | Eligible alternatives, selected identity/configuration or none, rules applied, reasons and evidence |
| `StudyLink` | Child identity, candidate, fitting inputs, space, policy, seed, work path and committed manifest reference |
| `AttemptRecord` | Physical attempt identity, reservation, launch/result state, child action ID, measured or uncertain cost |
| `CampaignEvent` | Ordered immutable transition with request identity, prior event hash, payload and referenced artifacts |

Keep execution status, scientific eligibility, and selection outcome separate. A successful model
execution can fail a conservation check. A valid candidate can lose the comparison. Missing data
can make acceptance unavailable. None of these is silently converted to a convenient objective.

### 3.3 Identity rules

Compute campaign scientific identity from the resolved specification, baseline/model snapshots,
input and observation hashes, acceptance implementation, declared model/glue sources, seed, and
environment lock. Include imported local helper sources explicitly. A top-level evaluator hash
alone is insufficient. Validate the declared dependency closure for the supplied adapters during
implementation; do not promise automatic discovery of arbitrary Python imports.

Separate identity layers:

- The campaign specification fixes what interventions are allowed. Admitted candidate snapshots
  are immutable events added under that specification, not mutations of the original campaign hash.
- A child study binds the exact candidate, adapter, fixed inputs, fitting data, search space,
  policy/options, budget, and seed. A changed implementation, policy, or study budget creates a
  new child study linked to its predecessor. It never resumes the old one.
- Host/model metadata belongs to a future worker invocation record. Changing a host must not
  invalidate scientific evidence when its admitted candidate snapshot is unchanged.
- Request IDs identify logical commands. Attempt IDs identify physical work. Neither is a synonym
  for candidate, component target, campaign, or child-study ID.

A campaign with incompatible scientific identity refuses resume before modifying evidence.
No automatic schema migration is needed in Part 2. An eventual migration must write a new campaign
with explicit parent provenance. Do not import the Part 1 mutable snapshot as a production journal.

## 4. Model and adapter contracts

### 4.1 Interface checks

Add richer contracts alongside legacy `Port` and `Component` rather than changing every existing
system YAML. A campaign must supply a contract for each exposed input/output. Unspecified legacy
metadata is `unknown` and cannot pass a required compatibility check.

For Part 2, require exact declared names, numeric dtype families, dimensions, coordinate order,
units, and time support. Support scalar values and aligned one-dimensional daily time series.
Represent grid/spatial support by a stable identifier and coordinate digest; test mismatches but
defer general regridding. Do not infer unit conversion, broadcast arrays, reorder features, join
dates, or interpolate gaps. Explicit trusted preprocessing adapters may perform declared conversions
with their own identities and tests.

Declare whether a time value is instantaneous, an interval mean, or an interval total. Require
matching timestep, calendar, timestamp convention, and warm-up/scoring masks. State initialization
and continuity across splits belong to the task. Preparing a new parameter configuration starts
fresh model state; moving from fitting forcing into comparison forcing preserves causal state
for that same configuration.

A coupled solver may be wrapped as one adapter with its own internal convergence checks. The
existing feed-forward graph runner continues to reject cycles. The campaign layer does not turn
feedback into an acyclic graph by dropping edges.

### 4.2 Lifecycle

Define a small protocol with these methods and recorded outputs:

| Method | Input | Output and obligation |
| --- | --- | --- |
| `prepare(context)` | Immutable snapshot, permitted data, parameter configuration, seed, scratch path | Prepared handle with explicit state initialization; no observation leakage |
| `validate(handle)` | Prepared handle | Interface/parameter checks before any costly model execution |
| `train(handle, fitting_data)` | Only declared fitting data | Optional learned-artifact reference and training cost; otherwise `not_applicable` |
| `run(handle, forcing)` | Explicit arrays/time axis | Outputs and state/flux diagnostics without mutating caller-owned inputs |
| `inspect(handle, outputs)` | Model state/output evidence | Physical/numerical diagnostics required by acceptance |
| `cleanup(handle)` | Prepared resources | Idempotent resource release, including after partial preparation or failure |

The first implementation uses a trusted Python adapter and an example-specific wrapper around
existing hydrology functions. Preserve existing command runnable behavior through a compatibility
wrapper only if needed by acceptance tests. Defining the optional training contract does not require
training a neural model. A small deterministic test adapter can exercise training artifact identity,
fitting-data access, and recorded cost.

Run model work in a supervised process for timeout and cancellation. Process separation provides
lifecycle control; it is not a security sandbox. The registry accepts only explicitly supplied,
trusted adapter factories. Worker-provided import strings, shell commands, or code uploads are not
admitted by this version. Future worker requests receive artifact IDs and permitted summaries,
not arbitrary evaluator file paths.

## 5. Scientific evaluation and acceptance

Use the same `EvaluationRecord` for the unchanged baseline, a supplied fixed replacement, and a
calibrated configuration. Store full-precision metrics and compare before rounding. Reports may
round display values without affecting retention.

Evaluate in this order:

1. Check data availability, alignment, initial state, parameter validity, and adapter compatibility.
2. Run the model and classify execution. Preserve the existing statuses `success`,
   `scientific_infeasible`, `model_failure`, `timeout`, and `infrastructure_failure` in child records.
3. Evaluate required output and physical checks. A required `unavailable` or `error` check prevents
   eligibility, just as a required failed check does. Optional checks remain visible.
4. Select parameter configurations using only the fitting objective and child constraints.
5. Evaluate frozen choices on the development comparison split and apply hard checks plus the
   predeclared primary gain, secondary tolerance, and tie rules.
6. Record eligible alternatives, decision, and reasons. An agent's narrative cannot override them.

Check functions are registered trusted implementations referenced by name and version. Avoid an
expression language or executable code embedded in campaign YAML. A check result includes its
scope, such as routing conservation, whole-model balance, or a diagnostic proxy. No generic metric
name implies that an observation is independent.

An ineligible baseline is not an eligible fallback. If every alternative is ineligible, return
`no_eligible_model` with no recommendation. If an eligible baseline is unbeaten, return
`retain_baseline`. If no candidate is proposed or observations are insufficient, retain those
explicit outcomes without manufacturing an improvement score.

Freeze selection before any optional confirmation. The first measured-data example uses
`confirmation: disabled` because its data have already been exposed. Reports must say
`confirmation_not_attempted`. Test the confirmation transition and one-shot restriction with a
small synthetic fixture, not a claimed independent hydrologic evaluation. A failed confirmation
cannot loop back into selection on the same confirmation data.

## 6. Workflow and request protocol

### 6.1 State machine

Keep one authoritative controller. The workflow state describes progress; a separate terminal
outcome explains why it stopped. The physical graph and intervention lineage remain separate.

| From | Command/result | To | Required evidence and failure path |
| --- | --- | --- | --- |
| `created` | Validate task and baseline | `baseline_ready` | Valid specification/data and eligible baseline, or terminal invalid/insufficient-data outcome |
| `baseline_ready` | Record diagnosis | `proposal_open` | Diagnostic artifact and allowed intervention scope; deterministic/manual input is sufficient |
| `proposal_open` | Submit proposal | `candidate_pending` | Valid proposal identity and remaining candidate/request allowance |
| `candidate_pending` | Admit adapter/snapshot | `candidate_ready` | Interface/source/eligibility checks; rejection records reasons and returns to `proposal_open` |
| `candidate_ready` | Request fixed evaluation or calibration | `evaluating` | Durable reservation and attempt/study link committed before launch |
| `evaluating` | Commit evaluation | `evidence_ready` | Verified result or explicit failure; uncertain work enters `reconciliation_required` |
| `evidence_ready` | Apply acceptance and record review | `proposal_open` or `selection_frozen` | Rule-derived decision; further proposals only within frozen limits |
| `selection_frozen` | Confirm or record disabled confirmation | `report_ready` | Fixed selection and confirmation identity, or explicit `not_attempted` |
| `report_ready` | Generate report and close | `completed` | Artifact references, outcome, costs, failures, and unresolved checks |
| Any nonterminal state | Cancel, timeout, or exhaust budget | `stopping` then terminal | Termination/reconciliation evidence before claiming no active work |

Add explicit terminal outcomes for accepted candidate, retained baseline, no suitable intervention,
no eligible model, insufficient data, invalid task, budget exhausted, cancelled, and failed execution.
`reconciliation_required` is resumable but cannot launch new scientific work automatically.

Every transition declares its owner, preconditions, result schema, retry allowance, and stop rule.
For the first profile, allow at most two repairs after a rejected proposal/request. Persist rejects
and repair counts so restarting a caller does not reset them. Valid duplicate requests consume no
extra scientific budget. An edited request needs a new request ID and references the rejection it
repairs. Invalid byte streams without a valid ID are recorded by a generated transport-attempt ID
and bounded by the transport limit, not inserted as malformed domain events.

### 6.2 Tool envelope

Use one envelope for CLI JSON and the Python service:

```json
{
  "schema_version": "1.0",
  "campaign_id": "campaign-id",
  "request_id": "request-id",
  "expected_revision": 12,
  "operation": "evaluate",
  "payload": {"candidate_id": "candidate-id", "mode": "calibrate"}
}
```

Responses carry request ID, status, resulting revision, typed result/error, and artifact IDs.
Operations are `state`, `diagnostics`, `propose`, `admit`, `evaluate`, `review`, `freeze`, `confirm`,
`cancel`, and `report`. Read operations cannot advance state. Scientific operations are available
only to the trusted local controller/broker in Part 2.

On retry, look up the canonical request digest before checking `expected_revision`. Identical
committed requests return the original response even if the campaign has since advanced. Reusing
an ID with different content is an error. A new request with a stale revision is rejected without
execution. Store the response reference in the same committed event that resolves the request.

Cap an individual request at 64 KiB. Reject unknown fields and unsupported operations before model
imports. Return errors such as `schema_error`, `stale_revision`, `request_conflict`,
`identity_mismatch`, `invalid_transition`, `budget_exhausted`, and `reconciliation_required`.
Do not put tracebacks or private observation paths in the worker-facing response.

## 7. Persistence, budgets, and cancellation

### 7.1 Campaign event store

Use an append-only sequence of individually committed canonical JSON event files. This avoids
making a partially written JSONL line part of the campaign's authoritative history. Keep the
existing child observation ledger format unchanged.

Proposed directory layout:

```text
campaign/
  campaign.yaml                 # immutable resolved specification
  identity.json                 # immutable scientific identity and source manifest
  events/000000000001.json       # ordered immutable events with previous-event hash
  state.json                    # replaceable projection, reconstructible from events
  artifacts/<digest>/...        # immutable verified inputs/results and source bundles
  children/<study-id>/...        # unchanged OptimizationStudy artifacts
  attempts/<attempt-id>/...      # supervisor receipts, logs, and process identity
  control/cancel-<request-id>.json
  reports/...
  .campaign.lock
```

Under a single-writer lock: validate the current event chain and referenced records, stage outputs,
flush files, atomically commit an event without overwriting an existing sequence number, sync its
directory, and update the derived projection. The event commit is the campaign transaction boundary.
A response is acknowledged only after that commit. Interrupted temporary files are not committed
events. Preserve/quarantine them during explicit recovery rather than silently deleting evidence.

Test crash points before staging, after artifact durability, after event commit, after projection,
and before acknowledgment. Rebuild a missing/stale projection from events. A gap, duplicate sequence,
modified hash, or missing committed result is corruption and stops recovery without rewriting the
journal. Hashes detect accidental changes; they are not protection against an actor who controls
the entire store.

Reject symlinks, path traversal, special files, and artifacts outside allowed roots. Use bounded
array readers with `allow_pickle=False`, explicit size/member limits, and hashes verified before
loading. Preserve owner-private result directories. Reuse tested path/NPZ helpers through supported
interfaces when possible; do not weaken existing validation to simplify the new store.

### 7.2 Reservations and child studies

Reserve a child's full worst-case execution allowance before creating it, plus separately declared
comparison/diagnostic calls. The child retains its own immutable budget and accounts for its own
ledger. Campaign totals charge physical attempts once through stable attempt/action mappings;
adding the child ledger total to the reservation would double-count work.

Maintain separate fields for reserved capacity, confirmed attempts, measured cost, and unresolved
attempts/cost. Count baseline, defaults, calibration, training, diagnostics, failures, and authorized
retries. Release unused reservations only after the child is terminal and its attempts reconcile.
An uncertain execution retains its allowance. A retry is a new attempt and needs capacity; it does
not erase the previous attempt.

Drive existing `OptimizationStudy` through its public API. Do not append synthetic observations to
its ledger or patch its private pending files. Persist the `StudyLink` before launch. On restart,
validate campaign identity and process/attempt state before allowing the child's normal recovery.
If child recovery records its existing zero-cost infrastructure failure, attach the campaign's
uncertain-cost note without changing that observation. Stop automatic continuation until the
uncertain attempt is acknowledged through an explicit reconciliation record.

### 7.3 Active cancellation and timeout

Run one child process group at a time on supported POSIX platforms. Persist a launch nonce and
process identity before acknowledging launch. Never signal an unrelated process based only on a
reused PID. For the first profile, use a 60-second evaluation timeout, a 5-second termination grace,
and a further 5-second kill/wait deadline. These are configuration values frozen in the campaign.

A separate `cancel` invocation atomically deposits a validated cancellation intent into the control
inbox. It does not become a second event-journal writer or wait indefinitely for a lock held by the
running controller. The controller polls that inbox while supervising work, records the intent,
stops new starts, terminates the owned process group, and records the observed result. Supervise
through `Popen` and polling rather than an uninterruptible in-process model call.

If a supervisor dies, recovery first establishes whether its owned process group is alive and
whether a valid result exists. An unverified process/result stays uncertain; no replacement work
starts. Do not claim cancellation complete until the group is gone or its survival is explicitly
reported as a failed stop. Test a child spawning a descendant, not only a sleeping parent process.

Keep cancellation/timeout in campaign execution records. Where interruption reaches the existing
child controller, preserve its established failure classification and add the campaign stop reason
alongside it. Do not add a new child-ledger status merely for the campaign CLI.

A supervised study must emit durable action-start and action-finish receipts. Apply the evaluation
timeout to each action, not to an entire multi-evaluation study. The campaign deadline bounds the
whole active invocation. A missing or contradictory receipt triggers reconciliation rather than
resetting the timer or assuming that the action never started.

## 8. Reference examples and numerical limits

### 8.1 Existing Leaf River routing path

Keep Part 1's source, task, arrays, ledgers, and manifests unchanged. Create a new campaign example
that uses its supplied routing functions and task concepts through the new contracts. Its scientific
scope remains an orchestration fixture: the chain does not represent a complete water balance.
Compare captured fixed-configuration predictions and decisions with saved evidence. Do not treat
new controller code as compatible resume of the old pilot or rewrite its source hashes.

The old pilot's data and implementation identity remain useful references, while its cumulative
mutable snapshot and ad hoc host runner are not promoted to production code. The user accepted the
Part 1 handoff; the old 320-execution limit is not extended by this plan.

### 8.2 Explicit-balance hydrology development case

Use [the existing local hydrology kernel](../../examples/local_models/kernels.py) as the starting
reference. It combines Hamon/Hargreaves PET, the soil bucket, and a linear reservoir and computes
a daily water-balance residual. Existing BMI components expose soil and reservoir storage. Wrap
these established equations in an example-specific trusted adapter, with explicit outputs for
both stores, ET, discharge, and the initial conditions. Keep a direct-call parity test against the
existing kernel. A general BMI integration remains Part 4 work.

Freeze a new development profile after checking cached timestamps, units, missingness, and metadata:

- Start with Hamon PET, soil capacity 100 mm, and reservoir recession 0.7.
- The supplied structural intervention replaces Hamon with Hargreaves. Preserve topology and
  meteorological inputs. Declare the full shared meteorological interface and reject missing
  required temperature inputs before execution.
- The parameter-only intervention changes capacity within [20, 200] mm and recession within
  [0.05, 0.95] while keeping the PET implementation fixed. Both kinds produce the same result and
  decision records, with implementation identity distinct from parameter configuration.
- Preserve the cached split labels: warm-up January-March 2019, fit April-September 2019,
  development selection October-December 2019, and historically exposed 2020 data. Treat the latter
  as an optional development replay, not a new holdout. Do not relabel the source CSV or historical
  study. Primary Part 2 acceptance needs only fitting and selection observations.
- Simulate causally from January 1 for each configuration, with soil initially half its configured
  capacity and reservoir storage zero. Never reset at the fitting/selection boundary or assimilate
  observed discharge. State explicitly that capacity changes its prescribed initial state.
- Evaluate each supplied default once. Give each family 16 scrambled Sobol fitting evaluations
  with seed 17, then evaluate the two selected configurations and two causality perturbations.
  Defaults are separate here: 2 + 32 + 2 + 2 = 38 planned executions. This is a new profile, not a
  reinterpretation of Part 1's default-included budget.
- Record three explicit comparisons from those runs: the fixed Hargreaves replacement against
  fixed Hamon, calibrated Hamon against fixed Hamon, and calibrated Hargreaves against calibrated
  Hamon. Apply the same acceptance rules to each pair. Report structural and calibration effects
  separately, and retain the comparator identity in every decision. Cached outputs can serve
  multiple comparisons without being counted as new physical executions.
- Hard checks require finite aligned outputs, nonnegative stores/fluxes within 1e-10, soil storage
  within capacity, and daily conservation. Use
  `abs(P - ET - Q - delta_storage) <= 1e-8 + 1e-10 * max(1, abs(P), abs(ET), abs(Q), abs(delta_storage))`
  in mm for each daily step. Compute the residual independently from saved states and fluxes.
- Fit RMSE on fitting observations. On the development selection split, require RMSE gain at least
  0.01 mm/day, KGE loss no greater than 0.02, and absolute bias increase no greater than 0.05 mm/day.
  All hard checks must pass. Ties retain the eligible baseline. Successful plumbing does not require
  the replacement to win.

These are proposed engineering tolerances fixed before the first new comparison. If the audit
finds incompatible data or physical definitions, document and repair the prerequisite before
freezing version 1; do not relax a failed frozen rule after seeing results.

Set the first campaign ceiling to 64 physical executions, two candidates, two repairs per rejected
handoff, 100 transport requests, and 30 minutes active execution time. Budgeted time is accumulated
supervised work plus a conservative reservation for unresolved attempts; time between user
invocations is not silently charged as model execution. Use synthetic fixtures for most recovery
and resource tests. Propose at most 320 total new real-model executions for Part 2 qualification,
tracked separately from Part 1. These limits describe future implementation checks; writing this
plan does not launch them or any paid/live-model work.

## 9. Proposed package and CLI surface

Keep modules small enough that domain logic can be tested without subprocesses or a CLI:

| Proposed path | Responsibility |
| --- | --- |
| `campaign/spec.py`, `records.py` | Strict immutable specifications and public domain records |
| `campaign/identity.py`, `artifacts.py` | Source/input identity and bounded artifact access |
| `campaign/events.py`, `store.py` | Event validation, commits, locking, projections, replay |
| `campaign/controller.py` | Legal transitions and campaign decisions |
| `campaign/acceptance.py` | Registered checks, eligibility, comparison and tie rules |
| `campaign/budget.py`, `execution.py` | Reservations, attempts, supervision, cancellation |
| `campaign/studies.py` | Adapter between campaign records and existing optimization studies |
| `campaign/service.py`, `command.py`, `report.py` | Tool envelopes, Click integration, evidence-based output |
| `adapters/contracts.py`, `python.py` | Interface/lifecycle protocol and trusted compatibility wrapper |
| `examples/campaign_contracts/` | Frozen profile, supplied candidates, direct driver, fault fixtures |
| `tests/test_campaign_*.py`, `test_adapter_contracts.py` | Contract, numerical, persistence, and CLI checks |
| `docs/campaigns.md` | User guide, status meanings, trust boundary, commands and recovery |

Use this as a responsibility map, not a requirement to create an empty module for each name. Combine
small modules where the resulting ownership remains clear.

Add a `campaign` Click group with `validate`, `run`, `resume`, `request`, `status`, `cancel`, and
`report`. Proposed usage, to become executable only during implementation:

```sh
pixi run autoengineering campaign validate examples/campaign_contracts/campaign.yaml
pixi run autoengineering campaign run examples/campaign_contracts/campaign.yaml \
  --workdir outputs/campaign-contracts --max-new-evaluations 4
pixi run autoengineering campaign status outputs/campaign-contracts --format json
pixi run autoengineering campaign resume outputs/campaign-contracts --max-new-evaluations 4
pixi run autoengineering campaign cancel outputs/campaign-contracts --request-id stop-1
pixi run autoengineering campaign report outputs/campaign-contracts
```

`run` rejects a nonempty work directory. `resume` uses the stored immutable specification and checks
its dependencies; overrides cannot change its scientific contract. `--max-new-evaluations` limits
new physical model starts across all active stages for that invocation, including baseline and
comparison work. It does not expand campaign or child budgets. Pass the remaining invocation allowance to the
child through its supported invocation limit. If a stage requires several physical calls, reserve
all of them before starting it or pause before that stage. `request` reads one bounded JSON
envelope from stdin and returns one JSON response. Send progress to stderr so machine-readable
stdout remains parseable.

Use stable exit behavior: zero for a valid command or completed campaign including a valid negative
decision; nonzero typed errors for invalid requests, incompatible/corrupt state, execution failure,
or failed stop. Report cancellation and budget exhaustion as explicit campaign outcomes in JSON;
the CLI's documented exit mapping must be tested rather than inferred by callers.

Reports link to immutable observations/checks and show rejected candidates, failures, uncertain
costs, unrun confirmation, and limitations. They must be regenerable without model execution or
network access. Existing `improve`, `optimize`, and report formats retain their current semantics.
Update the documentation test's CLI registry only when the new group actually exists.

## 10. Implementation sequence and acceptance gates

Complete each numbered increment before depending on it. Work in an isolated implementation
worktree that includes the accepted Part 1 material. Since the current evidence and plans are
uncommitted, preserve or explicitly transfer that state when creating an implementation branch;
creating a worktree from HEAD alone would omit it. No commit or push is implied by this plan.

### 2.1 Freeze contracts and compatibility fixtures

Write the resolved schema and records from Sections 3-6, plus a minimal fixture campaign and
request/response examples. Capture current direct predictions and the legacy APIs' behavior.
Choose the exact supplied adapter dependency list and serialize the new hydrology profile.

__Acceptance:__ YAML/JSON round trips are canonical; unknown/duplicate fields and invalid references
fail before execution; existing system/candidate YAML still loads; deep-copy tests prove that
specification inputs cannot mutate retained snapshots. No imports of optional BO/host packages.

### 2.2 Implement adapter lifecycle and independent scientific checks

Build the trusted adapter protocol, shape/unit/time checks, and both deterministic examples.
Exercise preparation, optional training, cleanup, and explicit state reset/continuity. Independently
recompute water balance from saved stores/fluxes rather than accepting a model-provided residual.

__Acceptance:__ adapter predictions match direct execution within declared numeric tolerance;
wrong units, shifted dates, missing temperature, invalid parameters, mutated inputs, and fabricated
zero-flow outputs fail the appropriate contract. Required unavailable checks block eligibility.
A physically invalid candidate cannot win on RMSE. No-winner outcomes remain valid results.

### 2.3 Implement event storage and identity-safe replay

Build the event store, artifact validation, lock, request digest index, and derived projection.
Use a pure reducer to reconstruct state from events. Add read-only inspection independent of
model imports. Implement bounded rejected-request records and repair accounting.

__Acceptance:__ byte-preserving refusal of incompatible resumes; deterministic replay; identical
responses for duplicate requests; conflicting IDs/stale revisions rejected; corrupt/gapped events
and symlink/oversized artifacts refused. Crash injection at every commit boundary either recovers
the one valid transition or stops visibly. Lost state projections rebuild without numerical work.

### 2.4 Implement reservations and supervised execution

Add physical attempt records, bounded process execution, timeout, cancellation inbox, and terminal
reconciliation. Keep the campaign lock and inbox ownership rules explicit. Record failures without
converting them into scientific scores.

__Acceptance:__ limits prevent an extra start; failed/uncertain work consumes its allowance;
retries cannot reset counts; timeouts and cancellation terminate owned descendants; a failed stop
is visible. Concurrent controllers cannot launch the same work. A new process does not kill an
unrelated reused PID. Cancellation while idle and while running both produce durable outcomes.

### 2.5 Connect immutable optimization child studies

Construct existing study/run records from the campaign's calibration clause and launch them through
the supervisor. Persist links and reservations before launch. Reconcile committed child results,
partial studies, and interrupted actions without direct ledger edits. Implement selection from
successful feasible child observations, then separate development comparison.

__Acceptance:__ bounded interruption/resume produces the same fitting selection as uninterrupted
execution when no physical result was lost. A saved result before acknowledgment is reused without
re-evaluation. An unknown physical outcome remains accounted for even when the child reports
zero cost. A changed candidate/policy creates a distinct child; unchanged inputs resume compatibly.
Existing optimization recovery tests pass without changed expected semantics.

### 2.6 Assemble controller, service, CLI, and reports

Wire the transitions and tools to the store, adapters, acceptance, and study bridge. Add invocation
limits that pause cleanly at legal boundaries. Generate reports from committed evidence and support
selection freeze plus explicitly disabled confirmation. Use scripted/manual role artifacts only.

__Acceptance:__ fixed replacement and parameter search reach a decision through the same public
contract; invalid candidates and unsupported recommendations are rejected; CLI JSON is parseable;
status/report commands trigger no model calls; a report includes failures and unknown costs. The
workflow can finish with retained baseline, no candidate, insufficient data, or no eligible model.

### 2.7 Run integration qualification and document the handoff

Exercise the new examples from fresh directories, interrupt at execution/commit boundaries, and
verify all reported numbers against artifacts. Use synthetic fixtures for the full fault matrix
and a small real-model run for numerical and recovery parity. Record source/lock identity, commands,
actual execution counts, tested platform, and skipped checks.

__Acceptance:__ the completion checklist below passes. Write the Part 3 handoff with the exact tool
schema, worker-visible artifacts, host permission requirements, and provenance hooks. State which
APIs are experimental. No new host, live-model comparison, or installed plugin is required to close
Part 2.

## 11. Verification and completion

Required tests cover observable behavior, not a copy of the implementation:

| Area | Discriminating cases |
| --- | --- |
| Specification | Duplicate YAML keys, unknown fields, false-as-zero limits, unsupported version |
| Interfaces | Same shape but shifted dates, same name but wrong unit, reordered coordinates, missing input |
| Lifecycle | Input mutation, state leaking between candidates, cleanup after preparation/run failure |
| Science | Attractive invalid model, unavailable required check, ineligible baseline, exact acceptance tie |
| Studies | Changed source/input/seed/space/policy, interrupted pending action, result saved before acknowledgment |
| Events | Torn temporary file, missing event, stale projection, modified result hash, response lost after commit |
| Concurrency | Two writers, stale revision, duplicate command during execution, cancellation while lock is held |
| Budgets | Failed attempt, uncertain cost, replay without extra charge, exhausted reservation, repeated invalid requests |
| Process control | Timeout, descendant process, supervisor death, reused PID, cancellation that fails to stop work |
| Data access | Fitting adapter receives no comparison labels; report-only access does not open private observation data |
| Compatibility | Legacy replacement retention unchanged, optimization artifacts untouched, optional imports remain optional |
| Reports | Reconstructed metrics, correct negative result, no confirmation claim from exposed development data |

Run focused tests after each affected increment. At integration completion run `pixi run lint` and
`pixi run test`. Run `pixi run -e bayes test-bayes` when an existing optimization interface or shared
helper changes and the environment is available. Record unavailable optional checks explicitly.
Do not launch or replace frozen benchmark matrices to validate this feature. Existing evidence may
remain bound to older source revisions; retain that provenance distinction.

Exercise macOS ARM64 and Linux x86-64 before claiming both platforms. If Linux execution is
unavailable, deliver the verified macOS implementation with Linux qualification outstanding rather
than inferring process/locking behavior. Windows support is outside this increment.

Part 2 is complete when:

- The fixed replacement and parameter-search paths use the same immutable identities, adapter
  lifecycle, acceptance rules, and result schema.
- The state machine and append-only campaign events recover correctly and preserve legacy child
  ledger semantics, including failure and uncertain-cost meaning.
- Hard scientific checks can veto a numerically attractive candidate, and missing required
  evidence cannot pass.
- Scientific execution counts, timeout, cancellation, duplicate requests, and bounded repairs are
  enforced with tested behavior.
- The local CLI and direct Python interface produce equivalent scientific decisions and reports
  from the same frozen example, including a valid negative outcome.
- Current guides and reproducible example commands describe what actually ran and what remains
  outside scope. Strict token enforcement and other-model support are documented deferred items.

The next work after this checklist is Part 3: attach bounded agent roles and a host integration to
the completed contract, capture dispatched prompts and resolved model identity, and evaluate their
usability. That work should not be folded into Part 2 merely because the contract can support it.
