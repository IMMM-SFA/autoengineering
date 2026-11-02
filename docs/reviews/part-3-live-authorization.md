# Part 3 remaining live validation

Status: supplemental approval is pending for three additional cumulative host slots. The user
already selected `~/.codex/auth.json`, its recorded account and `gpt-6.1-sol`, and authorized the
destination and payload below. Six live calls remain charged, with zero scientific starts.
Compatibility fixes pass saved-response/native replay, all native qualification groups, 1,438
full-suite tests with 65 skips, and 171 focused tests in both source and wheel layouts. The fresh
runtime clocks and credential lease have not started. The original time and science ceilings stay
unchanged. Earlier proposal and rejection records below are historical.

## External destination and payload

The fixed worker sends HTTPS POST requests to OpenAI at
`https://chatgpt.com/backend-api/codex/responses`. The temporary OAuth bearer credential and
recorded account ID are sent in the `Authorization` and `ChatGPT-Account-ID` headers.

The request body contains `gpt-5.5`, role instructions, typed task/output contracts, allowed
task context, candidate configurations, evaluation metrics/check summaries derived from the
scientific runs, and permitted role handoffs/history. Raw weather/streamflow arrays and refresh
tokens stay local. No other external destination, proxy, account or automatic retry is selected.

The original approval request omitted this explicit destination and payload description. The
automatic reviewer rejected execution on that basis despite the approved run budget and cache
choice. Additional consent is needed for the egress described here; all original ceilings remain
unchanged. The rejection and source audit are recorded in `auto-review-egress-rejection.json`
under the evidence root.

The [original plan, section 11](../implementation-plans/part-3-multi-agent-system.md#11-bounded-development-comparison)
requires: "Use a new output root and a newly authorized budget." The bounded work below is needed
for the remaining host-conformance and measured-comparison acceptance items. Implementation
tests and authored fixtures do not establish those results.

## Frozen work

Run conformance first. Continue to the comparison only if the actual real-provider conformance
gate passes. Preserve failure evidence and stop if it does not pass.

| Stage | Physical host-call ceiling | Scientific-start ceiling | Elapsed ceiling |
| --- | ---: | ---: | ---: |
| Six provider-conformance cases | 16 | 2 public fixture starts | 720 seconds |
| Scripted Leaf River baseline | 0 | 38 measured starts | Within comparison batch |
| One-persona Leaf River route | 20 | 38 measured starts | Within comparison batch |
| Four-role Leaf River route | 20 | 38 measured starts | Within comparison batch |
| Comparison batch total | 40 | 114 measured starts | 1,800 seconds |
| Combined remaining work | 56 | 2 public + 114 measured starts | 2,520 seconds |

Each live comparison route retains sixteen tasks, four total repairs, at most two repairs for
one task, a 600-second worker-run ceiling and thirty seconds for one host invocation. One
trusted preflight interruption is charged inside each route's original twenty-call allowance.
The aggregate comparison limits remain thirty-two tasks and eight repairs. Transcript and
workspace ceilings are bound in the pinned batch specification. These are maximum allowances,
not promised usage or a token/dollar estimate. Unknown usage remains unknown.
Elapsed ceilings govern dispatch windows. Stop verification and reporting may finish later,
but they cannot authorize another call after the deadline.

No new Docker run is needed for fixture admission. The current standalone fixture registration
`92c7a82cad845a4a6fce7d5a1ef36231681be902913b6febdbee36640d0eabdd` verifies in source and
installed layouts using unchanged interface evidence and its original authored fixture review.
It makes no claim of human author approval, live source generation or new scientific results.

## Host and immutable inputs

The selected existing executable is
`/Users/cam/.local/lib/codex-no-clock/0.155.1/codex`, SHA-256
`26d4d42df9846aaeedce4a9c8c7cfa9e209fc8710fb2ab2b972a151c79463600`.
The requested model is `gpt-5.5` with subscription authentication. Availability, account access
and the actual resolved model remain unverified until the provider cases execute. There is no
model/account fallback or automatic refresh.

All roots below are under `/private/tmp/part3-native-runtime-20261027/`:

| Input | Root or file | Digest |
| --- | --- | --- |
| Qualified native profile | `/private/tmp/part3-output-contract-20261027/native` | `930c439fee16a72c5a5548522eefc83a2788f7d40987ee545d030bb19645d1ae` |
| Conformance preparation | `live-conformance-proposal/` | `5fae7c70181ca6831814b10d9b41c13f943e69f24e60d2eeed9db390307fcee9` |
| Comparison preparation | `live-comparison-proposal/` | `ee94e281ef1ab4d4a147d963dcc7a6a013143c272d0f85d40e75a48ecead1a01` |
| Host configuration | `live-host.toml` | `8bdc22ccd49858de09f88a82bc562137db31df2ebaf549fe0e4ac6931b49738e` |
| Original checked Leaf preparation | `/private/tmp/part3-matched-leaf-20261027/final` | `f054946aea8f072579350909c5307f313e253be27b40c5e00f6f436b5dc25934` |

The host configuration digest covers its parsed metadata. Other preparation/profile digests
use their respective canonical record contracts. The comparison captures all driver bytes and
the child preparations. The actual conformance runtime pin is created during that stage and
must be passed unchanged to the comparison. Its report, journal head and specification are
verified before the comparison clock starts.

The future runtime roots are `live-conformance-runtime/` and `live-comparison-runtime/`.
Both are absent. The existing private parent and separate roots preserve the original budgets
and prevent resuming an unrelated study. Commands, environment paths and source hashes are
recorded in `live-run-request.json` under the evidence root. Earlier pending-request versions
remain historical preparation records.

## Credential choice and timing

The dedicated lease destination is `live-lease/lease.json`, with lease ID
`part3-live-20261027`. Its parent is currently an empty owner-private placeholder. The marker
`lease-placeholder.json` records that no source read or lease preparation has been attempted.

The user selected the exact existing managed-cache file `~/.codex/auth.json` and its recorded
account for the one-shot helper. No other source may be discovered or substituted. Token values
and actual account IDs belong in the private lease, not chat or a public report. The source has
not yet been read because automatic review rejected the launch.

After authorization, the caller verifies the original placeholder marker, ownership, private
mode and empty directory. Only that untouched empty placeholder may be removed immediately
before the existing helper recreates its absent output. Any attempted, partial or nonempty
preparation requires stopping rather than resetting it. Source-cache contents remain unchanged.

The helper permits at most 900 seconds. That is shorter than the combined worst-case batch
deadlines. Each fixed worker requires enough remaining lease lifetime before its request.
Expiry can stop the run; there is no refresh, deadline extension, uncharged retry or permission
to create another study. Local lease checks do not prove server validity or actual token expiry.

## Evidence required afterward

Retain all calls, failures, repairs, owned-stop proofs, raw/normalized artifacts, observed model
and usage, physical science starts and replay receipts. Reports must distinguish physical host
starts, request intents and confirmed responses. A local stop does not prove remote computation
termination. Pending work blocks further dispatch.

The scientific controller retains selection authority. The data remain the exposed 2019/2020
development material, with the original warm-up/fitting/comparison splits and fixed seeds.
Measured confirmation stays `confirmation_not_attempted`. Baseline retention, failed candidates,
negative NSE/KGE and neutral/adverse role results remain valid evidence. One run establishes
feasibility and overhead, not general scientific benefit or role superiority.

The [acceptance inventory](part-3-completion-audit.md) remains the completion authority. Part 3
must not be marked complete until actual results satisfy the original seven increments.

## Authorized attempt and transport repair

The preceding preparation state is historical. The user approved the specified destination,
payload, managed cache and recorded account. The initial attempt stopped before reading the
cache because its parent directory was not private. The user then explicitly approved changing
only `~/.codex` from mode 0755 to 0700. The credential file remained mode 0600 and its contents
were unchanged.

The continuation prepared a 900-second lease and made one actual provider request. The text
case returned HTTP 400 and failed conformance. Local stop was verified, with no pending
reservations, zero science starts and no comparison runtime. The response body was not captured,
so neither the HTTP cause nor model/account compatibility is established. The expired generated
lease copy was removed after local stop. This does not claim server revocation.

Evidence remains under `/private/tmp/part3-native-runtime-20261027/` in
`live-conformance-report.json`, `live-continuation-result.json`,
`source-directory-permission-change.json` and `live-lease-cleanup.json`.

The request normalizer omitted top-level instructions that the native client had supplied.
The repaired worker supplies fixed trusted instructions without forwarding ambient client
context. It also classifies a bounded error body into fixed codes and parameter names without
retaining provider messages or reflected credentials. This is a tested compatibility repair,
not a confirmed explanation of the original HTTP 400.

Repair evidence and fresh preparation live under
`/private/tmp/part3-http400-repair-20261027/`. The original failed runtime, source pins and
budget charge remain intact. The repaired conformance cases permit at most thirteen new calls.
Including the previous charged call and the unchanged forty-call comparison allowance gives
at most fifty-four cumulative calls within the original fifty-six ceiling. Public science stays
at two starts and measured science at 114. A repaired launch must also retain the elapsed
allowance already consumed. Preparation does not read the cache or execute the provider.

The repaired bounded launch then executed under the existing user authorization. It stopped on
its first request with HTTP 400 and sanitized code `model_not_found` for `gpt-5.5`. No comparison
started. Total charges are now two host invocations and zero science starts. Both failed
runtimes and their original pins remain intact. The generated second lease copy was removed
after verified local stop without reading its contents. No fallback, refresh or automatic retry
occurred. Further live execution awaits the user's exact replacement model choice.

The user subsequently selected `gpt-6.1-sol`. Explicit catalog support and a pinned text-only
metadata copy allowed the unchanged 0.155.1 executable to pass all original native checks.
The cached model's Code Mode descriptor was explicitly disabled locally. The requested provider
model stayed unchanged. Catalog bytes and ambient native instructions are not forwarded.

Two bounded Sol text probes returned HTTP 200 but failed the strict response-header gate. The
last records encoding `identity` and content-type category `other`. There is no verified response
body, resolved model or usage. Total charged host calls are four, scientific starts are zero,
and neither comparison started. All failures and charges remain intact. Generated credential
copies were removed after verified local stop. Further execution is stopped. A fresh full
conformance run's thirteen-call worst case would reach seventeen cumulative conformance calls,
above the original sixteen ceiling, so it must not be launched with a reset allowance.

## Supplemental proposal after offline compatibility repair

The exact missing-MIME condition and the inert `response.metadata` event are now handled with
bounded parsing. Complete text/model/usage validation and all tool/privacy checks remain active.
The saved actual Sol response and a sandboxed native replay pass offline. The failed live gates
are unchanged. Six calls are charged, all temporary credential copies have been removed after
verified stop, and scientific starts remain zero. The final complete suite passed 1,438 tests
with 65 skips.

The proposed fresh roots are under `/private/tmp/part3-sol-final-live-20261027/`:

| Input | Digest |
| --- | --- |
| Native qualification | `5533596bbe49697d692c3b00814c7839afbd234ad483b80fc460676f321ea265` |
| Conformance preparation | `1b8b7a99a0e2ee3c127cdded9161d0d10c7af4d8086d262ee21405cde8120277` |
| Comparison preparation | `9e45d74b18aa750a04fb996956fc567c940a689dab76c81ddb710333c000c434` |

| Work | Host slots | Science starts | Dispatch time |
| --- | ---: | ---: | ---: |
| Prior failed attempts, preserved | 6 | 0 | 360 seconds, conservatively charged |
| Fresh full conformance | 13 maximum across fixed cases | 2 public | 360 seconds, enforced by supervisor |
| Conditional original comparison | 40 maximum | 114 measured | 1,800 seconds |
| Cumulative proposal | 59 | 2 public + 114 measured | 2,520 seconds |

This requires three additional cumulative host slots. The original time ceiling is unchanged.
The immutable conformance manifest retains its original local limits. The outer supervisor uses
only the remaining 360 seconds after conservatively charging prior attempts. No scientific
budget, criterion, held-out access, model/account choice, destination or payload scope changes.
There is no refresh, fallback, automatic retry or lease extension. The comparison still requires
an actual passing live conformance gate. The final full-suite result and execution-packet digest
are bound in the supplemental request. Source/profile/runtime pins remain immutable.

The reason for supplemental approval is the original
[plan, section 11](../implementation-plans/part-3-multi-agent-system.md#11-bounded-development-comparison):
"Use a new output root and a newly authorized budget." The selected account and model are
already authorized. The existing approval does not increase the original cumulative ceilings.

## Latest approved recovery outcome

The user approved packet `ed81950801876f02abde927ba67a7d98112c704d76a381493094774ec7ebb09c`
with cumulative ceilings of 60 host calls, three public science reservations, 114 measured
starts and 2,520 dispatch seconds. This attempt failed the frozen investigator eligibility
check after passing text and executing its baseline. Cumulative charges are ten host calls
and two public science reservations. Measured starts remain zero. No reservations are pending
and the temporary lease was removed. The failed response, gate and earlier charges remain.

The broker stop fix and prompt clarification change source identity. Earlier execution packets
cannot authorize that new source. A full fresh conformance run also needs two public starts,
while only one remains approved. No further live run or increased ceiling is inferred.

## Verified watchdog recovery request

The eligibility recovery packet was withdrawn after the full suite exposed a concurrent-stop
`PermissionError`. The corrected source now passes 1,444 default tests with 65 skips, 99
installed-wheel checks and fresh offline native qualification. All prior failed evidence remains.

The [replacement request](part-3-watchdog-recovery-live-request.md) binds packet
`24f28077a3cd16112bbafb7767c768a6cbc59c0b6c15f22d9dc2b5c0dbb873fc`. It requests cumulative
ceilings of 63 host calls, four public scientific starts and 2,820 dispatch seconds, adding
three calls, one public start and 300 seconds. The measured ceiling stays 114. Ten prior host
calls, two public starts and 720 conservative seconds remain charged. The same model, account,
destination, payload scope and frozen criteria remain. No actual approval file, credential
lease or live runtime exists for this replacement. Further live work requires user approval.

## Standing authorization applied after the user's blanket approval

The user then wrote, "I aprove all agentic calls to chat gpt", and resumed the goal. That
approval was applied to the exact replacement packet and its local public fixture prerequisites.
The run failed on reviewer citation formatting after seven host calls and two public starts.
It stopped cleanly and its lease was removed. A subsequent one-call review-only diagnostic,
with no new scientific execution, passed after clarifying the exact-name contract. A failed
local diagnostic setup made no provider call. All records and charges remain separate.

Standing approval covers the necessary agentic ChatGPT validation workflow for this goal, with
the selected account/model/destination and approved payload classes. New attempts still receive
fresh output roots, fixed limits and immutable records. The operator derives and records each
new cumulative allocation rather than requesting approval for each ChatGPT call. This is an
interpretation of the user's blanket instruction, not a claim that the user separately supplied
each numerical ceiling. It does not authorize a different account, provider, model, new measured
study, relaxed criterion, refresh, fallback or mutation of old budgets.

The next bounded allocation is 71 cumulative host calls, six public starts and 3,180 dispatch
seconds, including all eighteen prior calls, four public starts and 1,080 conservative seconds.
Each fresh conformance attempt still allows thirteen case calls and two public starts. Comparison
still requires actual passing live conformance and retains forty calls and 114 measured starts.
No current attempt or old ledger is expanded during resume.

## Current executed accounting and pending scope

The subsequent approved fresh conformance passed all six cases. Its conditional measured
comparison failed after 94 starts: scripted 38, single-agent 38 and four-role 18. Cumulative
charges are 47 host calls and six public reservations. There is no pending work and the lease
was removed. The four-role route selected no outcome because its reviewer lacked calibration
configuration bindings. All earlier failures and charges remain intact.

The corrected common summary has passing focused, installed and offline native checks. Full
verification is running. A one-call diagnostic on already captured aggregate Leaf evidence
was rejected twice by automatic approval review before execution. The reviewer requires direct
approval for this specific payload despite the earlier authorization record. A clarification
asks about candidate configurations, aggregate metrics/checks and role handoff sent to the
same ChatGPT endpoint using the same selected account. Raw arrays stay local. No call or
credential read occurred in either rejected launch.

A fresh matched preparation is under `/private/tmp/part3-calibration-context-20261027/fresh-study/`.
It preserves all scientific criteria and needs 114 new measured starts, making the proposed
cumulative ceiling 208. The requested increase is 94 slots above the original 114 ceiling,
including the 20 original unused slots. This measured-budget increase remains unauthorized.
Standing ChatGPT-call approval does not supply it. Both the original failed study and its
94 charged starts remain counted. No live runtime or lease has been created for the new study.

Current source verification is now complete: 1,452 default tests pass with 65 skips, all 238
installed checks pass, and eleven mock operator fixtures pass. The unchanged source snapshot,
qualified native profile, current wheel, exact preparations and operator are bound in
`/private/tmp/part3-calibration-context-20261027/fresh-study/execution-packet.json`. With no
new diagnostic charge, the proposed cumulative allocation is 100 host calls, eight public
reservations, 208 measured starts and 5,280 dispatch seconds. New numerical authority and
the direct payload clarification remain pending. No actual authorization file was created.

The user subsequently replied "approved" to both pending questions. Specific payload consent
and the increase to 208 cumulative measured starts are now authorized. The captured review
diagnostic completed with one host charge, zero science and verified full provider proof.
Its lease was removed after verified stop. The original reviewed packet remains preserved.
The executing packet `94e84e72f6bc587a65ed1f92b65e7bdadda652c3a65f801c6898684d5ca357fd`
includes that one call and 60 conservative seconds in prior accounting: cumulative caps are
101 host calls, eight public reservations, 208 measured starts and 5,340 dispatch seconds.
No scientific criterion or measured allocation changed after approval. Fresh conformance is
running, with comparison conditional on its complete actual pass.

The executing calibration-context attempt subsequently failed only its malformed case: the
model returned a valid handoff instead of the required intentionally invalid payload. Five
cases passed. All 12 host calls and two public starts remain charged, with verified stop,
no pending work and its lease removed. Comparison did not start. Cumulative usage is now
60 host calls, eight public reservations and 94 measured starts. The approved measured ceiling
remains 208 with 114 unused starts.

The initial probe prompt was contradictory. Its corrected host supplies the intentionally
invalid diagnostic contract on the first call and the ordinary role contract on repair.
The fixed invalid payload, actual provider-proof requirement, strict parser and one-repair gate
are unchanged. The fresh attempt receives a new preparation/root after source verification.
Standing approval covers its required calls and local public prerequisites. Operator-derived
cumulative caps are 113 host calls, ten public reservations and 5,640 dispatch seconds. This
adds no measured authority and does not expand or reopen a resumed ledger.

The user approved the later 39-slot request. Its exact packet is
`51c164c22488348e503c178b52ba6f2b36d76d6df81c6119e1cc27556672e640`, under
`/private/tmp/part3-proposal-context-20261027/fresh-study/`. The measured ceiling is now 247,
including all prior 133 starts. Cumulative host/public/dispatch caps remain the prepared
131 calls, twelve public reservations and 7,800 seconds. Current-source actual conformance
passed all six cases before the matched comparison started. Earlier failed matrices, public
reservations with unknown costs and all host charges remain preserved.
