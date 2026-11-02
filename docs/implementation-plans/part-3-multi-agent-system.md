# Part 3 implementation plan: a bounded multi-agent system

__Status:__ proposed implementation plan. No live worker campaign, installation, new scientific
qualification, or generated-code execution is authorized by this document.

__Parent:__ [Development plan, Part 3](../development-plan.md#3-implement-a-small-multi-agent-system).
__Starting point:__ the `agentic-architecture` branch at `b393726`, the
[Part 2 audit](../reviews/part-2-workflow-contracts-audit.md), and the
[campaign handoff](../part-3-campaign-handoff.md).

## 1. Deliverable and boundaries

Add four bounded agent roles above the existing deterministic campaign controller. Deliver a
serial workflow that diagnoses the Leaf River development case, proposes an allowed intervention,
prepares its implementation handoff, requests calibration and evaluation, obtains an independent
review, and produces a reproducible evidence report. The controller decides scientific eligibility
and selection. A valid workflow may retain the baseline or find no eligible intervention.

Use the existing Codex subscription prototype as the starting host integration. Replace its ad hoc
runner with a supervised, versioned adapter. Verify the installed host's actual capabilities during
implementation before choosing invocation options. The historical host inventory is evidence of
the Part 1 environment, not a current compatibility guarantee. Keep host dependencies outside
`autoengineering.campaign`, `autoengineering.adapters`, and base package imports.

Deliver the supplied-implementation path first. A second increment lets the implementer produce
code in an isolated workspace, but admission requires a separately tested execution boundary and
a trusted registration step. Completing the supplied path alone does not satisfy the development
plan's generated-implementation requirement. Track the two outcomes separately.

| Include | Defer |
| --- | --- |
| Orchestrator, investigator, implementer, reviewer | Parallel candidate execution and distributed workers |
| One production host adapter and deterministic fake host | Other models/providers and a second live host |
| Strict role handoffs, artifact permissions, invocation history | Strict token ceilings and inferred subscription dollar costs |
| Serial dispatch, bounded repairs, interruption and cancellation | A custom agent runtime, web app, and automatic ML training |
| Supplied adapters, followed by gated generated-code admission | Open-ended architecture changes and arbitrary dependencies |
| Matched single-agent and four-role development pilots | General scientific utility or superiority claims |

Other-model support and strict token enforcement remain deferred from Part 2. Preserve unknown
usage as null and disclose that an observed-token stop cannot guarantee an in-flight token ceiling.
Do not revive a failed BO gate or reuse the nearly consumed Part 1 execution allowance.

## 2. Reuse the current scientific boundary

| Existing interface | Part 3 use | Contract to preserve |
| --- | --- | --- |
| `campaign.records.Request` / `Response` | Exact version `1.0` envelope at the broker boundary | 64 KiB requests, strict fields, revisions and replay |
| `CampaignController.stage_record` | Trusted staging of validated proposals and snapshots | No arbitrary worker upload, executable entry, or path endpoint |
| `CampaignService` | Execute permitted scientific transitions | Default service grants no scientific authority |
| `CampaignController` | Baseline, admission, evaluation, review, freeze and confirmation | Deterministic acceptance and single scientific writer |
| `campaign.store` / `artifacts` | Immutable evidence and bounded verified reads | Hash verification, confinement, append-only events |
| `StudyLink` / `AttemptRecord` | Scientific lineage and physical execution accounting | Separate child studies, reservations, attempts and unknown cost |
| `campaign.execution` / `runtime` | Reference for owned process supervision | Cancellation receipts and reconciliation before new work |
| `adapters.contracts` | Exact model interface and lifecycle | Units, time support, state, data access and source identity |
| `examples/campaign_contracts` | Deterministic fixtures and Leaf River task definition | Existing data exposure, acceptance and scientific limitations |
| `scripts/agentic_architecture_workers.py` | Historical host behavior reference | Preserve its source and evidence rather than rewriting the prototype |

Scientific operations and their payloads remain those documented in
[campaigns.md](../campaigns.md#requests-and-replay). Worker tools are a narrower facade over these
operations. Do not expose the full campaign CLI, state artifacts, or `stage_record` to a worker.

The current Part 2 source closure includes package sources. Before adding agent modules, test how
that closure is constructed. New worker prompts or host code must not become scientific inputs
merely because they share a package directory. Use an explicit scientific closure for new profiles,
and record the host closure separately. Preserve old manifests and their original resume checks.
If a shared scientific module changes, create a new scientific identity instead of disguising it
as a host-only change.

## 3. Proposed package and interface layout

Paths below describe new work, not shipped modules.

| Path | Responsibility |
| --- | --- |
| `src/autoengineering/agents/records.py` | Frozen run, task, invocation, handoff and review records |
| `src/autoengineering/agents/store.py` | Worker journal, immutable transcripts, replay and reservations |
| `src/autoengineering/agents/permissions.py` | Role operation policy and explicit artifact grants |
| `src/autoengineering/agents/broker.py` | Resolve allowed summaries, validate role outputs, dispatch campaign requests |
| `src/autoengineering/agents/scheduler.py` | Serial role lifecycle, bounded repair, stop and recovery |
| `src/autoengineering/agents/hosts/base.py` | Host protocol and capability receipt |
| `src/autoengineering/agents/hosts/fake.py` | Scripted responses and failures without live model calls |
| `src/autoengineering/agents/hosts/codex.py` | First optional host process adapter |
| `src/autoengineering/agents/workspaces.py` | Scoped candidate workspaces and immutable patch capture |
| `src/autoengineering/agents/admission.py` | Trusted promotion of qualified implementation bundles |
| `src/autoengineering/agents/report.py` | Worker evidence linked to deterministic scientific reports |
| `src/autoengineering/agents/prompts/` | Versioned role templates included in package data |
| `src/autoengineering/agents/command.py` | Experimental CLI facade with lazy imports |
| `examples/agent_campaign/` | Fake-host smoke workflow, live run template and comparison driver |
| `tests/test_agent_*.py` | Contracts, permissions, host lifecycle, recovery and end-to-end tests |

Reuse canonical serialization and safe artifact utilities where their public contracts fit.
Extract shared helpers only with regression coverage. Do not copy the optimizer or build another
scientific state machine. The worker journal records orchestration and references campaign events;
it cannot replace or edit those events.

Proposed commands belong under `autoengineering agents`: `validate`, `run`, `resume`, `status`,
`cancel`, and `report`. These names are design targets. `run` takes an agent-run file, an explicitly
selected campaign, and a fresh worker directory. `resume` uses the stored identities and original
limits. `status` and `report` require neither host credentials nor scientific imports. Keep JSON
stdout machine-readable and progress on stderr. Package entry points and command documentation
are added only with their implementation tests.

## 4. Versioned records and identities

Use frozen records with strict deserialization, canonical JSON, explicit schema versions and deep
copies of nested inputs. Reject unknown fields, duplicate keys, invalid references, nonfinite
numbers, boolean limits, oversized envelopes and unsupported versions before launching a worker.

| Record | Required content |
| --- | --- |
| `AgentRunSpec` | Campaign identity, host/auth mode, requested model, role templates, permitted interventions, tool policy, resource limits, source/environment identities, execution mode |
| `TaskAssignment` | Stable task ID, role, parent task, campaign revision, bounded question, input artifact grants, expected result schema, allowed operations, deadline, repair allowance |
| `WorkerInvocation` | Unique physical invocation ID, task/attempt IDs, exact prompt artifact, host version, requested and resolved model, policy digest, launch receipts, raw response, normalized output, timing and supplied usage |
| `RoleHandoff` | Task/invocation IDs, role, status, typed output, supporting artifact IDs, unresolved issues, proposed next action, superseded handoff when repaired |
| `ReviewFindings` | Candidate/evaluation IDs, evidence digests, findings with severity and supporting checks, missing evidence, advisory recommendation |
| `ImplementationBundle` | Base snapshot, patch/source digests, allowed files, dependencies, interface results, execution-boundary receipt, admitted implementation identity if promoted |
| `ArtifactGrant` | Run/task/role scope, immutable artifact or derived summary ID, allowed operation, maximum bytes, visibility classification |

Keep three identities distinct: the logical task, each physical host invocation, and each campaign
request. A transport retry reuses the exact campaign request envelope. A fresh LLM call creates a
new invocation and consumes its allowance even when its task is unchanged. Changed handoff content
creates a new handoff and, if submitted, a new request with `repair_of` where supported.

Persist the resolved prompt before dispatch. Save raw host output before parsing, then retain the
normalized output or parse failure. Store private raw transcripts separately from worker-readable
summaries. Prompts and transcripts must never contain authentication material. Record credentials
only by authentication mode, never by value. Unsupported model resolution is an explicit incomplete
provenance outcome, not permission to invent a resolved model name.

Host metadata is separate from scientific provenance. A host change creates a new worker-run
identity linked to the campaign and may reuse unchanged scientific evidence. It cannot silently
resume a worker run under different prompts, model, permissions or limits.

## 5. Role behavior and authority

| Role | Inputs | Required output | Authority |
| --- | --- | --- | --- |
| Orchestrator | Safe campaign projection, task history, available allowances, decision reasons | Bounded task assignment or next-step recommendation | Requests permitted broker actions; cannot alter science or budgets |
| Investigator | Approved diagnostics, interface summary, admitted implementation catalogue, supplied sources | Falsifiable candidate brief, evidence, expected tradeoffs, eligibility gaps | Reads granted summaries and proposes within allowed interventions |
| Implementer | Approved brief, public interface specification, scoped source workspace, fitting fixtures | Supplied-adapter configuration or versioned implementation bundle and checks | Edits only candidate workspace when its mode permits it |
| Reviewer | Immutable proposal, implementation/check receipts, approved evaluation summaries | Evidence-linked findings and advisory disposition | Cannot modify candidate code or issue scientific acceptance |

The deterministic scheduler validates the orchestrator's recommendations. It can reject an illegal
assignment without consulting another LLM. Activate roles only when the campaign needs their output.
Do not keep idle agents running, and do not ask a reviewer to repeat an already complete review
without changed evidence or a recorded repair reason.

Run the reviewer in a fresh context with no implementer scratch history. Its input includes the
submitted rationale and exact artifacts needed to challenge it. Independence means a separate
invocation, permissions and evidence review, not statistical independence from using another model.
Reviewer prose never replaces required executed checks. A blocking finding pauses admission or
freeze until resolved or explicitly disposed of by a trusted caller with a recorded reason. A
favorable review cannot override an ineligible scientific result.

The investigator initially works from supplied, provenance-bearing sources. Treat source text and
candidate comments as untrusted content. They cannot grant tools or change instructions. Live
literature retrieval can be added through a bounded source broker, with its own access policy,
query/fetch limits and retained sources. A missing source remains a gap rather than a fabricated
citation. No general browser or shell is required for the supplied-adapter pilot.

## 6. Serial execution and handoff validation

1. Validate the agent-run specification and campaign identity. Check the host capability receipt,
   execution boundary and remaining allowances before creating a dispatch reservation.
2. Let the trusted controller validate/evaluate the baseline and prepare permitted diagnostics.
   If the campaign cannot proceed, report its outcome without calling an agent.
3. Ask the orchestrator for the next bounded assignment. The scheduler checks current scientific
   state, allowed role, intervention and task budget before dispatch.
4. Ask the investigator for a candidate brief. Check its target and implementation against the
   allowed catalogue and resolve every evidence reference through the artifact policy.
5. Stage a valid `CandidateProposal` through the trusted broker. Submit the exact `propose` request
   once and preserve its envelope and response. Unsupported ideas remain research artifacts.
6. Ask the implementer for the supplied configuration or an isolated implementation bundle. The
   broker constructs the `CandidateSnapshot` only from admitted sources and checked interfaces.
   Worker text cannot choose an import path or self-certify source closure.
7. Submit `admit`, then `evaluate` with the allowed mode. The controller owns physical reservations,
   fitting and evaluation. Workers receive only permitted evidence summaries.
8. Ask the reviewer to inspect the candidate and evaluation evidence. Save findings independently
   of the controller's `review` operation, whose existing payload does not accept reviewer prose.
   After required findings are resolved, the broker requests deterministic review.
9. Continue with another bounded candidate or request `freeze` according to the controller's legal
   transitions and remaining budget. `confirm` is allowed only by the frozen campaign contract.
10. Generate the scientific report and the worker report. Link the complete task/invocation/request
    history, unresolved findings, costs, failures and confirmation status.

Each handoff validator checks schema, task identity, role, revision context, permitted action,
artifact grants, candidate identity and evidence consistency. Validation failures consume the
persistent repair allowance. A repair receives the specific error and permitted evidence, with a
new invocation ID. The default proposed allowance is at most two repairs for a logical role task,
also bounded by a run-wide cap frozen in the run file. Exhaustion stops that task visibly.

Task-level repairs do not reset campaign reject/repair limits. A stale campaign revision triggers
a safe state refresh, never a blind replay with a changed revision. If a committed response was
lost, resubmit the original request unchanged and obtain its original response first.

## 7. Artifact permissions and execution boundaries

Use a deny-by-default broker policy. A digest is an identifier, not an access capability. Check
the requesting run, task, role, artifact visibility and byte limit on every read. Derive worker
summaries from an explicit allowlist of fields. Do not serialize controller state and redact a few
known fields afterward.

Keep comparison labels, final holdout arrays, private source caches, child work directories,
controller checkpoints, process logs and unredacted source paths evaluator-owned. Approved
fitting diagnostics and scalar acceptance summaries may be shared. Record their exposure so later
reports cannot describe previously inspected data as independent confirmation. Read-only worker
views must not transitively expose private artifacts through links or nested IDs.

Treat two execution boundaries separately:

- __Host worker boundary:__ the agent sees only its staged brief, allowed summaries and candidate
  workspace. Block access to every checkout and evaluator directory, ambient credentials beyond
  the required host authentication, unapproved tools, and unrelated network destinations. The
  host connection itself may need network access. Verify the effective boundary outside the prompt.
- __Generated implementation boundary:__ execute untrusted candidate code with explicit resource
  limits, no network, no controller/evaluator mounts, no credentials and no child-study writes.
  Permit only declared inputs and a bounded output channel. Candidate outputs and logs are
  untrusted and require size, type, shape and finite-value checks before use.

Part 2's POSIX subprocess supervision is lifecycle control, not either security boundary. Select
an available OS/container mechanism during implementation and qualify it on each claimed platform.
If an enforceable boundary is unavailable, generated execution remains blocked. Do not downgrade
to the trusted Python runner or describe a read-only checkout as protection from private reads.

For code production, create a workspace from an explicit source allowlist. Protect acceptance
rules, evaluator code, data splits, environment locks, host prompts and scientific records. Reject
symlinks, traversal, undeclared files/imports, binary payloads and dependency changes outside the
frozen policy. Snapshot candidate bytes before testing and verify those same bytes at admission.
Capture the patch even when tests fail. Never execute a worker-supplied test command verbatim.

Start with one small permitted component adapter and a fixed dependency set. A trusted admission
step reviews the source closure and boundary receipt and creates a registered adapter identity.
If the frozen campaign does not already permit that implementation, create a new campaign linked
to the originating proposal. Do not expand `allowed_interventions` or replace sources in a resumed
campaign. Full automatic admission of arbitrary code is outside this delivery.

## 8. Resource accounting, interruption and recovery

Freeze limits for physical host invocations, tasks, repairs, elapsed run time, individual worker
time, transcript bytes and candidate workspace size. Enforce scientific execution allowances in
the existing campaign controller. Track these counters separately; LLM retries cannot replenish
model-call capacity, and a reused scientific result does not imply a free new host invocation.

Reserve an invocation before launching it. Record a launch nonce and owned process identity, then
persist raw output, parsed handoff and completion receipt. A worker invocation has explicit states
such as `reserved`, `running`, `completed`, `invalid_output`, `timeout`, `cancelled`,
`host_failure` and `reconciliation_required`. Unknown usage stays unknown after timeout or crash.
Observed-token thresholds can stop the next call but remain advisory to an in-flight call.

Use a worker-run writer lock and an append-only journal. Only the trusted broker writes scientific
events. Do not hold the worker journal lock throughout an LLM call or numerical evaluation. Commit
dispatch intent first, perform the external action, and reconcile its receipt afterward. Recovery
must handle every gap without assuming an atomic transaction across the two journals.

| Interruption point | Required recovery |
| --- | --- |
| Reservation before provable launch | Reconcile launch receipts; unresolved work retains its allowance |
| Worker launched, output missing | Stop or identify the owned process; no automatic replacement call while ownership is uncertain |
| Raw output saved, parsing incomplete | Parse the saved bytes without a new model invocation |
| Handoff valid, campaign request not acknowledged | Replay the identical persisted request and reconcile the committed response |
| Campaign committed, worker journal not updated | Reconstruct the link from request ID and response, without scientific execution |
| Scientific attempt unresolved | Preserve campaign reconciliation state; worker cannot acknowledge unknown physical work |
| Cancellation queued | Report queued intent until process-stop and campaign receipts establish the outcome |

Cancellation has an independent inbox. A run cancellation stops further dispatch, cancels the
owned host process group, and forwards campaign cancellation when scientific work is active.
Expose worker and scientific stop states separately. A dead host process does not prove its
scientific child work ended. Failed or unverifiable stops require reconciliation.

## 9. Implementation increments and acceptance gates

Implement in dependency order. Each increment should be reviewable without a live model call.

| Increment | Work | Acceptance gate |
| --- | --- | --- |
| 3.1 Contracts and fake host | Records, run loader, role schemas, host protocol, deterministic fixtures | Strict round trips, immutable nested values, rejected malformed input, base imports without host SDK/network |
| 3.2 Worker journal and permissions | Invocation reservations, immutable raw/normalized artifacts, grants and safe summaries | Replay after commit faults; private artifacts and cross-task reads denied; unknown usage preserved |
| 3.3 Serial broker and roles | Task scheduling, four prompts, supplied proposal/snapshot handoffs, bounded repairs | Fake-host supplied-candidate workflow reaches the same scientific decision as the direct path |
| 3.4 Host lifecycle | First host adapter, authentication-mode checks, capability receipt, process ownership and cancellation | Fake executable fault suite plus separately authorized real-host conformance on the qualified platform |
| 3.5 Candidate implementation | Scoped source workspace, patch capture, sandbox qualification and trusted registration | Valid small adapter admitted under a compatible new identity; malicious/invalid candidates rejected before scientific use |
| 3.6 CLI and evidence reports | CLI commands, package data, read-only status, report links, install/use instructions | Script/CLI parity, installation smoke in a disposable environment, report reconstruction without host/science access |
| 3.7 Leaf River development pilot | Frozen single-agent/four-role comparison, interrupted worker, invalid candidate | Complete evidence, no allowance overrun, deterministic decisions, explicit negative outcomes and development-only limits |

Begin 3.5 boundary design during 3.2, but do not launch generated code before its gate. The supplied
path can be qualified while generated admission is blocked. In that case report partial Part 3
completion and name the missing boundary. Do not mark the whole parent requirement complete.

The first host integration is a maintained CLI/JSON adapter. Installing a plugin is a separate
packaging choice, not evidence implied by a passing local runner. A second live host remains
deferred. The fake host proves contract separation, not real provider portability. Revisit a custom
runtime only after recording a concrete requirement that the chosen integration cannot satisfy.

## 10. Verification matrix

| Tests | Required cases |
| --- | --- |
| Contracts | Unknown/duplicate fields, oversized JSON, nonfinite values, invalid identities, deep immutability, prompt/model digest changes |
| Role permissions | Investigator attempts `evaluate`, implementer changes acceptance, reviewer edits code, orchestrator expands budget, fabricated evidence IDs |
| Artifact mediation | Private label digest, nested private reference, cross-task grant, traversal, symlink, source-path leakage, oversized artifact |
| Prompt injection | Source text and candidate comments request privileged tools or reveal data; broker grants remain unchanged |
| Handoffs | Wrong role/task/candidate, stale revision, unsupported action, missing citations, malformed output, repair exhaustion across restart |
| Host adapter | Missing executable, unsupported capability, authentication mismatch, model identity missing, partial JSON, nonzero exit, truncated transcript |
| Worker accounting | Duplicate dispatch, timeout, failed launch, unknown usage, restart at limit, child process survives parent, cancel while writer busy |
| Scientific recovery | Lost response after commit, exact-envelope retry, conflicting ID, unresolved physical attempt, no duplicate model start |
| Generated code | Label read, network attempt, evaluator write, fork/resource exhaustion, output flood, symlink escape, altered dependency, changed bytes after qualification |
| Scientific authority | Reviewer contradicts checks, attractive infeasible model, no eligible baseline, failed confirmation, attempted selection reopening |
| Reporting | Missing/corrupt evidence fails visibly; private data absent; links resolve; raw and normalized outputs distinguished; no new model calls |

Use fake executables and deterministic fixtures for the default suite. Live tests require a
separate explicit command and never run from ordinary `pixi run test`. Contract assertions should
measure actual permissions and process outcomes, not whether a prompt contains a prohibition.

After each increment, run its narrow tests. Before integration run `pixi run lint` and
`pixi run test`; run the optional Bayesian suite only where installed and affected. When using
the existing main-checkout environment from a linked worktree, explicitly select that worktree's
`src` and verify the imported package path. Do not accidentally test the main branch's package.

Qualify macOS ARM64 first, matching Part 2's verified platform. Linux process, filesystem and
execution-boundary checks need their own evidence before a support claim. Preserve skips and
unverified platforms. Ordinary verification does not rerun the old frozen benchmark matrices or
consume Part 1/Part 2 scientific qualification budgets.

## 11. Bounded development comparison

Before any live dispatch, save a resolved run manifest with concrete candidate, host-invocation,
repair, elapsed-time and scientific execution ceilings. Select the exact model/authentication
mode and retain all prompts and capability checks. Use a new output root and a newly authorized
budget. No placeholder limit is executable, and this plan does not choose paid compute or install
a host on the user's behalf.

Start with three routes over the same supplied candidate pool:

1. Deterministic scripted broker, to establish scientific and tool-contract parity.
2. One agent with the same tools, data visibility, allowed candidates and total allowances.
3. Four serial roles with the same aggregate allowances and scientific rules.

Freeze independent campaign identities, common fitting seeds, candidate pool, ordering rules and
comparison metrics before running. A role comparison must not obtain extra calibration calls or
private feedback. Count diagnosis, research, invalid calls, retries, calibration and review in the
relevant totals. Report fresh and replayed work separately. Seeded science does not make LLM calls
reproducible; distinguish replay of saved decisions from a new live run.

Use the current Leaf River data only for development. Its fitting/comparison/exposure history
remains unchanged and measured-data confirmation remains `confirmation_not_attempted`. Do not
turn exposed 2020 data into a new holdout. Preserve the finding that a relatively accepted model
can still have negative NSE/KGE. A reproducible agent report must carry those limitations.

Measure workflow completion, valid handoffs, correctly rejected candidates, recovery, human
interventions, physical model calls, wall time, host calls and observed usage. Also report the
controller's objective, scientific constraints and selected implementation. Do not collapse human
effort, subscription usage and scientific quality into a fabricated monetary score.

A first authorized smoke needs one complete live four-role path, one worker interruption/recovery,
and one deliberately invalid candidate. The invalid candidate must be rejected for the intended
reason without weakening acceptance. A matched live single-agent comparison is required before
claiming the role split has demonstrated practical value. Repeated comparisons and role-removal
studies require a separately frozen affordable design; one successful run establishes feasibility
only. Record a neutral or adverse outcome if role overhead buys no measured benefit.

Generated-code value needs a separate comparison after 3.5: distinguish a fixed candidate pool
from newly generated implementations. Otherwise a larger search space could be mistaken for a
benefit of multiple roles. Broad utility and independent confirmation remain Part 5 work.

## 12. Completion record and documentation

Publish a local implementation audit mapping every increment to tests, artifact paths, source
hashes and platform evidence. Include completed, blocked, deferred and not-attempted rows. Part 3
completion requires all seven increments, including the generated-code boundary and authorized
Leaf River evidence. A supplied-adapter release can ship earlier with that narrower scope stated.

Update `docs/campaigns.md`, add an agent-workflow guide and example README, and link both from the
documentation index. Update CLI documentation contracts and the development plan's status only
after verification. Keep historical Part 1 and Part 2 sources, protocols, evidence and limits intact.

The final report must answer: which roles ran, which host/model actually ran, what each role could
access, what failed or was repaired, whether physical work was duplicated, how much allowance was
used or remains unknown, why the controller selected or rejected the candidate, and whether any
independent confirmation occurred. A narrative from an agent is not evidence for these answers.
