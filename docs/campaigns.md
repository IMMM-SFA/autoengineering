# Local campaigns

The experimental `campaign` command evaluates supplied trusted model implementations through
admission, optional calibration, scientific acceptance, selection freeze, and reporting. The
Python broker is `autoengineering.campaign.controller.CampaignController`. No LLM or host SDK runs
inside the campaign package.

A fixed replacement and a parameter search produce `EvaluationRecord` and `DecisionRecord` objects
with full precision metrics. Required checks can veto an attractive metric. A missing or unavailable
required check prevents eligibility. An ineligible baseline cannot become a fallback selection.
The existing `improve` retention rule and `optimize` CLI keep their earlier semantics.

## Commands

Run from the repository root in Python 3.12 with the default Pixi environment:

```sh
pixi run autoengineering campaign validate examples/campaign_contracts/fixture.yaml
pixi run autoengineering campaign run examples/campaign_contracts/fixture.yaml \
  --workdir outputs/campaign-fixture --max-new-evaluations 1
pixi run autoengineering campaign status outputs/campaign-fixture --format json
pixi run autoengineering campaign resume outputs/campaign-fixture --max-new-evaluations 1
pixi run autoengineering campaign report outputs/campaign-fixture
```

`run` requires an absent or empty work directory. `resume` reads the stored resolved contract,
checks the original sources and copied bundle, and refuses incompatible scientific identity before
writing new evidence. `--max-new-evaluations` limits physical starts across the invocation. It
cannot expand a campaign or child-study budget. Paths under a symlink are refused. On macOS, use
`/private/tmp` when choosing a temporary output directory because `/tmp` is a system symlink.

`validate` resolves no executable import strings and runs no model. The source bundle root is
inferred from the enclosing repository. `--source-root` can identify that root explicitly for an
author-supplied specification elsewhere. It changes file resolution, not frozen scientific values.

`status` and `report` reconstruct committed evidence without opening private observation arrays,
importing scientific models, or using a network connection. Reports can still be read when the
original source bundle is unavailable. Progress goes to stderr. JSON commands produce one JSON
object on stdout.

A separate cancellation command deposits an intent without waiting for the event writer:

```sh
pixi run autoengineering campaign cancel outputs/campaign-fixture --request-id stop-1
```

The running supervisor consumes the intent and stops its owned process group. For an idle campaign,
`resume` consumes the queued intent and records cancellation. A queued intent is not proof of a
completed stop. Inspect the resulting campaign state and attempt receipts.

## Specification and trust

`CampaignSpec` version `1.0` rejects unknown fields, duplicate YAML keys, invalid references,
nonfinite values, malformed dates, and booleans used as integer limits. Python constructors copy
and freeze nested inputs. Canonical JSON sorts mapping keys and preserves list/parameter order.
Resolved defaults participate in scientific identity. Raw source/input hashes retain provenance.
The declared engine and supplied adapter bytes must match the executing package and registered
source locations. Copying a bundle does not authorize running a different installed implementation.

Author YAML declares model snapshots, exact scalar or aligned daily port contracts, data exposure,
allowed interventions, fixed fitting study/policy/space/budget, scientific checks, secondary
metric tolerances, process limits, and confirmation. Calibration uses `OptimizationRunSpec` rather
than a second optimizer language. The supplied adapters support deterministic studies with physical
execution cost units (`calls`, `physical_executions`, or `model_call`) and the existing validation
metrics. Unsupported noise/cost/outcome contracts fail validation. Registered checks use names and
versions, never YAML expressions.

The local registry supplies `linear`, `hydrology`, and `routing` adapters. Their factories are
application code. Requests cannot provide Python entries, shell commands, uploads, or arbitrary
file paths. Extending the registry requires a trusted implementation with a declared source closure.
Process separation supplies timeout, cancellation, cleanup and state isolation. It is not a security
sandbox. Trusted code can access files with its operating-system permissions.

Fitting adapters receive permitted forcing and optional fitting labels. Comparison labels stay
in the broker. The supplied hydrology adapter needs no training labels. A new parameter configuration
starts fresh model state. Continued forcing for that configuration preserves causal state across
splits. Exact units, coordinate order, dates, timestamp support, dtype and dimensions are required.
There is no implicit regridding, date joining, unit conversion, broadcasting or interpolation.

## Requests and replay

`campaign request WORKDIR` reads at most 64 KiB of UTF-8 JSON from stdin:

```json
{"schema_version":"1.0","campaign_id":"contract-fixture","request_id":"inspect-1","expected_revision":0,"operation":"state","payload":{}}
```

The envelope and response records are `Request` and `Response`. Operations are `state`,
`diagnostics`, `propose`, `admit`, `evaluate`, `review`, `freeze`, `confirm`, `cancel`, and `report`.
The broker stages supplied artifacts first. Mutating tools refer to their digest IDs:

| Operation | Required payload | Optional payload |
| --- | --- | --- |
| `state` | Empty | None |
| `diagnostics` | `artifact_id` | `repair_of` |
| `propose` | `proposal_id` | `repair_of` |
| `admit` | `snapshot_id` | `repair_of` |
| `evaluate` | `candidate_id`, `mode` (`fixed` or `calibrate`) | None |
| `review` | Empty | `evaluation_id`, `reconcile_attempt_id`, `repair_of` |
| `freeze`, `confirm`, `cancel`, `report` | Empty | None |

Responses carry a request ID, status, resulting revision, scalar result mapping, typed error,
and artifact IDs. Internal controller checkpoints can advance the revision several times while
one scientific request runs. Identical committed requests return the original response before
checking revision. Different content with the same ID conflicts. A new stale request executes no
model. Rejected commands and repairs persist. Restarting a caller cannot reset their allowances.
Invalid transport without a valid ID uses a separate bounded transport receipt.

The default service has no scientific authority. The trusted local broker enables scientific
handlers explicitly. These commands are not an API for arbitrary generated executable code.
Worker-facing errors contain neither tracebacks nor observation paths.

## Persistence and recovery

The writer commits individual canonical event files under `events/`, linked by hashes and revision.
Artifacts are immutable and verified. `state.json` is a derived projection. A missing or stale
projection is reconstructed from events. A gap, modified hash, changed result or missing committed
artifact stops replay. Interrupted temporary files are preserved during explicit recovery.

Child optimization ledgers retain their existing format. The campaign commits a `StudyLink` and
reserves the complete child allowance before constructing it. Each physical attempt has its own ID,
launch nonce and durable action receipts. Reserved capacity, confirmed attempts, measured cost,
and unresolved cost are separate. A failed or uncertain start keeps its physical allowance.

Recovery verifies that a process group is gone before accepting a saved result. A complete,
hash-verified result can be reused without another model call. Unknown work enters
`reconciliation_required` and prevents automatic starts. A trusted local caller can explicitly
acknowledge an uncertain attempt with `review` and `reconcile_attempt_id`. A verifiable surviving
group is stopped first. An unverified group or failed stop remains unresolved. Unknown cost stays
unknown even after acknowledgment.

The optimizer's optional `pending_result_resolver` accepts a verified result from the outer broker
through its public constructor. With no verified result, its established recovery behavior remains
an `infrastructure_failure` with zero child cost. That zero does not erase the campaign attempt or
its uncertain cost. No campaign code edits a child pending file or ledger.

## Outcomes and exit codes

Workflow progress and terminal outcomes are separate. Outcomes include `accepted_candidate`,
`retain_baseline`, `no_suitable_intervention`, `no_eligible_model`, `insufficient_data`, `invalid_task`,
`budget_exhausted`, `cancelled`, and `failed_execution`. Execution records preserve `success`,
`scientific_infeasible`, `model_failure`, `timeout`, and `infrastructure_failure`.

CLI exits are 0 for valid commands and valid scientific negative decisions, cancellation and budget
exhaustion; 2 for invalid requests/schema/store access; 3 for incompatible identity; 4 when a run
requires reconciliation; and 5 for a completed execution failure. A queued cancellation exits 0
and reports `queued`. It does not claim that active work has stopped. Request errors exit 2 and
return their typed error in JSON.

Selection freezes before confirmation. The exposed measured-data examples explicitly report
`confirmation_not_attempted`. The synthetic `eligibility-v1` confirmation protocol exercises one
additional eligibility evaluation, once. A failed confirmation cannot reopen model selection.

See the [example](../examples/campaign_contracts/README.md) and
[implementation progress](reviews/part-2-workflow-contracts-progress.md) for qualification status.
Token ceilings, provider portability, production investigator/implementer/reviewer roles, installed
host plugins, cloud workers and general model training remain later work. BO remains experimental.

## Qualification

The final macOS ARM64 qualification passed in `outputs/campaign-qualification-v3`: 38 direct and
38 CLI hydrology executions, two fixed routing references and two kernel parity oracles. The
current source identity matches the archived manifest. Two earlier rounds remain preserved, for
240 cumulative qualification executions within the 320 ceiling. See the
[verification record](reviews/part-2-workflow-contracts-progress.md) and
[completion audit](reviews/part-2-workflow-contracts-audit.md) for the evidence and limits.

The selected development model passes relative rules while NSE and KGE remain negative. This
qualifies the workflow, not general predictive adequacy. Linux and the optional bayes environment
remain unverified. Exposed data do not establish independent confirmation.

Stored immutable Markdown reports resolve links from their artifact directory. The `report`
command prints links relative to the campaign directory. To save its output with working links:

```sh
pixi run autoengineering campaign report outputs/campaign-fixture > outputs/campaign-fixture/report.md
```
