# Part 3 implementation progress

Part 3 is incomplete. Work is in the existing `agentic-architecture` worktree. The original
[implementation plan](../implementation-plans/part-3-multi-agent-system.md) remains the acceptance
contract. The supplied path alone will not satisfy it.

| Increment | Current state | Evidence or missing work |
| --- | --- | --- |
| 3.1 Contracts and fake host | Initial implementation, focused tests passed | Strict records, JSON loader, typed role outputs, immutable nested values, scripted host and lazy base imports in `tests/test_agent_contracts.py`. A complete audit of all nested bundle/review contracts remains. |
| 3.2 Journal and permissions | Scripted path implemented | Hash-linked journal, creation-time clock, host source/runtime identity checks, immutable raw/normalized/parse artifacts, scoped grants, approved summaries, exact campaign requests and scientific receipts. Uncertain live-host reconciliation remains with 3.4. |
| 3.3 Serial broker and roles | Scripted supplied path verified | Four serial roles, legal orchestrator assignments, trusted staging, bounded domain repairs, independent review and explicit trusted dispositions. Tests cover scientific decision parity, lost responses/staging acknowledgments, ineligibility and cancellation. Live-host evidence remains unqualified. |
| 3.4 Host lifecycle | Native boundary qualified offline; six conformance handlers implemented | Nineteen permission checks, all nine profile groups and owned SDK/journal recovery passed with the exact 0.155.1 binary. All six handlers have authored unit evidence. The unmodified owner-loss handler also has actual native evidence before credential preflight. An actual native reply without fixed-provider proof is rejected. Other partial gaps, real-cache compatibility and authorized real-provider conformance remain. |
| 3.5 Candidate implementation | Fake-host source handoff, trusted registration and linked campaign verified | Version 1.1 source responses, capture before checks, preserved failures, check reservations/recovery, pinned review, new frozen profile and budget, explicit origin lineage and separate reviewer context. Production host isolation and live generation remain pending. |
| 3.6 CLI and reports | Native configuration, batch accounting and conformance preparation verified offline | Thirteen commands include pinned proposal capture/inspection, conformance run/resume and read-only status. A shared ledger spans native and scientific starts. Actual native-profile CLI/batch/preparation checks passed. Scientific installation smoke requires an explicit source bundle. All six handlers and public dispatch are implemented offline. Real-provider conformance remains not attempted. |
| 3.7 Leaf River pilot | Fresh Leaf preparation and authored three-route driver verified; live pilot not attempted | All three synthetic routes completed 38 starts with the same scientific selection. Replay, static interface rejection, bounded repairs and acknowledgment recovery passed. The native comparison path, conformance/account binding, native interruption within its ceilings and authorized measured-data evidence remain. |
| Additional hosts, parallel workers, strict token ceilings | Deferred by plan | Fake-host tests do not establish provider portability or in-flight token ceilings. |
| Linux platform qualification | Unverified | No Linux process or sandbox evidence was collected. |

## Current implementation evidence

The worker tests exercise actual artifact reads and failures, rather than prompt wording. They
cover cross-role/run access denial, fabricated evidence IDs, source instruction injection,
symlinks, corruption, task/candidate/revision mismatch, lost commit acknowledgment, restart at a
repair limit, an unresolved reservation and a cancellation inbox while the writer is busy.
Scheduler tests also verify raw persistence before parsing and no relaunch after a raw-output
commit fault. Reviewer inputs omit previous private role transcripts.

Scientific source separation is opt-in for new profiles through the shipped allowlist. Historical
whole-package checks remain intact. `tests/test_agent_scientific_identity.py` checks that host-only
bytes do not change the new scientific identity, modified shared sources fail verification,
shortened closures fail and old profiles do not silently resume under changed package sources.
Checked Part 2 profile bytes and historical results were preserved.

The main checkout's Python 3.12 environment was used with explicit worktree `PYTHONPATH` and `PATH`.
The imported package path was verified as the linked worktree's `src/autoengineering/__init__.py`.
Initial sandboxed broad tests could not inspect process ownership because `ps` was denied. That
run does not qualify campaign process behavior. Later verification uses local process access.
Final command results and current source hashes are recorded below after verification.

## Remaining acceptance requirements

The supplied workflow retains exact campaign envelopes and reconstructs scientific receipts.
The CLI supports both workflow routes and the qualified brokered native adapter through an
explicit host configuration. Offline native boundary, lifecycle and authored-response checks
are recorded below. They do not establish real-provider conformance or model availability.
Generated source handoffs, trusted registration and linked campaign execution have local
Docker evidence. The authored synthetic comparison is verified. Full completion still needs the
native comparison path, the original requirement audit, separately authorized real-provider conformance, and authorized
Leaf River evidence with invalid-candidate and interruption cases. No practical benefit of
multiple roles or independent measured-data confirmation has been established.

The [host boundary plan](../implementation-plans/part-3-host-boundary.md) retains platform and
authentication limits. The [comparison design](../implementation-plans/part-3-matched-comparison.md)
tracks preparation and remaining execution work. Do not substitute the trusted Python runner
for an untrusted-code boundary or reuse old scientific qualification allowances.

## Source snapshot for the first increment (superseded)

| Source | SHA-256 |
| --- | --- |
| `src/autoengineering/agents/__init__.py` | `abc3b488a29988053f28916de3a79176b224a665d3493e7054ca0827aceeede2` |
| `src/autoengineering/agents/hosts/__init__.py` | `485805103879aeec3c87982fa9c64ebfe605eb632394293b7590d4790714532f` |
| `src/autoengineering/agents/hosts/base.py` | `8d673c1e1b3a227601c01b2da49a60317f6745cea2ae11342214f23e40034a13` |
| `src/autoengineering/agents/hosts/fake.py` | `835bd13644534e9592f7f6f019cf7ff9060441e7f64b7391819da711ff6fdf98` |
| `src/autoengineering/agents/permissions.py` | `0d03aa690991c4c5d0e32394ba823c84c7d6d1075418d03d32a31d41061ee1e6` |
| `src/autoengineering/agents/records.py` | `71d1c56dafa6e45f629a7bf046f70896c9668e4a7cefca82d548d53a691d504e` |
| `src/autoengineering/agents/scheduler.py` | `f58c00ccb3e1ac9c536b7665189b2e5a5d75822b3a9ce4f4e564832aa85fc6cb` |
| `src/autoengineering/agents/store.py` | `23176edc5c4f9b00930b3f1935be2318d4cdf7fe870e5634451b8a1605279608` |
| `src/autoengineering/agents/prompts/implementer.txt` | `793708c23cb02f8cbe9baa22cfd4750d97b0b56cae066ad0bf0f5e955bf8ceda` |
| `src/autoengineering/agents/prompts/investigator.txt` | `c9348cd09dc36737081ec6af14514d031042f8b9c31141b9cc0d1366656a7f64` |
| `src/autoengineering/agents/prompts/orchestrator.txt` | `b22b909c03b800283fd197ac17a663c25606b56c39d14d12f85ea719bf4801dd` |
| `src/autoengineering/agents/prompts/reviewer.txt` | `0510634be90b4fd823c804e9a1f14da2a945b8f084ed486ed0e58ddc25cb5654` |
| `src/autoengineering/campaign/identity.py` | `2351d6c38710180c7791df150a24a41fd13f0eab3275934ce9b74308397e41ae` |
| `src/autoengineering/campaign/scientific-closure-v1.json` | `8bdb77661f390c69ea7072f4571db843825553352776e06ab377c78a63b00cd5` |

## Verification results for the first increment

Verified on the local macOS ARM64 checkout on 2026-10-25:

| Check | Result |
| --- | --- |
| `ruff check --no-cache src tests examples` from the main checkout's default environment | Passed. |
| `python -m pytest tests/test_agent*.py -q -p no:cacheprovider` | 74 passed. Includes the existing agentic-architecture tests. |
| `python -m pytest tests -q -p no:cacheprovider` with worktree `PYTHONPATH`, default environment on `PATH`, and local process inspection | 660 passed, 65 skipped in 162.73 seconds. |
| `git diff --check` | Passed. |
| Audit source hash verification | All 14 listed source hashes matched. |
| Worker guide and example README relative links | Resolved. |
| Optional Bayesian environment suite | Not run. No Bayesian behavior was changed. |
| Live host, generated code, new Leaf River qualification, benchmark matrices | Not attempted. |

The full-suite log for this local run is `/private/tmp/part3-pytest-final.log`. Earlier failed
runs are not acceptance evidence: one lacked process inspection, and another exposed stale
historical fixture use in three recovery tests. Those tests now resolve current profiles and
the final full suite passed. No historical manifest was regenerated to obtain that result.

## Broker, evidence and CLI increment

The trusted broker connects the four roles to the unchanged scientific state machine. Scientific
requests have persisted original envelopes and acknowledgments. Staging recovery recognizes exact
committed bytes. Illegal orchestrator assignments consume persistent repair allowances, and
committed scientific errors stop instead of retrying with a new revision.

The broker copies only approved scalar fields into role summaries. It never grants controller
state, labels or child directories. Reviewer contexts contain submitted rationale and exact
approved evidence, without implementer scratch history. Blocking findings pause deterministic
review. A trusted disposition binds the original review digest, unchanged context and a reason.
It preserves findings and cannot override scientific eligibility.

A durable run-start event now anchors elapsed limits before the first invocation. Current host
source, Python runtime, prompt and policy identities are checked before dispatch. Changed host
capability receipts cannot silently continue a run. Worker and scientific cancellation intents
can be queued while both writers are busy. They are not process-stop receipts.

Reports reconstruct tasks, invocations, raw/normalized evidence links, original reviews,
dispositions, allowances, uncertain usage and scientific scalar receipts. The latter retain
selection, configuration, objective, physical attempt accounting and confirmation at an explicit
campaign revision. Reports do not inspect later external scientific changes. Root CLI groups load
lazily, and fresh-process tests deny host/scientific imports for `agents status` and `agents report`.

The wheel installation smoke used a disposable environment with existing base dependencies and
no network installation. It verified the installed package path, all four prompt resources,
matching installed/source host identities and the installed `agents status` command outside the
checkout. Receipt: `/private/tmp/part3-install-70vtn56n/receipt.json`.
No global package, host, plugin or external service was installed.

## Broker and CLI source snapshot (superseded)

| Source | SHA-256 |
| --- | --- |
| `src/autoengineering/agents/__init__.py` | `abc3b488a29988053f28916de3a79176b224a665d3493e7054ca0827aceeede2` |
| `src/autoengineering/agents/broker.py` | `cd6a36919c64b7576a379a6e9d8c2ebbe1f4411c21d4eff5330e2e88cf565652` |
| `src/autoengineering/agents/command.py` | `50df2deb2d06131e24abb02c724d5f7f3f6c6d5d8352448c69916de93c03b291` |
| `src/autoengineering/agents/hosts/__init__.py` | `485805103879aeec3c87982fa9c64ebfe605eb632394293b7590d4790714532f` |
| `src/autoengineering/agents/hosts/base.py` | `8d673c1e1b3a227601c01b2da49a60317f6745cea2ae11342214f23e40034a13` |
| `src/autoengineering/agents/hosts/fake.py` | `1b2311f8b44e708feaf6dabe3def0888a8fcdfad95357148d80a236f636967ba` |
| `src/autoengineering/agents/hosts/scripted.py` | `6255af2bbaf494f1206290e3dba34fb7a1e08474597d4f1834396d3e3566744e` |
| `src/autoengineering/agents/identity.py` | `2b2e3671f8e3722a2c8f8203157c7c328e41a213fc3ec00436856c3c1a8015a5` |
| `src/autoengineering/agents/permissions.py` | `0d03aa690991c4c5d0e32394ba823c84c7d6d1075418d03d32a31d41061ee1e6` |
| `src/autoengineering/agents/records.py` | `7b58dd1432a6dc0fa249cf860765459333e5ee1df34caa6ed79c2d424adf6662` |
| `src/autoengineering/agents/report.py` | `208e95ed6d0c3f843fd3739b5f329ea5a9bbdd047ce34704add0a7cbd92c5f6c` |
| `src/autoengineering/agents/scheduler.py` | `2590bfb8ef3371894f35a13735f532d28b48a3476bc4368d3048d6caf45e41f5` |
| `src/autoengineering/agents/store.py` | `15833ce3a2bec1e82a05904d6185efaa7a42457d6b2f0e3ee8a23b596faeb742` |
| `src/autoengineering/agents/prompts/implementer.txt` | `793708c23cb02f8cbe9baa22cfd4750d97b0b56cae066ad0bf0f5e955bf8ceda` |
| `src/autoengineering/agents/prompts/investigator.txt` | `c9348cd09dc36737081ec6af14514d031042f8b9c31141b9cc0d1366656a7f64` |
| `src/autoengineering/agents/prompts/orchestrator.txt` | `b22b909c03b800283fd197ac17a663c25606b56c39d14d12f85ea719bf4801dd` |
| `src/autoengineering/agents/prompts/reviewer.txt` | `0510634be90b4fd823c804e9a1f14da2a945b8f084ed486ed0e58ddc25cb5654` |
| `src/autoengineering/campaign/identity.py` | `2351d6c38710180c7791df150a24a41fd13f0eab3275934ce9b74308397e41ae` |
| `src/autoengineering/campaign/scientific-closure-v1.json` | `8bdb77661f390c69ea7072f4571db843825553352776e06ab377c78a63b00cd5` |
| `src/autoengineering/cli.py` | `4adb78d97ceb9ca6b954ecdc414a4e2f6f02539ecfd6c809614cbfb77348a2e2` |
| `pyproject.toml` | `f8199a5393eb7084aaa29cee855e47044de3741c4284a6a989b505d9b6c95387` |

Host source identity: `3e1c3975aa92bfe1414a7eacb804de3d7c30b071a6098d6d72a33a56107bb157`.
Host runtime identity: `5e22b468ddc41651064d59f1e322a17d05916c2be0712c86eda1a0fcc60a45f7`.
Platform: `Darwin arm64`, Python `3.12.13`.

## Broker and CLI verification results

| Check | Result |
| --- | --- |
| Full default suite with local process inspection | 679 passed, 65 skipped in 190.75 seconds. |
| Ruff and `git diff --check` | Passed. |
| Disposable installed wheel | Passed. Four prompt resources and installed/source host identities matched. Installed CLI status ran outside the checkout. |
| Offline scripted example | Completed. Four roles, seven fake host invocations, two supplied model calls, selected multiplier 1.5, synthetic RMSE 0.0. |
| Confirmation | `confirmation_not_attempted`. The synthetic result provides no Leaf River or model-utility qualification. |
| Live provider, generated code and frozen benchmark matrices | Not attempted. |

Full test log: `/private/tmp/part3-broker-cli-tests.log`.
Installed wheel SHA-256: `9a653d6e552b59d0449518505c870cdfe4c6469aa95fa9ef920df47cc5fdd6b7`.
Offline example evidence: `/private/tmp/part3-scripted-iujdj193/report.json` and
`/private/tmp/part3-scripted-iujdj193/run/worker/report.md`.
JSON report SHA-256: `ee31f78ab210c5fba46b5662cbd9f51a643cf5f4f809581ee57fb785afd55caf`.

The remaining lifecycle work includes enforcing the elapsed run stop during active scientific
transitions. Current dispatch checks use the durable creation time, while in-flight scientific
work remains bounded by the campaign controller. This does not yet establish a hard elapsed
worker-run ceiling or an owned live-host stop.

## Process, Codex transport and source workspace increment

On 2026-10-26 the process primitive and scheduler were extended with a durable launch gate. A
physical fake executable cannot begin until its running/ownership event is durable. A lost
acknowledgment after that event preserves its authoritative process receipt and blocks a new
invocation. Independent cancellation stops the owned group. Missing stops remain reconciliation
states. Recovery without a live parent handle only signals a group whose root nonce/start identity
can still be verified. Complete automatic worker reconciliation remains pending.

Raw stdout, derived final text and stderr are distinct invocation 1.1 artifacts. Invocation 1.0
serialization omits these new fields and retains original hashes. The saved seven-invocation
scripted report at `/private/tmp/part3-scripted-iujdj193/run/worker` was reconstructed successfully
under the new reader without rewriting evidence.

The Codex transport was tested with trusted fake executables. Tests cover required flags,
authentication-mode mismatch, ambient key exclusion, reported versus requested model identity,
unknown usage, missing executables, partial/empty JSON, tool-use events and nonzero exits. Raw
process bytes are durable before event parsing. No actual provider call or real credential file
was used. Read-only CLI mode and rejection of tool events after return do not establish host
isolation, so this transport is not yet exposed as a production scheduler host.

Candidate workspaces preserve the original source manifest and byte hashes. Snapshots and patches
survive invalid Python, dependency changes and other failed inspections. Symlinks are not followed,
undeclared files are recorded, and source/entry limits bound capture. Static checks do not execute
candidate code and cannot qualify an execution boundary.

### macOS boundary evidence and limits

The first deny-by-default Python profile failed at startup. Trusted probes traced the missing
permission to reading the root directory itself. Adding a literal root read permitted interpreter
startup without granting the home, project or private temporary directories. Later trusted probes
verified denial of evaluator canary reads/writes, workspace writes, symlink escape, site-package
reads, local network connections and fork.

The required memory limit is unavailable on this machine: both `RLIMIT_DATA` and `RLIMIT_AS` calls
with a 256 MiB limit raise `ValueError: current limit exceeds maximum limit`, including in trusted
child probes outside the candidate sandbox. The resource wrapper fails at that call before
`runpy` executes the candidate. Probe artifacts are under
`/private/tmp/part3-sandbox-probes-11fcu3d2`. These are adverse qualification evidence, not a passing
generated-code gate. No claim of a qualified host or generated-code boundary is made.

Docker 29.8.2 is available locally. A bounded, offline, read-only inspection of the already cached
public `rocker/r-ver:4.6.1` image found no Python interpreter. No image was pulled and no package
or host was installed. A trusted Python 3.12 execution image or another effective resource boundary
still needs selection and qualification. Generated mode remains disabled.

### Lifecycle and workspace source snapshot

| Source | SHA-256 |
| --- | --- |
| `src/autoengineering/agents/__init__.py` | `abc3b488a29988053f28916de3a79176b224a665d3493e7054ca0827aceeede2` |
| `src/autoengineering/agents/broker.py` | `cd6a36919c64b7576a379a6e9d8c2ebbe1f4411c21d4eff5330e2e88cf565652` |
| `src/autoengineering/agents/command.py` | `50df2deb2d06131e24abb02c724d5f7f3f6c6d5d8352448c69916de93c03b291` |
| `src/autoengineering/agents/hosts/__init__.py` | `485805103879aeec3c87982fa9c64ebfe605eb632394293b7590d4790714532f` |
| `src/autoengineering/agents/hosts/base.py` | `5633a8c48b79efbdc302ab208dca0acc6f26e64bc8067a54aefff22e1eab3ca0` |
| `src/autoengineering/agents/hosts/codex.py` | `f9a1fe158731c7e9ef2e8e76a9a47f5acf27c5bc597bd9a71e045cb90efec616` |
| `src/autoengineering/agents/hosts/executable_fake.py` | `0564895bf00d2f1d5771e5095abcc3449150957b636158a1aa58246090306aa0` |
| `src/autoengineering/agents/hosts/fake.py` | `1b2311f8b44e708feaf6dabe3def0888a8fcdfad95357148d80a236f636967ba` |
| `src/autoengineering/agents/hosts/scripted.py` | `6255af2bbaf494f1206290e3dba34fb7a1e08474597d4f1834396d3e3566744e` |
| `src/autoengineering/agents/identity.py` | `2b2e3671f8e3722a2c8f8203157c7c328e41a213fc3ec00436856c3c1a8015a5` |
| `src/autoengineering/agents/permissions.py` | `0d03aa690991c4c5d0e32394ba823c84c7d6d1075418d03d32a31d41061ee1e6` |
| `src/autoengineering/agents/process.py` | `13632105ecff02a129805a59dde9ea2b6603b44f030fa233b29fc25d46242f24` |
| `src/autoengineering/agents/process_worker.py` | `3a9fe274a4649ee6ad526012703debd7986ca9139de4c735ccf64666964283e1` |
| `src/autoengineering/agents/records.py` | `1add186cf3dd56f2a4dc901e6affa32f2359e9cc07d412dad0e15b729c9902c5` |
| `src/autoengineering/agents/report.py` | `191f0bca70b22c9fa2f2e9be4f51497097e846f90f5eff0b6b0fb33685ec4bb9` |
| `src/autoengineering/agents/resource_worker.py` | `069d65e08e2f36eb772e88fac1e95fa77c9880caf1b69ea2b8e00856c1cd2b67` |
| `src/autoengineering/agents/sandbox.py` | `36deab2502ee319a8100fa2a0078df46fdc7fbc88771d4111b53833fad116bca` |
| `src/autoengineering/agents/scheduler.py` | `b0e6cc2872b4c80854cddd2edd769162760fafaf08ac9dfb4a6912d6a6c65e94` |
| `src/autoengineering/agents/store.py` | `aaad3928fe10f1377d3e703f9e053720500dd6dbf0fe24074786303c5f292110` |
| `src/autoengineering/agents/workspaces.py` | `c6c6a515d3ab4e207e39bda27d9b02d296831173036767723372781c6fcce545` |
| `src/autoengineering/agents/prompts/implementer.txt` | `793708c23cb02f8cbe9baa22cfd4750d97b0b56cae066ad0bf0f5e955bf8ceda` |
| `src/autoengineering/agents/prompts/investigator.txt` | `c9348cd09dc36737081ec6af14514d031042f8b9c31141b9cc0d1366656a7f64` |
| `src/autoengineering/agents/prompts/orchestrator.txt` | `b22b909c03b800283fd197ac17a663c25606b56c39d14d12f85ea719bf4801dd` |
| `src/autoengineering/agents/prompts/reviewer.txt` | `0510634be90b4fd823c804e9a1f14da2a945b8f084ed486ed0e58ddc25cb5654` |

Host source identity: `7941445999cba9c3ba71c8dc1477602ec96a26a06e82bbbdb2a2ca79f1408c8d`.
Host runtime identity: `5e22b468ddc41651064d59f1e322a17d05916c2be0712c86eda1a0fcc60a45f7`.

### Lifecycle and workspace verification results

| Check | Result |
| --- | --- |
| Final default suite with local process inspection and macOS sandbox creation | 718 passed, 65 skipped in 189.78 seconds. |
| Ruff and `git diff --check` | Passed. |
| Process/executable fixture checks | Durable launch gate, bounded capture, descendant cleanup, timeout, cancellation, failed launch acknowledgment and explicit stop after supervisor death passed. |
| Codex transport checks | Offline fake executables passed. Valid reported usage survives a failed exit, without completing the handoff. Unknown metadata remains unknown. |
| Source workspace checks | Immutable baseline/source/patch capture and initial policy checks passed. No execution or registration authority follows from capture. |
| OS privacy probes | Private read/write, workspace write, symlink escape, site-package access, network and fork were denied. |
| Generated memory boundary | Unavailable. The wrapper failed before candidate code. This is an adverse qualification result. |
| Live host, generated implementation admission and Leaf River pilots | Not attempted. |

Final suite log: `/private/tmp/part3-lifecycle-final-tests.log`. The earlier lifecycle run also
passed 718 tests but preceded the failed-exit usage correction and is not the final source evidence.

Final disposable wheel receipt:
`/private/tmp/part3-lifecycle-final-install-389kj350/receipt.json`.
Wheel SHA-256: `252e1e283091cae7c9a86064ebae2d4be58c988c298b19245d11800a186ca011`.
The installed package matched current host source and prompt hashes, ran its packaged standalone
process worker successfully, verified that process stopped, and reconstructed the earlier seven-call
invocation 1.0 journal. The environment used existing base dependencies and no network installation.

Remaining work still includes a production host boundary, full pending-worker reconciliation,
active scientific elapsed-time enforcement, an effective generated-code memory boundary, trusted
registration under a compatible new scientific identity, and the separately authorized development
pilots. If the scientific runtime adopts the new process helpers, include those dependencies in its
scientific source closure or extract shared helpers with regression coverage. Do not treat them as
host-only merely because their current package path is under `agents`.

## Saved-invocation recovery and local container qualification

This increment supersedes the earlier statement that no generated execution boundary has passed.
It does not enable generated mode or production host dispatch. The macOS memory-limit failure
remains adverse evidence. A separate local Linux container boundary now has passing qualification
on this macOS ARM64 host.

The scheduler can reconcile verified saved raw responses and checksummed physical results without
another host call. Invocation 1.2 records a separate recovery receipt, preserving the original
completion bytes. The broker resumes matching pending tasks through this path. Changed raw output,
stale campaign context and uncertain process ownership remain visible failures. Historical 1.0
journals still reconstruct. Full live-host recovery and active scientific elapsed enforcement
remain unfinished.

The Docker boundary uses an immutable official Python image ID, explicit read-only source export,
no network, no capabilities, an unprivileged user, memory and swap limits, CPU and process limits,
bounded output, and a watchdog in a separate session. The effective container policy is inspected
before start. Ownership labels bind the exact container ID, nonce and intent. The watchdog removes
an expired container that has not started, or kills its owned running container. Probe results and
stop evidence are durable before normal removal. Missing stop evidence requires reconciliation.

The official `python:3.12-slim` image download was explicitly reviewed and approved for these local
probes. It used an isolated Docker client configuration without registry credentials. The download
receipt is `/private/tmp/part3-runtime-download-a8m07l_f/result.json`. The qualification runner
never pulls an image automatically. Two earlier unavailable-runtime preflights remain preserved
under `/private/tmp/part3-container-preflight-cn39y6mf` and
`/private/tmp/part3-container-preflight-bhi5n2oo`.

Qualification output: `/private/tmp/part3-container-qualification-jtyic12r/qualification`.
Receipt SHA-256: `ea49b020b4482eac3094e0b8e2af3db885d8b889c4e6746d20e50178907e7dff`.
Boundary source identity: `3e9b8025286e537498b89f52475689b16e421b6cd39cdcbe6696990133ae9003`.
Pinned image: `sha256:a0f57064cbdcd6285fa45f51237ab0b35ea8ebaed06a1f5973e89e19dfb86704`.

All nine fixed probes passed in 10.30 seconds: Python 3.12 startup as UID 65534, private reads and
writes, network denial, memory exhaustion, CPU exhaustion, output ceiling, wall timeout, process
ceiling and supervisor death. The memory probe was OOM-killed under the 128 MiB limit. The final
probe verified a running container before killing its supervisor, then independently verified that
the watchdog stopped it at the deadline. No provider call, generated candidate or scientific
campaign ran during this qualification. This is evidence for the tested local Docker runtime,
not native Linux host qualification or a production Codex isolation boundary.

`qualification.verify_qualification` reads a trusted caller's pinned receipt without executing
anything. It checks the frozen manifest, current boundary sources and platform, runtime, all nine
probe identities, captured source/input/output bytes, and owned stop receipts. A worker cannot
select the trusted digest or turn this receipt into scientific admission. Its 14 focused tests
cover changed artifacts, symlinks and source changes without requiring Docker.

Current source snapshot: `/private/tmp/part3-container-qualification-jtyic12r/source-snapshot.json`.
Snapshot SHA-256: `34dbbe8a22b5bb8f584bcab09eaf2be28636c8831a27568a625108f3cbf04040`.
Host source identity: `11e6d7c1d3cfd3cef43943e136a5d2b84daf2bb5043573949f8611d04fc15358`.
Host runtime identity remains `5e22b468ddc41651064d59f1e322a17d05916c2be0712c86eda1a0fcc60a45f7`.

The disposable wheel installed into `/private/tmp/part3-container-install-wjdcyi9p/venv`.
Its receipt is `/private/tmp/part3-container-install-wjdcyi9p/receipt.json`, and its SHA-256 is
`1b5f9c61ab597d474ce7711374537434de678e71a757a7c886b3f3c365af4cdb`.
The installed package verified the pinned qualification evidence and reconstructed the earlier
seven-invocation worker journal. This used existing base dependencies with no network installation.

The first broad test run returned 728 passed, 65 skipped and one CLI schema failure. A package module
was added while that run was active. Reopening the affected historical whole-package fixture
returned `identity_mismatch`, as required. The negative-outcome test passed separately. That first
run is not final acceptance evidence. Package sources were then held fixed for the final run.

Final verification against that fixed source snapshot:

| Check | Result |
| --- | --- |
| Default suite with owned process inspection and macOS sandbox creation | 743 passed, 65 skipped in 194.14 seconds. |
| Ruff and `git diff --check` | Passed. |
| Qualification receipt reconstruction | Passed from source and from the installed wheel. |
| Exact-ID container cleanup inspection | All nine containers removed. Receipt: `/private/tmp/part3-container-qualification-jtyic12r/cleanup-check.json`. |
| Optional Bayesian suite | Not run. No Bayesian behavior changed. |
| Production host, generated adapter admission and live Leaf River comparison | Not attempted. |

Final suite log: `/private/tmp/part3-container-final-tests.log`. The earlier failing log remains
at `/private/tmp/part3-container-regression.log`. The main checkout is clean. No commit or push
was performed.

Remaining work includes a qualified production host, full live-host reconciliation, a generated
interface driver, trusted registration and compatible scientific source closure, active scientific
elapsed enforcement, releasing the worker writer around external host/scientific actions, and
separately authorized matched Leaf River pilots. The current lock scope still spans those actions,
although cancellation has an independent inbox. This does not satisfy the plan's lock-scope rule.
Part 3 remains active.

## Operation leases and journal lock scope

The earlier lock-scope gap is corrected in this increment. Host invocation, scientific request
handling and trusted staging now run without the worker journal writer. A separate advisory
operation lease excludes another dispatcher or reconciler across preparation, external action and
result commits. The lease is acquired before the writer. Launch callbacks briefly reacquire the
writer to durably acknowledge process ownership before the existing launch gate opens.

Both leases use owner-private regular files with `O_NOFOLLOW` and nonblocking `flock`. They are
distinct OS locks. A second store can acquire the journal writer while a host or scientific action
holds the operation lease. The lease is released by descriptor closure or process death. Its file
can remain after exit and does not establish live ownership. Reports require neither lock.

Two new tests first reproduced the old behavior: acquiring the journal writer during a host call
or scientific request failed. Both pass after the change. The fake-host test also attempts dispatch
and recovery from a second scheduler during the call. The scientific test attempts a second broker's
reconciliation during requests and staging. These attempts fail on the operation lease, with no
duplicate starts. A separate process test confirms that killing the lease owner releases the lease
while leaving its file present. Symlinked lease files are rejected without changing their target.
The live trusted-executable cancellation test also verifies that the writer is available and a
competing `stop_owned` recovery cannot stop the active dispatcher's process.

Focused verification: 39 passed in 46.91 seconds, with local owned-process access. Log:
`/private/tmp/part3-lock-focused.log`. The final suite includes the additional live-process writer
and recovery assertions added after that focused run. Package sources are fixed during the final
suite so historical whole-package fixture identities remain stable.

No scientific controller, source-closure manifest, frozen benchmark record, or qualification source
changed for this increment. The existing container qualification remains source compatible. No
provider call, generated candidate admission or Leaf River pilot was performed. The remaining
requirements still include production host isolation, full live-host recovery, active scientific
elapsed enforcement, generated interface execution and trusted registration, and matched live
development pilots. Part 3 remains incomplete.

Final verification for the operation-lease increment:

| Check | Result |
| --- | --- |
| Default suite with local process inspection | 747 passed, 65 skipped in 206.58 seconds. |
| Ruff and `git diff --check` | Passed. |
| Installed-wheel operation lease and independent writer | Passed. |
| Installed-wheel historical journal reconstruction | Seven invocations reconstructed. |
| Existing container qualification reconstruction | Passed with its unchanged boundary source identity. |
| Optional Bayesian suite | Not run. No Bayesian behavior changed. |

Full suite log: `/private/tmp/part3-operation-final-tests.log`.
Disposable installation receipt: `/private/tmp/part3-operation-install-rfjhci5k/receipt.json`.
Wheel SHA-256: `f03d184ec4cd01d1b74529905397625b49a84d0034c169bbedeb1811eafd94bc`.
Current host source identity: `ec0a9a703266d2c2f201b10ae8b494545b7b85e7f712fbd08e0ac6e24e6cc6d0`.

| Changed package source | SHA-256 |
| --- | --- |
| `agents/store.py` | `b2180d00575db630cc14582af641a63cf75f9cdd41129264a3421d725c7ce8e5` |
| `agents/scheduler.py` | `ef4480d43334a20c07333155067df99d1371413dce2cfba2bfdbf5b86fdafc7d` |
| `agents/broker.py` | `e03757020a02284cab76e3e66c2c98ad314a071f17a68b3fa4329bd39ccfed0e` |

No commit or push was performed. The main checkout remains clean. The next elapsed-time work must
stop an active scientific request at the worker-run deadline and preserve the original request
envelope for recovery. Generated admission still needs an isolated interface driver and a trusted
registration step. If scientific execution imports boundary helpers currently under `agents`,
include those exact dependencies in a new compatible scientific closure. Role prompts and host
adapters must remain outside it. Do not expand or rewrite a resumed campaign.

## Worker deadline during scientific work

The broker now checks the original creation-time deadline before new tasks, dispatch, staging and
scientific requests. During a request, a foreground timer forwards cancellation to the independent
worker and scientific inboxes. It is joined before the broker commits the response or starts another
action. A completed request disarms its timer, so it cannot queue cancellation later.

Each expiry records a strict immutable notice with run identity, original deadline, action ID,
forwarded intent IDs and bounded failure codes. Both forwards are attempted if one fails. A failed
forward remains `reconciliation_required`. A successful retry can explicitly reconcile that failed
notice without rewriting it. Read-only JSON and Markdown reports include the notices and relative
receipt links. CLI forwarding failures exit 4 with reconciliation evidence rather than a schema
error. Notices record forwarding, not proof that a process stopped.

Committed scientific responses are obtained through exact-envelope replay before expiry forwarding.
Uncommitted requests get cancellation before the service can start numerical work. This exposed a
controller issue: a direct evaluation with cancellation already queued did not finish cleanly before
reservation. Evaluation and confirmation now check cancellation before execution. If an earlier
attempt remains unresolved, these handlers preserve `reconciliation_required`, its unknown cost
and the frozen choice. A queued stop cannot change uncertain work into a completed campaign.

This increment changes scientific controller source, unlike the previous host-only increment. New
campaigns bind the new controller hash through their declared scientific closure. No old campaign,
manifest, ledger or benchmark was rewritten. Historical profiles retain their original resume
checks and cannot resume against the changed controller. Read-only evidence remains available.

| Scientific controller source | SHA-256 |
| --- | --- |
| Before this increment | `93a856a59e219aa33d7cd45b754f622a526e4e1bef1add038f3008c3c9d53989` |
| After this increment | `9aeadd2aabeb5dd00e28419489b2ee1b942b42f2c10e195b5c4490253c7ee61b` |

The test evidence includes an already expired run with no baseline, host call or campaign action;
a real owned scientific-supervisor process stopped by the worker deadline; exact-envelope recovery
after expiry; an expired uncommitted request with no execution or reservation; failed forwarding
and explicit resolution; disarmed timer behavior; corrupt notice rejection; read-only CLI reports;
cancelled confirmation with no third execution; and preservation of unresolved evaluation and
confirmation attempts. The slow process is a bounded trusted test fixture, not a Leaf River result.

The timer is part of the foreground broker. Supervisor death still requires existing scientific
ownership checks and recovery. This does not qualify an independent scientific watchdog or the
production host. Active deadline cancellation has been exercised for fixed evaluation. A separate
calibration cancellation exercise remains to be added before claiming equal coverage of that path.

Source snapshot: `/private/tmp/part3-deadline-evidence-k3w0k4qx/source-snapshot.json`.
Snapshot SHA-256: `55020c7b1487b9a83a47032f0115e4ed64667c5e5e6cae49bf769d1d044e7c1f`.
Host source identity: `29089fea45323d71a9f3c5a6029db29d723b88360e5f18b71de26ba27ad66d63`.
The existing container boundary identity remains
`3e9b8025286e537498b89f52475689b16e421b6cd39cdcbe6696990133ae9003`, and its pinned qualification
still reconstructs without running another probe.

Earlier verification: 18 deadline/recovery tests passed in 32.60 seconds, followed by 14 focused
deadline and confirmation checks in 9.00 seconds. The broad run with 763 passed and 65 skipped
preceded the unresolved-attempt correction. It is preserved at
`/private/tmp/part3-deadline-pre-audit-tests.log`, and is superseded for final source claims.
The two new unresolved-attempt tests passed after that correction in 4.35 seconds.

Part 3 remains incomplete. Required work still includes production host isolation and conformance,
full live-host recovery, generated interface execution and trusted registration, and separately
authorized matched Leaf River pilots. No live provider call or generated candidate admission ran in
this increment. No benchmark matrix, commit or push was performed.

Final verification after the unresolved-attempt correction:

| Check | Result |
| --- | --- |
| Default suite with local process inspection and macOS sandbox creation | 765 passed, 65 skipped in 225.60 seconds. |
| Ruff and `git diff --check` | Passed. |
| Saved source snapshot | All listed source and test hashes match. |
| Installed deadline forwarding fixture and notice reconstruction | Passed. No scientific campaign or provider call. |
| Installed corrected scientific controller | Exact source hash matches the worktree. |
| Historical worker report | Seven invocations still reconstruct. |
| Existing container qualification | Verified from source and installed package without new execution. |
| Optional Bayesian suite | Not run. No Bayesian behavior changed. |

Final suite log: `/private/tmp/part3-deadline-final-tests.log`.
The final disposable installation receipt is
`/private/tmp/part3-deadline-install-wm4557fj/receipt-after-uncertainty-fix.json`.
Final wheel SHA-256: `a44b598c93b54bba46da85a4ac8ad30f3b42b1271ba22637d5ecdfbf54fa54b0`.
The earlier installation receipt in that directory predates the unresolved-attempt correction
and is superseded for controller source claims. Its other smoke outcomes remain historical evidence.

The main checkout is clean. The next numerical cancellation check should exercise a fitting child
study under worker-run expiry, preserving both its campaign attempt and optimization ledger.
Then continue the generated adapter interface driver and trusted registration work. These checks
and the remaining production host and live-pilot requirements still gate full completion.

## Isolated interface driver and calibration cancellation

The fitting-child cancellation check now passes. It injects expiry after a real fitting process
launch, verifies that the owned group stops, and reads the failed observation from the child ledger.
Baseline, supplied-default and fitting starts remain distinct. Resume starts no further work.
This exposed a worker receipt bug: scientific child action IDs use `study-id:action-id`. The receipt
now accepts this composite form and preserves legacy single identifiers. Malformed references remain
rejected. Scientific controller source did not change in this increment.

`agents.interface` adds strict scalar/daily float contracts, immutable public fixtures, a fixed
container driver and read-only receipt reconstruction. Expected values stay outside the container.
Each case gets a fresh process and read-only source export under the qualified resource policy.
The host never imports the candidate. Source policy is rechecked independently of claimed checks.
Parser recursion produces a captured source failure, retaining source and patch artifacts.

The receipt binds source/capture, fixture specification, qualification and runner identities.
Verification checks physical intents, source and driver bytes, input/output hashes, effective
container policy and fixture outcomes. Failed and skipped cases remain explicit. Unit tests include
changed units, changed source/output/policy bytes, and a resealed receipt with elevated privileges.
These checks establish interface behavior only. They do not grant scientific eligibility or adapter
registration. Limits remain four cases, four input/output ports and 128 values in each mapping.

The container runtime now records client bytes and a server fingerprint covering version, kernel,
architecture and security metadata. Qualified execution rechecks these before starting. Each
physical receipt binds its saved effective policy. These source changes invalidate the earlier
boundary qualification for new execution. The old receipts remain intact.

Fresh qualification: `/private/tmp/part3-interface-boundary-mz2h782u/qualification`.
All nine fixed probes passed in 10.30 seconds, without downloading another image.
Qualification receipt SHA-256: `42e918316fd97d113c4216af6a6c01f7b38dc9ac048a9e5cc9dedb2a25d0b5ed`.
Boundary source identity: `c4bba04d7b191a31ae4ba4a4d0396c790abba0216d43c4acfcc463f021fa5e86`.
The executed qualifier source is archived at
`/private/tmp/part3-interface-boundary-mz2h782u/qualifier-executed.py`.

Final authored fixture evidence: `/private/tmp/part3-interface-vector-ntiwf6w8/fixtures`.
Scalar and daily-vector cases passed. Input mutation, an infinite loop and a wrong fixture value
failed as expected. Seven starts completed in 4.88 seconds under a frozen worst-case allowance of
ten starts and a 60-second success criterion. Reserving both cases for each fixture also bounds
unexpected passes. No criterion was relaxed to accept a failure. The executed fixture source is
archived at `/private/tmp/part3-interface-vector-ntiwf6w8/fixture-executed.py`.

Earlier authored fixture runs remain preserved at `/private/tmp/part3-interface-fixtures-cqsvp1mh`
and `/private/tmp/part3-interface-final-574s2od7`. The first predates parser/receipt hardening. The
second tested the final runner over scalar and adverse cases before vector coverage was added.
Their five-start plans are historical evidence, not the current worst-case fixture budget. The
wrapper scripts now include total elapsed time in their success decisions. The qualification
verifier independently enforces its 90-second criterion for the recorded qualification.

Final source snapshot: `/private/tmp/part3-interface-evidence-du9mdepy/source-snapshot-final.json`.
Snapshot SHA-256: `52a582102944732c9a14923a6221dbbf1f07a23783b372502e7a4d0b1fe47230`.
Host source identity: `b02879a8c9f3bfdb694837f2dd41b8dfc5df3b4dd684e5ea9b191a2358f72c45`.
Interface runner identity: `c0c4e11d070a4bd089081232dfc5f0fe742794bfa6591b545aeb9728bf1e23d4`.

| Verification | Result |
| --- | --- |
| Default suite | 793 passed, 65 skipped in 211.78 seconds. |
| Ruff and `git diff --check` | Passed. |
| Fresh boundary qualification | Nine probes passed. |
| Final authored scalar/vector/adverse fixtures | Five receipts verified, seven physical starts. |
| Installed wheel | All five receipts reconstructed without execution; historical seven-invocation worker journal reconstructed. |
| Exact-ID cleanup | Sixteen containers from qualification and final fixtures verified removed. |
| Optional Bayesian suite | Not run. No Bayesian implementation changed. |
| Live provider, generated worker candidate, scientific registration or Leaf River pilot | Not attempted. |

Full-suite log: `/private/tmp/part3-interface-final-tests.log`.
Installed receipt: `/private/tmp/part3-interface-install-edg7dl8y/receipt-vector.json`.
Wheel SHA-256: `64d7cd13b591eae5133c04cddfa1ae71fda17c3e3b5c9068c5839b5d48349227`.
Cleanup receipt: `/private/tmp/part3-interface-evidence-du9mdepy/cleanup-vector-check.json`.
The main checkout remains clean. No commit, push or benchmark matrix was performed.

The next increment is trusted registration and its broker handoff. It must consume the exact
captured source and verified receipt, preserve author review, and create a compatible new campaign
when required. Scientific runtime imports must enter an explicit scientific source closure.
Do not add host adapters or prompts to that closure merely because boundary helpers live under
`agents`. Production host isolation/conformance, full live-host recovery and authorized matched
Leaf River pilots remain required. Part 3 is incomplete and remains active.

## Reviewed standalone registration and portable evidence

`agents.admission.register_candidate` now verifies an exact source capture, passing interface
receipt, qualification pin and separately pinned caller review before publishing a registration.
There is no worker operation for this function. The public worker policy still rejects self-admitted
implementation bundles. A rejected or stale review, failed check or unknown packet file cannot
produce a registration directory.

The bundle contains candidate source, the fixed driver, registration metadata and a deterministic
stored ZIP of verified evidence. Only explicit workspace, interface and qualification files enter
the archive. Limits are 4 MiB, 512 members and 64 KiB per member. Extraction checks the member table
before writes, rejects traversal, symlinks, compression, collisions and excessive entries, and
creates every directory with private permissions. An initial test caught permissive intermediate
directory modes from recursive `mkdir`; those modes were corrected and the focused tests passed.

Interface manifest 1.1 records the original execution origin. Explicit relocation verification
reconstructs archived source, inputs, outputs and effective policy while preserving that origin.
The bundle can therefore be copied without rewriting physical evidence. The live fixture moves
its original workspace and checking directories aside, retaining their bytes, before testing the
registered bundle and its copy.

Registration 1.1 also binds an explicit execution source identity. This extends the versioned
scientific engine closure with isolated execution helpers and their package initializer. Provider
adapters and role prompts remain excluded. A runtime source change rejects use of the old entry.
Legacy 1.0 registration metadata still round-trips with its original identity, but cannot authorize
an unbound execution. Both current and legacy cases were checked in the installed wheel.

`adapters.isolated.registration_entry` creates an application-owned `AdapterRegistration` for a
standalone `AdapterRegistry`. The adapter accepts one fixed component with exact scalar/daily float
contracts and no tunable parameters or training. It verifies evidence before execution and exports
only captured source, the fixed driver and forcing. It never imports candidate code on the host.
Each handle permits one execution. Cleanup retains physical receipts and does not independently
certify that a container stopped.

Final authored fixture: `/private/tmp/part3-registration-final-wmt0xl_v/fixture`.
Two interface checks and two standalone registered lifecycles completed in 3.36 seconds, within
the four-start and 60-second allowances. Both registry entries returned 8.0 for the separate forcing
value 4.0, with stopped-container receipts. The approval record is explicitly a test fixture, not
human author approval. There was no campaign selection, provider call or live generated worker.

Registration identity: `f09f96c198537f68fcb17ab2246b871a23dad02363c94b29c55275d5e7f6f8a2`.
Execution source identity: `5b9d8b20ee1a798726afc645fa2ea63b52533efa9b2714d9e34e0d5fe8504114`.
The earlier prototype under `/private/tmp/part3-registration-fixture-ubajtugc` remains intact as
legacy 1.0 evidence. It predates the explicit execution source binding and is not runnable under
the current policy.

| Verification | Result |
| --- | --- |
| Default suite | 820 passed, 65 skipped in 216.04 seconds. |
| Ruff and `git diff --check` | Passed. |
| Real authored registration fixture | Four starts, original and copied entries passed. |
| Installed wheel | Portable evidence and source binding verified without new execution; legacy registration and seven-invocation worker report reconstructed. |
| Cleanup inspection | Four exact final fixture container IDs verified removed. |
| Optional Bayesian suite | Not run. No Bayesian implementation changed. |
| Campaign backend activation, human author approval, live provider or Leaf River pilot | Not attempted. |

Full-suite log: `/private/tmp/part3-registration-final-tests.log`.
Source snapshot: `/private/tmp/part3-registration-evidence-kglgtnoe/source-snapshot.json`.
Snapshot SHA-256: `07f2a67c0743df885b745303d5d2e1b66311990940d8c0c5516575aa0610d89c`.
Installed receipt: `/private/tmp/part3-registration-install-caz21twh/receipt.json`.
Wheel SHA-256: `5629968d44a44bf30069652136c29a3940881d14c667a6470fc53173d4a9eb44`.
Cleanup receipt: `/private/tmp/part3-registration-evidence-kglgtnoe/cleanup-check.json`.
No scientific controller, frozen manifest, benchmark matrix, commit or push changed in this increment.
The main checkout remains clean.

Campaign activation is deliberately still rejected by the default registry and tested as such.
The next step must connect this runtime to container-aware campaign attempt receipts and recovery.
Stopping an outer native process group cannot prove that its inner container stopped. Activation
also needs a compatible campaign source closure and broker handoff, with a new campaign when the
frozen implementation catalogue lacks the registration. Do not expand a resumed campaign or claim
the standalone fixture satisfies the full scientific admission gate. Production host qualification,
full live-host recovery and authorized matched Leaf River pilots remain required. Part 3 is active.

## Container recovery helper

Added `agents.container_recovery.reconcile_container` and 27 focused tests. The helper accepts
trusted source/input bytes and a pinned qualification, reconstructs intent and effective policy,
refreshes the Docker runtime identity, and inspects the exact immutable container ID. It checks
saved output hashes without rerunning code. An outer worker exit is not proof of container stop.
Missing launch artifacts, conflicting receipts, ownership changes and daemon errors remain
unresolved. Absence proves physical stop only, without recovering missing output or settling cost.

Optional stop requires the caller to stop the outer owner first. The helper checks ownership again
immediately before signalling, removes an unstarted container to prevent a late start, and checks
the resulting state. Failed stop commands cannot certify stop. Original execution artifacts remain
unchanged. The scientific controller does not use this helper yet. Its default registry still
rejects generated IDs, and this increment does not activate generated campaigns.

The authored two-start fixture passed in 2.09 seconds at
`/private/tmp/part3-container-recovery-20261026/fixture-v2`. It recovered a saved successful result,
observed a running container after killing its outer owner, then verified its stop and removal.
The interrupted attempt retained no numerical result. No provider, registration or scientific
campaign ran. Both exact fixture container IDs were verified absent.

The earlier fixture at `/private/tmp/part3-container-recovery-20261026/fixture` stopped after its
first completed probe because this Docker CLI reports absence with lowercase `error: no such
object`. That failed attempt is preserved. The helper now accepts that complete diagnostic for the
exact ID, with regression coverage. A preliminary invocation rejected a nonprivate output parent
before creating output or starting a container. These attempts used three container starts total.
No image was downloaded and the existing physical boundary qualification remains unchanged.

Focused checks: 27 passed. Default suite: 847 passed, 65 skipped in 209.49 seconds.
Full-suite log: `/private/tmp/part3-container-recovery-tests.log`.
Ruff and `git diff --check` passed. Optional Bayesian tests and a wheel rebuild were not run.
Source snapshot: `/private/tmp/part3-container-recovery-evidence-4hh5qbin/source-snapshot.json`.
Snapshot SHA-256: `40122a0292e43c9860296c0728db1efbe2d9d7ef2ade26f8c0f8a064b34f710b`.
The snapshot covers the helper, tests, authored fixture and current guides. It does not include
this later progress entry. No commit or push was made. The main checkout remains clean.

Next connect source-bound launch receipts and this helper to campaign execution, cancellation,
finished-result recovery and manual reconciliation. A new scientific closure and compatible frozen
implementation catalogue must precede activation. Broker generated handoffs, production host
qualification, live-host recovery and authorized matched Leaf River pilots remain pending.

## Frozen generated backend and campaign ownership

The deterministic controller now supports one predeclared reviewed registration in a new scientific
profile. Default registry calls still reject generated IDs. Opt-in registry construction requires
the exact `generated-<digest>` ID, registration bytes and complete version 2 execution closure.
Worker text cannot supply a factory, extend the catalogue or change a resumed campaign. Initial
registrations remain fixed, parameterless single components with the reviewed ports and source
refs. Calibration and training are rejected. `linear-fixed` is an explicit parameterless authored
baseline. Existing adapters and their numerical defaults remain unchanged.

`scientific-closure-v2.json` adds only the explicit isolated execution helpers to version 1's
source list. Both manifest digests are bound. Provider adapters, role prompts and worker records
remain excluded. Version 1 remains the default and its manifest bytes were preserved. Standalone
registration identities now include this execution closure and container recovery. Earlier
registration evidence remains readable but cannot authorize new execution under changed sources.

The controller allocates a unique scratch directory for each generated attempt. A trusted callback
commits the outer attempt ID/nonce, registration digest, relative execution path and inner
container ID/nonce/intent before Docker can start. Callback failure removes the unstarted owned
container through the existing launch gate. The worker supplies only forcing to the fixed driver.
The host never imports candidate source.

Normal completion verifies the native owner is gone, checks inner stop and compares native arrays
against the raw container result before scoring. Finished-result recovery checks the same binding
and reuses the result without a replacement launch. Cancellation and manual reconciliation verify
the inner stop separately. Missing jobs, contradictory bindings and incomplete physical launch
evidence remain unresolved. Provable absence of a launch is recorded separately.
An inner stop alone does not manufacture a numerical result or turn uncertain cost into zero.
Inner receipt artifacts accompany native supervisor evidence. Tests cover live native ownership,
changed bindings/catalogues, differing native arrays, missing jobs, unknown inner stop and
unchanged supplied-adapter recovery behavior.

The final authored fixture is
`/private/tmp/part3-generated-campaign-20261026/verified-recovery-fixture`.
It used five container starts and two scientific fixture evaluations in 7.83 seconds. It prepared
and copied a reviewed authored registration, froze a private source profile, ran a native baseline
and isolated candidate, and terminated the controller before committing the saved candidate
result. Resume verified and reused the result, accepted the candidate against a separate public
scalar fixture and completed with the same two physical attempts. Completed resume added none.
Confirmation remained `confirmation_not_attempted`. There was no provider call, live worker,
human author approval, Leaf River run or scientific utility claim.

Final registration identity:
`1802c57896db03820a9eeb6165166035c36e8fc1e7f7727a0fd1ac4d15a6a735`.
Execution identity:
`0acbde775883f063fd3aafe2f561b6b7a876dfec220b46b6768c28eeeb98f2cb`.
Three earlier five-start fixtures remain under the same parent as development evidence. One
completed the ordinary path and two checked saved-result recovery before the final admission and
missing-job checks. All 20 exact owned container IDs were verified absent in
`/private/tmp/part3-generated-campaign-20261026/cleanup-check.json`.

Focused checks: 56 passed. Final default suite: 872 passed, 65 skipped in 199.07 seconds.
Log: `/private/tmp/part3-generated-campaign-verified-tests.log`.
Ruff and `git diff --check` passed. Optional Bayesian tests and Linux qualification were not run.
An intermediate focused run found a supplied recovery fixture without a job artifact. The stop
gate was corrected to preserve that supplied path while requiring the job for generated profiles.
A broad run that overlapped the final source edit reported one stale-artifact recovery failure
(870 passed, one failed, 65 skipped). It is not final verification. The stable-source rerun is
the final verification result above.

The disposable wheel includes version 2 and verified the final registration identity and portable
evidence without new execution. Receipt:
`/private/tmp/part3-generated-install-s1fy7c8z/receipt.json`.
Wheel SHA-256: `a86cded09c22379d6b1643c377bdd11abab1ba4f294a67c537a12f87111624b4`.
Installed verification used Python's safe-path option after an unrelated temporary-directory
module shadowed a standard library import on the first attempt. The unrelated file was preserved.

Source snapshot: `/private/tmp/part3-generated-evidence-siubabk_/source-snapshot.json`.
Snapshot SHA-256: `6a4d41236258c19cf2000aca161cffc987b9bf2c20ad5c744d74b35b16b6b88f`.
The snapshot binds current engine/helper files, both manifests, the integration fixture, tests and
package configuration to the final fixture's verified scientific and execution identities.

The next work is the generated workspace handoff through the trusted broker, followed by
production host qualification and the explicitly authorized live conformance and matched Leaf
River pilots. This backend fixture does not complete Part 3. No commit or push was made.

## Source-response preparation and linked campaign

Added version 1.1 `SourceDraft` handoffs for explicit fake-host generated runs. Old version 1.0
handoffs remain readable. Task schema/version, candidate/base identity, file allowlist, fixed
dependencies, byte limits and granted evidence are checked before accepting a response. Worker
text cannot choose a test command, claim executed checks or self-admit source. Production hosts
remain rejected. Ordinary generated broker advance stops at the originating proposal rather than
admitting an implementation under a changed catalogue.

`SourcePreparation` writes the returned `adapter.py` to a scoped workspace and captures source and
patch before policy checks. Source failure remains visible without candidate execution. Capture,
check reservation, check outcome, separate trusted admission and successor creation are worker
journal events. The operation lease excludes competing checks while the writer remains available
to cancellation. Public fixtures and qualification remain trusted caller inputs. A pending check
blocks another host dispatch. Cancellation reaches the container executor. Recovery reuses saved
checks or stops/retires partial checks without repeating a potentially launched case. Interface
reservations remain separate from host invocations and scientific budgets.

After a separately pinned `AdmissionReview`, the fork API requires a new name and explicit new
`ExecutionSpec`. It preserves baseline, data, acceptance and confirmation semantics, copies only
declared artifacts and creates the new campaign without executing it. A complete campaign directory
is published atomically. `generated/origin.json` binds the originating campaign/proposal, worker
handoff, capture, interface checks, review and registration into the new scientific provenance.
Lost admission or fork acknowledgments reuse exact saved artifacts. The parent scientific journal
and allowance remain unchanged. The successor reviewer receives the captured source and public
interface/check receipt without mutable workspace access, private paths or implementer history.

One stop-recovery defect surfaced during review: a saved `reconciliation_required` container result
could previously prevent an owned stop. Recovery now validates its context and raw hashes, inspects
and stops only the exact owned container, and retains the uncertain result unchanged. It returns
no numerical outcome for that record. A regression test verifies stop and missing-result semantics.
The existing physical boundary qualification remains unchanged.

Final fixture: `/private/tmp/part3-source-handoff-20261026/verified-fixture`.
Eleven fake-host invocations, three container starts and three scientific fixture evaluations
completed in 10.44 seconds. Four parent calls prepared source. Seven successor calls included a
separate reviewer with exact source/check context. The parent remained `candidate_pending` with
one physical attempt. The successor used its explicit two-attempt budget, accepted the candidate
against public authored scalar values and reported `confirmation_not_attempted`. Replaying the
completed successor and fork added no execution. There was no provider call, human author approval,
live worker generation, Leaf River run or independent scientific confirmation.

Two earlier development fixtures remain under the same parent. The first passed before exact
review context was added. The second completed scientific work but its postcondition searched
encoded prompt text without decoding the nested granted JSON. That assertion was corrected.
All nine exact owned container IDs across the three fixtures were verified absent in
`/private/tmp/part3-source-handoff-20261026/cleanup-check.json`.

| Verification | Result |
| --- | --- |
| Focused preparation, journal, permission, scheduler and container recovery checks | 77 passed in 39.88 seconds. |
| Full default suite | 892 passed, 65 skipped in 240.89 seconds. |
| Ruff and `git diff --check` | Passed. |
| Installed wheel | Parent/successor reports and portable registration verified without new execution; no host/controller imports for reporting. |
| Legacy compatibility | Historical seven-invocation report and legacy registration metadata reconstructed with the installed wheel. |
| Optional Bayesian tests and Linux qualification | Not run. |
| Production host, live generation, matched Leaf River pilots | Not attempted. |

Full-suite log: `/private/tmp/part3-source-handoff-tests.log`.
Installed receipt: `/private/tmp/part3-handoff-install-jjv8g2_e/receipt.json`.
Wheel SHA-256: `54296477d20a1ed8c24772ab682f7000ab3c8d9518b5291b183e4d79a57f5328`.
Source snapshot: `/private/tmp/part3-handoff-evidence-rsvpk3z0/source-snapshot.json`.
Snapshot SHA-256: `d68a7bf3d0f26c0e198bc279161167f694b9d1d300fa00b154684dde0ac3c31b`.
Host source identity: `8c65015c996e83a827c2f5560c24cdfaa446dc392e4b6680d61d8069dc67289d`.
Execution identity: `9e0736b4999cff7f82257626744571c2d8906be699957984be6b5c88b5f84956`.
Registration identity: `cc2a2def6b94eb3912852fee7fbcf98a62ea44f8ca05b479e68cd29212b765d8`.
The main checkout remains clean. No commit or push was made.

Part 3 remains active. Generated preparation recovery currently requires the pinned Python API;
CLI `resume` reports the pending state but does not yet invoke that recovery. Complete this CLI
integration, then qualify the production host boundary and prepare the explicit live conformance
and matched pilot gates. The fake-host fixture does not satisfy those remaining requirements.


## CLI preparation recovery and adverse host probe, October 26, 2026

The preceding SDK-only recovery limitation is resolved. `agents resume --qualification-root PATH`
now recovers a pending source preparation against its saved qualification digest. Missing or
incompatible qualification and unresolved process ownership stop recovery with exit 4. Recovery
opens the parent controller for inspection and does not advance scientific evaluation. A captured
preparation may start only its original unlaunched checks within the saved allowance. Interrupted
checks are reconciled without repeating a potentially launched case. Completed checks replay without
new work or a qualification root. Status exposes pending preparations. Forking also verifies the
originating scientific runtime sources before creating a successor.

The authored Docker fixture at
`/private/tmp/part3-source-cli-recovery-20261026/verified-fixture` completed in 4.16 seconds.
It recovered an interrupted check acknowledgment through the CLI, retained four fake-host
invocations and one parent scientific attempt, and reached `awaiting_trusted_admission`.
Recovery and replay added no provider calls or scientific attempts. All four exact container IDs
across the two fixture runs were absent at cleanup. No registration or successor was created.

| Verification | Result |
| --- | --- |
| Focused preparation and CLI tests | 33 passed in 72.21 seconds. |
| Command probe classification tests | 2 passed. |
| Full default suite | 904 passed, 65 skipped in 257.12 seconds. |
| Ruff and `git diff --check` | Passed. |
| Installed wheel | Recovery option and completed replay verified; journal unchanged, no new execution. |
| Production host qualification | Failed at the command-profile positive control; remains unqualified. |
| Live provider conformance, matched Leaf River pilots and Linux qualification | Not attempted. |

Full-suite log: `/private/tmp/part3-source-cli-and-probe-final-tests.log`.
Installed receipt: `/private/tmp/part3-source-cli-final-install-n3yka8hu/receipt.json`.
Wheel SHA-256: `4fdd74c6fbdb32bae7cc00bc24228f548416f9b169b7ec2650d420c8a6723be1`.
Source snapshot: `/private/tmp/part3-source-cli-evidence-x0twydb1/source-snapshot.json`.
Host source identity: `613eabb826cfb88d07b3c50a04a2a7ab0634d7899112c925783956f81bfd95d6`.

The new host-boundary plan distinguishes command filesystem permissions from model-client,
credential and other tool access. The offline inventory identified Codex CLI 0.164.0. The synthetic
command probe used no real credentials and denied network access around the entire CLI tree.
Its final record is `/private/tmp/part3-command-profile-20261026/final-probe`. The approved brief
read exited 71 with `sandbox-exec: sandbox_apply: Operation not permitted`. The remaining five
cases are explicitly `not_attempted`. All launched processes stopped. Both host and network
qualification remain false.

Direct network-denied echo controls succeeded. The combined Codex/native-profile invocation
failed with the same error both with and without a new process session outside the supervisor.
See `controls.json` and `composition-controls.json` in the same parent directory. This isolates
the observed failure from the process supervisor but does not establish a general macOS limit or
a definitive cause. The earlier development probe's negative-case pass flags counted startup
errors and are invalid denial evidence. The final classifier rejects that interpretation and
checks the positive control before attempting denial cases.

Part 3 remains active. The production host boundary, live provider conformance and matched pilot
gates remain unfinished. The failed profile composition must be resolved without relaxing the
boundary or inferring real credential or provider authority. No commit or push was made.


## External host boundary investigation, October 26, 2026

A single external macOS boundary now has passing offline filesystem and socket evidence.
The new `probe_external_boundary` example avoids nested sandbox initialization. It retains
root read denial except exact runtime paths, staged workspace reads and scoped scratch writes.
It grants no ambient home, private checkout, evaluator or Mach service access. Fifteen final
checks passed in 1.00 seconds, including positive and negative child reads, private canaries,
symlink traversal, write separation, and TCP/Unix socket controls. The network controls differ
only in network authority from the denial policy and reach fixed owned local listeners. Each
listener received exactly one control request. All owned processes and both listeners stopped.

Final artifact: `/private/tmp/part3-external-20261026/verified`.
Receipt SHA-256: `5c351a3ee6405a603505aa5e1c811ef2498c225302c8a7bed92e57bc793928f5`.
The fixture retains `host_qualified=false` and does not establish networked host conformance.

The new `probe_external_codex` example provides one authored Responses endpoint without auth.
The complete CLI process tree can reach only its selected localhost port. The final default
fixture, `client-verified` under the same parent, failed before any request while synchronizing
macOS managed preferences. It retains that adverse result. The exact absent system-requirements
path and `/etc` symlink requirements were established independently with fixed-command probes.
No broad directory permission was added to hide those startup errors.

Separate diagnostic policies tested read-only Codex preference-domain access and exact cfprefsd
service lookup. Those grants alone failed. Adding Apple's read-only `apple.cfprefs.` shared-memory
dependency enabled one local request/response and a zero client exit. The diagnostic remains a
failed adapter result: the CLI emitted an error item for the unknown fixture model metadata, and
the parser rejected it. The saved request advertised eight tools. The authored response requested
none. This does not prove tool enforcement, preference privacy or lifecycle qualification. The
restricted diagnostic grants have not been promoted into production dispatch.

Diagnostic evidence: `/private/tmp/part3-external-20261026/client-managed-shm`, including exact
policy, diagnostic source, request audit, raw request/output and receipt. The earlier failures
remain alongside it. All these fixtures used fresh scoped homes and no real authentication or
provider endpoint. No preference writes or global configuration changes were made.

| Verification | Result |
| --- | --- |
| Local service and denial-classifier checks | 5 passed in 0.88 seconds. |
| Full default suite | 907 passed, 65 skipped in 256.99 seconds. |
| Ruff and `git diff --check` | Passed. |
| External offline boundary fixture | 15 checks passed. |
| Installed CLI fake-service diagnostic | One authored response completed; adapter rejected explicit metadata error. |
| Production host, live provider conformance and matched Leaf River pilots | Unfinished; no production dispatch. |

Full-suite log: `/private/tmp/part3-external-boundary-tests.log`.
Source and receipt hashes: `/private/tmp/part3-external-20261026/source-snapshot.json`.
The new service guards reject duplicate requests, unexpected authentication without saving it,
wrong endpoints and invalid or oversized envelopes. They use no actual CLI or provider.

Next work is to supply explicit offline model metadata, enforce permitted tools against malicious
service responses, and qualify the preference/socket/resource/lifecycle boundaries. Then prepare
the separately authorized live conformance and matched pilot gates. Part 3 remains active.
The main checkout remains clean. No commit or push was made.


## Text-only host exchange and executable tool control, October 26, 2026

The installed CLI now completes an authored text response through a reusable pre-delivery
boundary. No real model ran. The fixture uses `gpt-5.5` metadata verified in the installed
executable's bundled catalog. Earlier attempts with an unknown fixture alias, an absent catalog
entry and an unavailable Code Mode helper remain preserved. The feature inventory was read
inside the scoped OS boundary. Execution surfaces are disabled for the text case, but advertised
tools remain visible in native requests. Configuration alone is not the tool boundary.

`hosts.response_boundary` validates a complete SSE response before returning any client bytes.
It rejects tool items, unknown events, incomplete or contradictory streams, invalid usage and
oversized output. It rebuilds assistant text, retaining reported model and observed usage in
separate evidence. Missing cache/reasoning counts remain unknown. Raw and normalized streams
remain distinct. This is a bounded text transport, not a general gateway or replacement agent
runtime.

`hosts.text_exchange.TextExchange` binds source, invocation, requested model, approved brief and
output schema. Only those approved inputs are sent to the trusted upstream callback. Native CLI
context, tools, cache keys and client metadata are omitted. One dispatch intent is committed
before the callback. Raw response artifacts use digest-named immutable storage. Recovery after
raw-save or outcome-commit faults verifies saved bytes and never calls the upstream transport
again. Uncertain transport outcomes retain their reservation. Error text is not recorded because
it can contain credentials. Oversized responses retain a bounded prefix and fail visibly.

Review found that orphan response artifacts also need to block dispatch when all acknowledgment
metadata is missing. The final implementation rejects that state before reserving another call.
A regression test deletes only synthetic fixture metadata and verifies no new callback or artifact
mutation. Competing owners, changed source, conflicting requests and corrupt outcomes also fail.
The broker operation lease is separate from the worker journal writer.

Final fixtures: `/private/tmp/part3-host-guard-20261026/`.

| Fixture | Observed result |
| --- | --- |
| `final-text` | Installed CLI completed validated text; one local HTTP request and one authored upstream callback. Only the exact approved prompt/schema was forwarded. |
| `final-control` | With response checking deliberately bypassed, the authored command created its scratch marker. A second HTTP attempt was rejected. |
| `final-blocked` | Same client execution permissions as the control; the identical tool item was retained and rejected before delivery. One HTTP request, no marker and no actionable client response. |

All three owned processes stopped. These rows cover the final fixtures only. Earlier diagnostic
fixtures remain alongside them. The source callback returns authored bytes and makes no network
request. No real authentication, provider call, scientific evaluation, Leaf River run or human
approval was involved. The control is an explicit offline diagnostic and is not available through
production scheduler dispatch.

| Verification | Result |
| --- | --- |
| Focused exchange, response, local-service and Codex tests | 46 passed in 4.03 seconds. |
| Final full default suite | 939 passed, 65 skipped in 257.69 seconds. |
| Ruff and `git diff --check` | Passed. |
| Installed wheel | Completed/rejected exchanges replayed with unchanged artifacts and zero upstream callbacks. |
| Optional Bayesian tests and Linux qualification | Not run. |
| Production host, live conformance and matched Leaf River evidence | Still incomplete. |

Full-suite log: `/private/tmp/part3-text-boundary-final-tests.log`.
Source/fixture hashes: `/private/tmp/part3-host-guard-20261026/source-snapshot.json`.
Host source identity: `ace4ecb7cca46344ebd5b76e6f5558a604e9648aa728c9c4030ccf356efa9b9d`.
Installed receipt: `/private/tmp/part3-text-exchange-install-zk_6ji6t/receipt.json`.
Wheel SHA-256: `595306be1414d73d302001c8984b319530c0eb813b79f091ae899d4506db3d4e`.
An intermediate 938-pass suite preceded the orphan-evidence guard and is not the final result.

Next work is the credentialless local endpoint and versioned host integration, followed by
preference/shared-memory privacy, socket-bypass, resource and full lifecycle qualification.
The trusted upstream callback still needs enforced endpoint, credential and timeout handling.
Live scheduler dispatch remains disabled. Separate live conformance and matched pilot authority
are still required after the host is qualified. Part 3 remains active. The main checkout is clean.
No commit or push was made.


## Packaged invocation endpoint, October 26, 2026

`hosts.text_endpoint.TextEndpoint` now connects the durable text exchange to the installed CLI.
It binds loopback and an invocation-specific route, accepts no provider credentials or client
credential headers, and forwards no HTTP headers upstream. Only the frozen prompt/schema can
reach the trusted callback. Exact retries replay saved normalized bytes without another callback.
Other request bodies cannot replace the original request. Endpoint records include the route
hash, not its bootstrap value, and never echo untrusted header, path or transport error text.

HTTP input is bounded by a connection count, 16 KiB of headers, 512 KiB of body and one absolute
read deadline. A socket reader checks that deadline while receiving, so slow clients cannot
extend it by sending another byte. Duplicate lengths and unsupported transfer/content encodings
fail before the exchange. Closing during partial headers cannot dispatch the callback.

Stop records distinguish listener closure, handler completion and local callback return. The
active-callback test verifies that closing a listener does not claim the callback stopped. A
later release completes the authored callback and permits a separate verified stop record. None
of these flags claims that remote provider computation ended. A production callback still needs
hard supervision, fixed endpoint/credential handling and its own deadlines.

Final fixtures: `/private/tmp/part3-endpoint-20261026/`.

| Fixture | Result |
| --- | --- |
| `final-text` | Installed CLI completed through the package endpoint; one request and one authored callback; all three local stop flags true. |
| `final-control` | The separate response-check bypass executed its scratch-only authored command, then rejected its second HTTP request. |
| `final-blocked` | Package endpoint rejected the identical tool item before delivery; no marker; one request/callback; all local stop flags true. |

An earlier bypass-control run completed native execution but its aggregate receipt failed when
it tried to serialize a threading event as endpoint stop data. That raw run remains under
`control`. The fixture now reads an explicitly named stop receipt. The final cases use fresh
directories and are the acceptance evidence. No physical work was inferred from that failed
serialization, and no prior artifact was overwritten.

| Verification | Result |
| --- | --- |
| Focused endpoint, exchange, response, service and Codex tests | 56 passed in 5.33 seconds. |
| Full default suite | 949 passed, 65 skipped in 253.67 seconds. |
| Ruff and `git diff --check` | Passed. |
| Installed wheel | Existing completed/rejected exchanges recovered unchanged; two local requests used one callback; listener/handler/callback stopped. |
| Production dispatch, real provider conformance and matched Leaf River pilots | Still incomplete; not run. |

The initial installed-wheel smoke was denied loopback bind by the outer task sandbox. Its log
and runtime directories remain unchanged. The same wheel passed with explicit local-socket
access and fresh runtime directories. This was not a provider failure or an automatic approval
rejection. No host was installed and no global configuration changed.

Full-suite log: `/private/tmp/part3-package-endpoint-tests.log`.
Source, archived helper files and fixture hashes: `/private/tmp/part3-endpoint-20261026/source-snapshot.json`.
Host source identity: `53f0bb3d5378ae2b0f6e2c7ccfde6b4cbda7d494ef8594b25e026cffbbdaad7a`.
Installed receipt: `/private/tmp/part3-endpoint-install-k5jk8dcw/receipt.json`.
Wheel SHA-256: `f177c6db5f5437f96b8031efc7a6c95c00cef10b454607ac2fd77c487fcf9b61`.
No real authentication, provider call, scientific evaluation or human approval occurred.
Optional Bayesian checks and Linux qualification were not run.

Next work is the separately versioned brokered Codex transport, bound native/endpoint/exchange
recovery and hard broker ownership, followed by the upstream credential/network/deadline policy
and remaining platform qualification. The full seven-increment goal remains active. Live host
and matched scientific allowances still require their separate authorization. No commit or push
was made. The main checkout remains clean.


## Version 2 transport and saved-evidence recovery, October 26, 2026

`hosts.codex_brokered` now binds native CLI execution, the package endpoint and text exchange.
Version 1 code and record behavior remain unchanged. The new experimental path uses a fresh
client home, no client provider credentials, a mandatory caller OS wrapper and explicit capability
inspection. It captures declared policy bytes and the exact wrapped command before launch.
The scientific controller and public production-host rejection remain unchanged.

The exchange namespace binds the physical nonce and invocation directory, in addition to the
logical call ID. This prevents another run with the same call number from supplying its exchange.
Recovery verifies prompt/schema artifacts, native command/environment/input, process completion,
current group absence, endpoint binding, stop-chain records and the original outcome. Successful
CLI text must equal saved broker text. Provider-reported usage remains separate from CLI defaults.
Missing cache counts stay unknown even when the client reports zero.

The first deadline test caught an idle endpoint observer that had not exited during a shortened
stop wait. The final profile records a bounded 0.2-second stop grace and counts it in elapsed time.
This does not extend the model deadline or permit a late successful handoff. Active callbacks
still return `reconciliation_required`. A later owned stop capture can resolve that uncertainty
without changing the original outcome or invoking upstream again. Unverified native stops and
missing native receipts remain explicit unresolved cases, not permission to relaunch.

The final installed-CLI fixtures are under `/private/tmp/part3-brokered-20261026/`:

| Fixture | Result |
| --- | --- |
| `final-text` | Completed through the version 2 package path with captured external policy bytes. |
| `final-tool` | The package rejected an authored tool item before delivery; native failure remained visible. |
| `final-lost-ack` | Lost final acknowledgment recovered from saved native, endpoint and provider artifacts. |
| `final-timeout` | Native deadline first left an active authored callback unresolved; after release/verified stop, recovery retained the original timeout and newly available usage. |

Each row covers one native client and one authored callback. All final native/endpoint stops were
verified. Replaying each tree changed no bytes and made no call. Earlier pre-namespace development
fixtures remain alongside the final cases. These are not real model runs, live worker campaigns,
scientific evaluations, independent confirmations or human approvals.

| Verification | Result |
| --- | --- |
| Focused version 1/2, endpoint, exchange and response tests | 68 passed in 14.37 seconds. |
| Full default suite | 965 passed, 65 skipped in 280.01 seconds. |
| Ruff and `git diff --check` | Passed. |
| Installed wheel | Recovered all four final outcomes unchanged; zero new clients, callbacks or provider calls. |
| Production dispatch, upstream credential/egress policy, live conformance and matched pilot | Unfinished. |

Tests cover conflicting CLI output, malformed/flooded transcripts, missing provider response,
launch/final acknowledgment loss, prelaunch timeout, queued cancellation, active callback recovery,
unknown usage, boundary mutation, cross-run native/exchange substitution, relabeled outcomes and
stale successful stop receipts contradicted by live group observation.

Full-suite log: `/private/tmp/part3-brokered-transport-tests.log`.
Source archives and receipt hashes: `/private/tmp/part3-brokered-20261026/source-snapshot.json`.
Host source identity: `7dce348db223776d93b6d06f73232d94dccb8fc111286fc756cc35b86023958d`.
Installed receipt: `/private/tmp/part3-brokered-install-zd7jmnkm/receipt.json`.
Wheel SHA-256: `b3ff15c701d223008843dba68fb1e99b92d68d051de96af38eb551b80fe02a78`.
Optional Bayesian checks and Linux qualification were not run. No real authentication or provider
endpoint was used. No commit, push, host installation or global configuration change was made.
The main checkout remains clean.

Next is hard broker ownership and parent-death handling, followed by a fixed, bounded upstream
transport with credentials outside the client. Then integrate the qualified version 2 path and
recovery artifacts into worker records/scheduler. Production dispatch stays disabled until those
and the remaining host boundary checks pass. The original seven-increment objective remains active,
including separate live conformance and the authorized matched Leaf River evidence.

## Watchdog-owned upstream execution, October 26, 2026

`hosts.command_upstream.CommandUpstream` runs one trusted authored transport command behind the
text exchange. It uses private request/response files, fixed argument slots, declared source hashes,
a sanitized environment, an absolute monotonic deadline and bounded diagnostic/response capture.
The callback cannot reuse an existing attempt directory. Saved successful response bytes can be
recovered after a final acknowledgment fault without another process or provider request.
Invalid, partial, empty, oversized, symlinked, changed-source and late responses cannot be delivered.
Executable and declared script arguments use the resolved paths whose bytes were hashed.
A regression test changes both original symlinks after construction and verifies that the
declared physical executable/script still run. This closes a path-binding gap found in review.

The POSIX supervisor now has an opt-in independent watchdog. It is ready before the launch gate
opens and binds its nonce, target identity, job digest and current watchdog/trampoline source bytes.
The trampoline retains the nonce-bearing group leader while descendants remain. The watchdog
checks target start time, command nonce and PGID before TERM/KILL. Parent death and deadline tests
verify group cleanup, including a descendant that ignores TERM after its direct parent exits.
Stale nonce/start bindings do not signal an unrelated group. A blocked launch callback does not
open the gate after expiry. A competing supervisor stop is reobserved before reporting uncertainty.
An early test caught that final race, and a regression case now covers it.

Read-only stop recovery checks job/receipt/source bindings and current group absence. Complete
upstream recovery additionally verifies command/environment/input, response ownership and digest,
and acceptance before the original deadline. A local stop cannot establish remote cancellation or
invent missing response/usage evidence. The current native Codex supervisor remains unchanged.
Its parent-death behavior is still an open acceptance item, along with the pipe-based owner lease
described in the host-boundary plan. This increment grants no new scheduler or scientific authority.

| Installed-CLI fixture | Final result |
| --- | --- |
| `final-text` | Completed with one authored upstream process and verified local stops. |
| `final-tool` | Forbidden authored tool response rejected before delivery. |
| `final-lost_ack` | Saved version 2 transport and upstream response recovered without another launch. |
| `final-timeout` | Native client and authored upstream process timed out and stopped; no manual callback release, successful response or inferred usage. |

Fixtures, source archives and exact receipts are under
`/private/tmp/part3-owned-upstream-20261026/`. Each fixture uses one native client and one authored
callback. Every replay left its tree unchanged. The isolated wheel recovered all four fixtures
and ran one new authored command through its installed watchdog/trampoline files.
Final source receipt: `source-snapshot-final.json` under that fixture parent. Earlier fixtures and
snapshots remain alongside it.
Installed receipt: `/private/tmp/part3-owned-upstream-final-install-rf3g1z84/receipt.json`.
Host source identity: `88a426141d1a0dc8056c50de91abf912dce6e47be2be32c9ae0af4bde891ae2f`.
Wheel SHA-256: `26b74571e3e1ad64f32f9b466a068ddd4e19ae35124971121fc85026c819e594`.

The final focused host suite passed 102 tests in 23.34 seconds. Ruff passed.
The first full default suite reported 988 passed, 65 skipped and one failure in
`test_watchdog_deadline_removes_unstarted_or_kills_owned_running_container[running]`.
That existing fake-Docker watchdog returned uncertainty before its readiness record. Its cause is
unidentified. Both cases passed on a focused rerun in 1.23 seconds. The initial full log and authored
failure files remain at `/private/tmp/part3-owned-upstream-tests.log` and
`/private/tmp/part3-owned-upstream-20261026/adverse-initial-container-watchdog/`.
An intermediate full recheck passed 989 tests with 65 skips in 289.05 seconds. Its log is
`/private/tmp/part3-owned-upstream-tests-recheck.log`. The final run covering the resolved-path
regression passed 990 tests with 65 skips in 292.50 seconds. Its log is
`/private/tmp/part3-owned-upstream-tests-final.log`. The initial unexplained failure remains
preserved rather than relabeled as a successful run. Ruff and `git diff --check` passed.

No real authentication, provider, live scientific evaluation, live worker campaign, Bayesian benchmark
or Linux qualification was run. No dependency installation, host configuration change, commit or
push occurred. The main checkout remains clean, and the user's initial four-line development-plan
addition remains unchanged. The private wheel target is the only new package installation.

Part 3 remains incomplete. Next, close native-client parent-death/startup recovery and the owner
pipe lease. Then implement and qualify the fixed credential/egress transport, integrate worker
records and production recovery, and prepare the separate live conformance and matched-pilot
approval packet. No live call or Leaf River allowance has been consumed.

## Inherited owner lease and native profile 2.1, October 26, 2026

The opt-in native profile now binds `codex-text-2.1` to watchdog supervision. Default version 2.0
native jobs and version 1 remain unchanged. Recovery derives the required job fields from the
profile and rejects a relabeled 2.1 record. This SDK option is not a production host registration.

Only the supervisor holds the anonymous pipe's write end. The trusted trampoline and watchdog
inherit the read end, while command executables inherit neither end. EOF signals owner loss
without depending on PID reuse timing. The worker checks its lease before the gate and before
command launch. The watchdog retains nonce/start/PGID checks before signaling. Tests explicitly
leave the pipe open with unusable owner PID metadata, then close it and verify cleanup. Another
case closes the lease before watchdog startup and verifies that the command never launches.

Known trampoline spawn errors leave a stopped failure with no identity. Watchdog spawn/readiness
failures leave an immutable abort receipt after reaping the direct child or observing a known
failed spawn. Startup deadline expiry returns timeout. Late ownership acknowledgments and queued
cancellation cannot open the gate. Recovery verifies abort/job/source bindings, current group
absence and that no launch gate exists. Callback exceptions retain failure evidence and propagate.

The 118-test focused host suite passed in 33.76 seconds. It covers both legacy profiles, the new
owned profile, native/upstream death, endpoint and response boundaries, startup failure, expiry,
cancellation, lost acknowledgment, profile downgrade, corruption and read-only replay. Native
parent-death tests observe endpoint closure separately from stopped process groups. Missing
native completion remains unresolved and cannot produce a successful handoff.

The installed CLI passed four final offline fixtures with both ownership options:

| Fixture | Result |
| --- | --- |
| `final-text` | Completed; native/upstream stops verified and replay unchanged. |
| `final-tool` | Authored tool response rejected before delivery; native/upstream stopped. |
| `final-lost_ack` | Saved response and transport recovered without another launch. |
| `final-timeout` | Native/upstream timeout and local stop verified; no successful late response. |
| `final-death` | Supervisor killed during an authored request; both groups absent, endpoint closed, missing completion refused. |

Each fixture used one installed native client and one authored upstream callback. No provider or
scientific call occurred. An earlier development death fixture remains alongside the final cases.
The final wheel rechecked all saved stop/replay evidence and ran one new authored command using
its installed scripts. It started no additional client, made no provider call and read no real
credentials. Current source/receipts are under `/private/tmp/part3-owned-native-20261026/`, with
all bound host sources and test/fixture scripts archived in `sources/`.
Source receipt: `/private/tmp/part3-owned-native-20261026/source-snapshot.json`.
Installed receipt: `/private/tmp/part3-owned-native-install-wx0umf80/receipt.json`.
Host source identity: `49bcb4b6716af51a7d62b3fd218f21f9a418ad82cb0fc536a5513612006da236`.
Wheel SHA-256: `60a5ba82a0ee3ef4c9b1f064c517b1250eb53473ff227d7c740c244d5ae14942`.

Ruff and `git diff --check` passed. The full default suite passed 1,006 tests with 65 skips in
298.64 seconds. Its log is `/private/tmp/part3-owned-native-tests.log`.
The earlier unexplained fake-container inspection failure from the previous increment remains
preserved with its failed log and authored state. No frozen gate or scientific closure changed.
No live conformance, Leaf River pilot, Bayesian benchmark or Linux qualification was attempted.
No commit, push, dependency installation or host configuration change occurred. The private wheel
target is the only new package installation. The main checkout and initial four-line user change
in the worktree's development plan remain unchanged.

Part 3 remains incomplete. Next is the fixed provider transport with a scoped credential file,
egress policy and explicit provider/usage uncertainty. Then finish host resource/privacy
qualification, integrate versioned worker dispatch and pending-invocation reconciliation, and
prepare the separate live conformance and matched-pilot approval packet. Owned local stop is not
proof of remote provider cancellation or a substitute for missing response/usage evidence.

## Fixed subscription transport, October 26, 2026

`ScopedSubscriptionUpstream` now binds a single fixed subscription request to the existing owned
command supervisor. The standalone worker has no endpoint override, proxy environment, redirect,
refresh, API-key fallback or HTTP retry. It configures certificate/hostname verification and TLS
1.2 or later. The fixed backend and bearer/account headers follow the
[official gateway documentation](https://learn.chatgpt.com/docs/enterprise/sign-in-with-chatgpt-through-a-gateway).
No production HTTPS request has been made, so server acceptance, TLS behavior and account/model
access remain unverified. This implementation does not authorize a live call.

An explicit owner-private lease stays outside the attempt and declared client roots. The worker
opens physical directory/file descriptors, rejects symlinks/hardlinks or exposed modes, checks the
lease ID and declared expiry, and never copies credential bytes or hashes into manifests. This
package-specific lease is not a parser for the user's native auth cache. Credential preparation,
refresh and real-account validation remain unfinished. No existing auth cache was opened.

The worker verifies the approved request digest, model, exact permitted fields, user brief,
`store: false`, no tools and strict schema format. Header, response and total parser-byte ceilings
cover HTTP chunk framing/trailers. Ambiguous framing, compression, oversized/partial responses
and full credential reflection are rejected. Reflection inspection handles raw and escaped JSON
across the SSE data forms accepted by the response boundary. An early cleanup test found a missing
reader `flush` method. Review then found that no-space and multiline SSE fields needed equivalent
reflection checks. Those cases now have regression coverage. Raw error bodies and exception text
are discarded. Receipts retain phase, HTTP status, request uncertainty and unknown usage.

The final focused host suite passed 156 tests in 36.56 seconds. This includes 38 subscription tests.
Actual owned-process checks cover invalid/cancelled leases, an authored HTTP factory, reflection,
slow headers, watchdog cleanup and replay after removing the synthetic lease. Subscription-decoder
unit tests supply the separately tested process proof explicitly and are not production HTTPS
recovery evidence. The real decoder checks fixed-command/source/policy/scope/provider bindings.

Four final installed-CLI fixtures used the new worker through an explicitly authored loopback
connection factory and synthetic credential file outside the client directories:

| Fixture | Result |
| --- | --- |
| `verified-text` | Completed; one authored HTTP request, no credential values in client artifacts. |
| `verified-tool` | Authored tool response rejected before delivery; stops and replay verified. |
| `verified-lost_ack` | Saved response recovered without another client, callback or request. |
| `verified-timeout` | One actual authored HTTP request timed out; upstream stopped before fixture-server release. |

Each final fixture uses one native client and one authored upstream callback/request. All local
stops are verified. Replays leave the saved trees unchanged. The helper's production-HTTPS flag is
false, and its records fail the production subscription decoder's fixed-command check. The earlier
`frozen-timeout` case used a 0.5-second fixture budget and correctly expired during preflight with
zero HTTP requests, failing the in-flight fixture criterion. Its original receipt remains intact.
The new in-flight fixture has an explicitly recorded 1.5-second budget and a fresh directory.
No scientific gate, resumed budget or prior outcome was changed. Earlier development cases remain.

The isolated installed wheel replays all four final trees, verifies native/upstream stops and
refuses to treat authored HTTP as a production exchange. It also launches its actual fixed worker
once with a deliberately mismatched synthetic lease, verifies preflight rejection with no request
intent or diagnostic output, removes the lease and verifies read-only failure recovery. No real
credential, production HTTPS, provider or live scientific call occurred.

Source archives and exact receipts: `/private/tmp/part3-subscription-20261026/source-snapshot.json`.
Installed receipt: `/private/tmp/part3-subscription-install-ru1i_ckc/receipt.json`.
Host source identity: `8cba6a3d38ca6bbc259d95f04a9cec9ff0a674f102c7876f336469d474588263`.
Wheel SHA-256: `0460fecc5b9a1774cef1a4aa9d7a93c7301d5c056a74df1478248ea2b60e9274`.
Focused log: `/private/tmp/part3-subscription-host-tests-frozen.log`.
Ruff and `git diff --check` passed. The default suite passed 1,044 tests with 65 skips in
301.03 seconds. Its log is `/private/tmp/part3-subscription-default-tests.log`.

Part 3 remains incomplete. Next, prepare the explicit credential-source/refresh policy and finish
OS egress, TLS, privacy/resource qualification and capability evidence before production worker
registration/reconciliation. Separately authorized live conformance and the matched Leaf River
pilot remain unattempted. No dependency installation, host configuration change, commit or push
occurred. Only a private wheel target was installed. The main checkout and the user's original
four-line development-plan addition remain unchanged. Prior adverse records and scientific gates
are preserved. No live provider or Leaf River allowance has been consumed.

## Explicit credential preparation/recovery and loopback TLS, October 26, 2026

`credential_lease` adds explicit managed-cache preparation without source discovery, login,
refresh, source modification or network access. The parser uses the managed ChatGPT fields
listed in the [official CI auth guide](https://learn.chatgpt.com/docs/auth/ci-cd-auth).
It requires an explicit expected account and UTC expiry, rejects API-key/external-token modes
and unknown fields, and bounds its source read. A custom seven-day freshness policy and a
30-to-900-second lease window limit this package's snapshot. They do not establish actual token
expiry, server validity or compatibility with the user's real cache. No real cache was opened.

The new helper reserves a fresh private destination before reading secrets. Unsafe modes,
symlinks/hardlinks, account mismatch, stale/future refresh metadata, source rotation, client-root
access and Git checkout destinations fail with static reasons. Source bytes remain unchanged.
Only the access-token/account fields needed for the lease are copied. Refresh/ID-token fields
are excluded, and receipts contain no secret value or hash. Partial destinations cannot be reused.

Read-only prepared-lease recovery requires the original lease ID, expected account and expiry.
It reads the prepared lease and scope-bound commit receipt without reopening the source or
writing files. Missing receipts, changed account/expiry, expired leases and copied foreign scopes
fail. It cannot reseed credentials, extend expiry or turn server validity into a verified claim.

The focused host suite passed 188 tests in 34.84 seconds, including 29 preparation/recovery tests
and three real loopback TLS tests. TLS uses a private ephemeral CA added only to a fixture
connection context. Certificate/hostname verification stays enabled. A valid local connection
sends one approved request, while an untrusted CA and wrong hostname fail before HTTP is observed.
This does not qualify the production peer, the system CA policy or account/model access.

Four final installed-CLI fixtures under `/private/tmp/part3-credential-tls-20261026/` passed:
`final-text`, `final-tool`, `final-lost_ack` and `final-timeout`. Each uses one native client and
one authored upstream callback/request. Each now prepares the lease from a synthetic managed
cache outside client roots. Source bytes remain unchanged, refresh/ID fields stay out of the
lease, and access/refresh/ID/account values stay out of client artifacts. Native/upstream stops
are verified, and replay changes no saved bytes. The in-flight timeout uses the explicit
1.5-second fixture budget and stops upstream before releasing the authored server. Earlier
pre-recovery development fixtures remain alongside these final source-bound cases.

The initial wheel test recovered fixtures but failed test collection because a repository-only
example helper was not on its test path. That target and log are preserved at
`/private/tmp/part3-credential-tls-install-wzb21r4d/`. The corrected harness adds only the repository
fixture path after loading the wheel package and asserts package module origins. A fresh private
target passed all 32 preparation/recovery/TLS tests, verified saved lease/transport receipts and
replayed all four fixture trees. Expired saved leases are refused rather than renewed. The actual
fixed worker also ran once with an intentionally invalid synthetic lease and no request intent.
No new native client or provider request was launched by that final wheel check.

Source archive/receipts: `/private/tmp/part3-credential-tls-20261026/source-snapshot.json`.
Final installed receipt: `/private/tmp/part3-credential-tls-install-recheck-rmjq15gz/receipt.json`.
Installed test log: `check.log` in that directory.
Host source identity: `7e3579571e0e850966435490211fc9c36b27cc4a50e829c0fd5b721899623a2d`.
Wheel SHA-256: `75976e22e063559f46396fe90e7d28f9755451c954481154f0ac3e978644fb0e`.
Focused log: `/private/tmp/part3-credential-tls-host-tests-final.log`.
Default suite: 1,076 passed, 65 skipped in 300.97 seconds.
Default log: `/private/tmp/part3-credential-tls-default-tests.log`.
Ruff and `git diff --check` passed. Prior adverse records and scientific closures/gates are intact.
No dependency installation, host configuration change, commit or push occurred. Only private wheel
targets were installed. The main checkout and the user's original four-line development-plan
addition remain unchanged. No real auth cache, production HTTPS or live scientific run was used.

Part 3 remains incomplete. The next implementation work is native boundary/capability qualification
and versioned production dispatch/reconciliation, followed by the concrete live-conformance and
matched-pilot approval packet. Pin the relevant OS/TLS environment in qualification evidence.
Keep the plan's host time/transcript/workspace limits distinct from the generated Docker resource
gates. No live provider or Leaf River allowance has been consumed.

## Pinned native adapter and offline four-role integration, October 26, 2026

`BrokeredCodexHost` now connects the version 2.1 owned transport to the scheduler. A new version
2.1 host selection pins the qualification digest before its first call. Capability and journal
validation enforce that binding. Version 1.0 host selections retain their original serialized
fields. The public CLI still rejects production dispatch, and no qualified profile is shipped.

The native-profile reader checks trusted pinned attestations, source/runtime/policy/executable
bindings and all referenced artifacts. It does not run qualification probes or establish the
truth of authored observations. Runtime inventory includes the OS build, Python executable,
TLS library and public trust-root identity from a clean environment. No real auth file is read.
The fixed macOS policy permits only the inventoried executable, staged directories, necessary
system reads/services and the chosen loopback endpoint. Its preference access and writable-home
behavior still need privacy and size qualification.

The adapter persists the exact framed prompt and a context manifest. A strict outer transport
object carries the core role response as a string. Raw native output and normalized handoffs stay
separate, and the scheduler retains typed role validation. Preparation counts against the original
deadline. Known setup failures and expired preparation produce durable results without launching
a client. Provider-aware reconciliation restores saved model/usage and checks the original context
without another call. Missing receipts, unknown ownership and incomplete parent-death completion
remain unresolved. They are not silently retried or reported as successful.

All 80 focused tests passed in 13.92 seconds. They cover malformed envelopes, invalid inner roles,
lost final acknowledgment, changed configuration/pins, prelaunch setup/deadline failures and actual
fixed-worker rejection of a missing synthetic lease before any request intent. Decoder tests use
authored attestations and synthetic platform metadata. Adapter tests substitute qualification and
the native wrapper. Neither test group supplies actual OS qualification.

The actual installed Codex executable ran seven clients across all four roles through the fixed
macOS policy and scheduler. Seven authored callbacks produced two synthetic scientific attempts,
an accepted fixture candidate and unchanged replay. Qualification was explicitly stubbed, no real
credential was used and provider calls were zero. This is integration evidence only. The source
fixture is `/private/tmp/part3-native-adapter-20261026/pinned-four-role/receipt.json`.

The installed wheel passed 39 focused tests and the same seven-client workflow after staging its
declared scientific fixture sources at the trusted registry root. Package module origins were
checked against the private wheel installation. The first harness failed because an unrelated
`/private/tmp/inspect.py` shadowed Python's standard library in subprocess tests. A second harness
passed its tests, then correctly refused missing fixture sources at the registry root. Both logs
and incomplete trees remain. The final fixture stages the supplied source inputs and verifies
their imported locations without adding `src` to the import path.

Installed receipt: `/private/tmp/part3-native-adapter-20261026/installed-receipt.json`.
Installed test log: `/private/tmp/part3-native-adapter-installed-check-v2.log`.
Installed fixture log: `/private/tmp/part3-native-adapter-installed-fixture.log`.
Source archive: `/private/tmp/part3-native-adapter-20261026/source-snapshot.json` (208 files).
All 119 installed Python package files match the archived worktree sources byte for byte.
Host source identity: `6fb08fd0ef69beb450c5110d299d9c7aee5b960b8facf5cf57e8cac974b2be1a`.
Wheel SHA-256: `e2bf03fb8d50e759b69333869b7cbfb29bd8662e29a25193a3b2985d1819cd99`.
Focused log: `/private/tmp/part3-native-adapter-pinned-tests-final.log`.

The default suite passed 1,098 tests with 65 skips in 332.40 seconds. Its log is
`/private/tmp/part3-native-adapter-default-tests.log`. The updated documentation contracts passed
19 tests in 0.62 seconds. Ruff and `git diff --check` passed. The optional Bayesian suite was not
run because no Bayesian behavior changed. Existing scientific closures and benchmark gates remain
unchanged, and no old benchmark matrix was rerun.

Part 3 remains incomplete. Next, implement and review actual native-boundary qualification,
including privacy and workspace bounds, then expose explicit pinned configuration in the CLI.
Prepare the frozen live-conformance and matched Leaf River approval packet after those gates.
No production profile, real credential, provider connection, new Leaf River allowance, scientific
gate change, host configuration change, dependency installation, commit or push occurred.
Only a private wheel target was installed. The original main checkout remains unchanged.

## Native permission canaries and pinned recovery

The new `hosts.native_canaries` producer exercises the fixed macOS policy through actual syscalls.
It compiles only the package's fixed trusted C source with the existing `/usr/bin/clang` driver.
Compiler, control and confined runs use bounded owned processes and watchdogs. No dependency,
global preference or host configuration is installed or changed.

All fifteen observations passed on local macOS ARM64. Synthetic private, checkout, evaluator,
cache and lease reads were denied. Outside/workspace writes, read/write symlink escapes, a
different executable and forbidden TCP/Unix connections were denied. Approved brief reads,
home writes and the designated loopback connection succeeded. An unrestricted control first
opened the same files and connected to both forbidden listeners. Permission errors are required,
so absent files and failed listeners cannot count as denials. The allowed listener accepted two
connections across both runs. Each forbidden listener accepted exactly its unrestricted control
and none from the confined run. Private canaries stayed unchanged, no synthetic private value
appeared in probe output, all listeners stopped and process groups were verified absent.

The compiled probe substitutes for Codex in the exact executable literal. The result measures
policy permissions only. Its receipt always reports `host_qualified: false` and lists native
behavior, preference privacy, lifecycle and full qualification as unverified. It cannot pass
the production native-profile reader. No real credential or model/scientific call was made.

Pinned recovery verifies raw/source/policy artifacts, exact commands/environments, compiler/probe
identities, current source/runtime and watchdog/process receipts. It reruns no compiler or canary
and leaves the evidence tree unchanged. Runtime inventory still starts a clean bounded Python
process to hash public CAs, and ownership checks use process inspection. The initial manual
`recovery.json` called this `new_processes: 0`; that field was too broad. The installed receipt
uses `new_compiler_or_canary_processes: 0` and explicitly records inventory/inspection instead.
Foreign copied scopes and a corrupt artifact are rejected in preserved adverse fixtures.

The focused suite passed 56 tests in 17.62 seconds. An initial unit test used pytest's long
temporary path and hit macOS's Unix socket length preflight before its intended reuse assertion.
The corrected test uses its own short private temporary directory and verifies that existing
bytes survive without a launch. The failed log remains. Twenty-one tests passed against a
private wheel installation, which also verified pinned recovery of the actual OS evidence.
Package module origins were checked. The earlier development probe remains, without a claim
that its superseded source identity can recover under the final implementation.

Final evidence: `/private/tmp/part3-native-canaries-20261027/final/receipt.json`.
Receipt pin: `28e280046ed516655334716d69437b1e31e47f43017811dc9391b8cdd9584f89`.
Adverse cases: `/private/tmp/part3-native-canaries-20261027/adverse.json`.
Installed receipt: `/private/tmp/part3-native-canaries-20261027/installed-receipt.json`.
Focused log: `/private/tmp/part3-native-canaries-focused-tests.log`.
Installed log: `/private/tmp/part3-native-canaries-installed-tests.log`.
Host source identity: `61e5377a9b0bfc8b9f39a7de3c684b0cfe1f68a66babe6a7e93254cc2d0e6409`.
Wheel SHA-256: `bed726a7e86f355cd292141cc6180f5e2dd3106e11275bf057f4529636274e13`.

The default suite passed 1,108 tests with 65 skips in 323.47 seconds. Its log is
`/private/tmp/part3-native-canaries-default-tests.log`. Updated documentation contracts passed
19 tests in 0.62 seconds. Ruff and `git diff --check` passed. The optional Bayesian suite was
not run because no Bayesian behavior changed. No historical benchmark matrix was rerun.
The source archive is `/private/tmp/part3-native-canaries-20261027/source-snapshot.json`, with
188 files. All 120 installed Python package files match the worktree byte for byte.

Part 3 remains incomplete. Native preference/service privacy, complete qualification, explicit
production CLI configuration, authorized live conformance and the matched Leaf River pilot
remain. The source audit and proposed next preference check are recorded in the host-boundary
plan. No real preference value was opened, no live allowance was consumed, and no commit/push or
scientific closure/gate change occurred. The main checkout remains unchanged.

## Preference failure, strict boundary and explicit native candidate

The follow-up tests found a concrete isolation failure in the earlier shared-memory prefix grant.
The confined probe mapped an unrelated synthetic `apple.cfprefs.ae.*` object and verified its
public payload. The 1.1 permission receipt failed at `unapproved_preference_shm_denied`. The
shared-memory test named and mapped only its own synthetic object. A synthetic CoreFoundation
private plist was denied,
while the approved workspace plist could be read. These results are preserved separately.

The installed 0.164.0 client completed the authored workflow after removing only the explicit
preference-read grant. Removing shared-memory access, or allowing only metadata, stopped startup.
A proposed `preference-key` policy filter was unsupported. A metadata-only absence check would
not contain the demonstrated shared-memory capability, so it was not added as a substitute.

An inventory found the already installed 0.155.1 binary. It has the required brokered flags and
completed a fresh four-role fixture with all preference grants removed. The fixed package policy
now denies preference reads, cfprefsd lookup and POSIX shared memory. No installation or global CLI
selection changed. The explicit candidate SHA-256 is
`26d4d42df9846aaeedce4a9c8c7cfa9e209fc8710fb2ab2b972a151c79463600`.
This result applies to that binary and boundary, not arbitrary versions or actual provider access.

The 1.1 prototype also required a successful workspace CoreFoundation read. The strict policy
denied that API, so that record failed too. Version 1.2 defines a stricter service scope: both
private and workspace preference-service reads must be denied, while ordinary approved file
reads remain required. Its shared-memory denial and all original filesystem/network checks are
required. Both failed 1.1 records remain intact. The earlier broad policy and 0.164.0 candidate
were not relabeled as passing, and no scientific or historical benchmark criterion changed.

All eighteen observations passed under 1.2. Unrestricted controls read both synthetic plists and
the shared-memory object. The confined probe denied them. The owned object was unlinked, and
recovery verified its absence. An initial shared-memory harness incorrectly used descriptor I/O
instead of macOS mmap, then had a payload-length mismatch. Both failures, their sources and the
corrected harness are retained. No existing object or preference was written.

The final explicit-candidate four-role fixture started seven native clients, used seven authored
callbacks and two synthetic scientific attempts, accepted the fixture candidate and replayed
without new work. Its receipt records version, executable, digest and explicit selection. The
qualification dependency was stubbed, so it remains integration evidence and reports false for
host qualification and production dispatch. Requested catalog metadata is `gpt-5.5`; no real
model, credential or provider was used.

Four strict-policy subscription fixtures passed: text, forbidden tool response, lost final
acknowledgment and in-flight timeout. Each used one native client, one authored callback and one
authored HTTP request. Native and upstream stops were verified, synthetic credentials stayed out
of client artifacts, source-cache bytes stayed unchanged and replay changed no files. The timeout
retains its explicit 1.5-second budget. Authored HTTP remains distinct from production HTTPS.

The strict cancellation fixture stopped native and upstream work after one authored HTTP request,
before server release. Usage stayed unknown. Its first harness incorrectly tried to recover a
successful upstream body after cancellation. That incomplete tree and log remain. The corrected
fresh fixture expects cancellation and passed. The actual strict supervisor-death fixture verified
both watchdogs stopped their groups after owner loss and the endpoint closed. Missing completion
remains unsuccessful and unreconciled rather than becoming a fabricated host result.

The installed wheel passed 27 preference/profile tests, verified unchanged permission replay and
reconstructed the seven-call worker report. Separate installed checks replayed all four strict
transport fixtures and the cancellation/death evidence without new native or provider calls.
Their production decoder refuses the authored HTTP factory. Runtime inventory and process
inspection still occur during recovery. All tested package module origins were from the wheel.

Evidence root: `/private/tmp/part3-preferences-20261027/`.
Strict permission receipt: `strict-v12-canaries/receipt.json`.
Permission pin: `cbeb59593c0fd820e963665b24802f907ebf438ca34eb979d8bb2bd37666c2a6`.
Four-role receipt: `final-four-role/receipt.json`.
Transport receipts: `strict-{text,tool,lost_ack,timeout}/receipt.json`.
Cancellation receipt: `final-cancel/receipt.json`.
Supervisor-death receipt: `strict-parent-death/receipt.json`.
Installed receipts: `installed-receipt.json`, `installed-transports.json`,
`installed-cancel-death.json`.
Host source identity: `356a4dafd4e25885e65ecdb163e93619a9e35af57b57d325e0d844e50e13d486`.
Wheel SHA-256: `98fc56683a487849b1b081db9d0bcb7c126d788bf2c3938c44bae85429599034`.

The final core default suite passed 1,114 tests with 65 skips in 315.24 seconds. Its log is
`/private/tmp/part3-preferences-v12-default-tests.log`. After the example cancellation/death routes
were added, the focused suite passed 109 tests in 21.92 seconds, plus the actual fixture checks.
Its log is `/private/tmp/part3-preferences-final-focused-tests.log`. Ruff and `git diff --check`
passed. No Bayesian behavior changed, so its optional suite was not run. No historical benchmark
matrix or live Leaf River allowance was used. The main checkout remains unchanged.
Final documentation contracts passed 19 tests in 1.31 seconds. The source archive is
`/private/tmp/part3-preferences-20261027/source-snapshot.json` (188 files), and all 120 installed
Python package files match the worktree byte for byte.

Part 3 remains incomplete. Next, safely reconcile abandoned owned transports without fabricating
success or usage, assemble the native qualification from actual evidence and expose pinned CLI
configuration. Then prepare the concrete real-auth/provider-conformance and matched Leaf River
approval packet. No real auth cache was opened, no provider was contacted, and no global config,
scientific closure/gate, dependency environment, commit or push changed. Only a private wheel
target was installed.

## In-flight abandonment recovery with unknown usage and duration

The registered adapter now retires an in-flight abandoned call as `host_failure` after verifying
both owned groups stopped and the original supervisor disappeared. The result has no resolved
model or normalized role output. Usage and duration remain unknown. `HostResult` now permits a
null duration for unsuccessful outcomes, matching the worker journal's existing optional field.
Completed results still require a measured duration. The original invocation remains charged.

Recovery verifies the saved adapter selection and original journaled native ownership. The SDK
proof binds native command, prompt, schema, captured/live policy, approved exchange request and
fixed upstream request/command. Both watchdog records must name the same supervisor PID/start
time. A successful process listing establishes owner absence without command-line disclosure.
Failed observation remains pending. The source-bound endpoint lived in that supervisor and its
listener descriptor was not inherited by workers, so recovery need not contact the old port.
It sends no signal and starts no replacement native/upstream work.

The fixed subscription verifier now checks the exact worker path and three declared sources.
It rejects extra source files and a claimed worker alias to the credential, before attempting
source reads. Model, lease ID and credential-path metadata must match the original host selection.
No credential or response is opened by this verifier. Live fixed-worker paths are not migrated
between package installations. The journal and read-only SDK inspection remain distinct from
that live configuration boundary.

The new path covers owner death before native completion and SDK timing/stop/outcome commits,
with native and upstream watchdog proof available. Existing result records use their normal
decoder and corruption checks. Missing startup ownership or other partial commit gaps remain
pending. The initial proof does not invent duration, completed bytes or provider usage, and it
does not claim that remote computation stopped. A private recovery artifact records hashes of
the bound proof and `raw_result_recovered: false`. Physical transport files remain unchanged.

Process tests held the actual fixed subscription command behind its launch gate. Its preflight
could not open the deliberately missing lease or attempt a provider connection. A live supervisor
was refused. After killing only that fixture's supervisor, both watchdogs stopped their groups,
recovery cleared the pending invocation as failure and repeated recovery started no new work.
Changed request, lease metadata, native job, owner record, journaled process identity and partial
completion were all rejected, preserving pending state. Failed process observation was also
rejected. Native qualification and the unit executable/wrapper remain explicitly synthetic.

The actual installed 0.155.1 binary then passed the same journal path under the strict package
policy. One native invocation was charged. The fixed upstream stayed gated before credential
preflight, both groups stopped, the physical tree replayed unchanged, and model/usage/duration
stayed unknown. Qualification was stubbed, and the fixture reports `host_qualified: false`.
The exact fixture source and native inventory are retained. No scientific attempt was started.

The first unit run used the wrong synthetic executable filename. That log remains. A subscription
decoder unit fixture also supplied only one source, whereas the strengthened contract requires
the full three-file closure. The corrected fixture supplies those public code/policy hashes and
still labels its delegated process proof as synthetic. Extra-source and credential-alias cases
now verify rejection. No real credential value or hash was read or written.

The focused suite passed 97 tests in 19.38 seconds. The default suite passed 1,125 tests with
65 skips in 323.72 seconds. An isolated wheel passed 49 abandonment/subscription tests, using
the installed package in their child supervisors. It also reconstructed the source-produced
native failure through the read-only SDK and worker report without changing its evidence tree.
That inspection does not claim migration of the live fixed-worker path. No new native/provider
call was made during replay. Final documentation contracts and lint are recorded below.

Evidence root: `/private/tmp/part3-abandoned-20261027/`.
Final native receipt: `source-bound-native/receipt.json`.
Installed receipt: `installed-receipt.json`.
Focused log: `/private/tmp/part3-abandoned-final-focused-v2.log`.
Default log: `/private/tmp/part3-abandoned-default-tests.log`.
Installed log: `/private/tmp/part3-abandoned-installed-tests.log`.
Host source identity: `71e4b743fa489af867917af24528c519bfe170d89efe280b488360d67659b8bf`.
Wheel SHA-256: `143de792d4ac796771c79d6f6909660cc9bf951258a553ada5dfede0b7f76a94`.
Source archive: `/private/tmp/part3-abandoned-20261027/source-snapshot.json` (191 files).
All 121 installed Python package files match the worktree byte for byte.
Final documentation contracts passed 19 tests in 0.77 seconds. Ruff and `git diff --check` passed.

Part 3 remains incomplete. Next, assemble the actual native qualification profile, retain visible
pending states for incomplete physical gaps, and expose explicit pinned CLI configuration. Then
prepare the authorized real-auth/provider-conformance and matched Leaf River packet. No real
auth cache, provider or Leaf River allowance was used. No source closure, frozen scientific gate,
global CLI/configuration, dependency environment, commit or push changed. Only a private wheel
target was installed. The original main checkout remains unchanged.

## Executed native qualification and independent upstream stop proof

The offline native producer now assembles a version 1.3 profile from actual local probes.
It binds the exact CLI, host source, OS/Python/TLS/public-trust runtime, policy and limits.
All nine check groups require a raw evidence index. The decoder verifies index bindings,
unique artifact paths, file hashes and size limits. Authored decoder fixtures remain separate
from executed native evidence. The reader does not independently establish an attestation's truth.

The new process-environment canary first exposed a policy gap. Restricting sysctl names alone
did not prevent reading the explicitly owned synthetic process's environment. The policy now
explicitly denies inspection of other processes, allows inspection of self and permits only
public hardware/OS sysctls. All nineteen permission observations then passed. No real process
environment, existing auth cache or credential was inspected by these probes.

Building the producer also found two fixture defects. An invalid Host header rejected the
slow-body request before its deadline, so that record correctly failed qualification. The
corrected probe requires the deadline event, HTTP 408, no upstream dispatch and verified endpoint
stop. A ctypes declaration treated shm_open's variadic mode as fixed on Apple ARM64, creating
unpredictable synthetic-object permissions. That caused intermittent unrestricted-control
failures. The corrected declaration passes the variadic mode explicitly, and a test requires
0600 permissions. Failed records and their original criteria remain intact.

The timeout fixture exposed a separate adapter defect. Returning from the upstream callback
did not prove that its command group stopped. Its original completion was uncertain, although
the independent watchdog later recorded a verified stop. The adapter now requires that stop
proof before releasing an invocation or reporting cancellation complete. Recovery records a
fresh proof against the fixed command, source, nonce, job and watchdog bindings. It preserves
the original completion and physical bytes. Group absence cannot manufacture successful
response bytes or provider usage. Unverified stop evidence leaves the invocation pending.

The final offline profile passed all nine groups with the explicitly selected installed Codex
0.155.1 executable under the strict package policy. The profile indexes 407 raw files totaling
549,995 bytes. Its model string is offline catalog metadata, not evidence that a real model ran.
A four-role scheduler run then verified this actual pin without a qualifier stub. Seven native
clients produced seven authored replies and two synthetic scientific attempts. All roles ran,
the controller accepted the synthetic candidate, and replay changed no saved tree bytes.
No provider call, real credential or Leaf River allowance was used.

The privately installed wheel passed 75 focused tests. Its initial end-to-end example failed
before host launch because the scientific runtime expects its registered source-checkout layout.
That limitation was not relaxed. Copying the installed wheel bytes and explicit synthetic source
bundle into that layout passed the same pinned four-role path. All 121 installed Python package
files match the worktree. This does not establish standalone installed scientific campaigns
without the source bundle.

Evidence root: `/private/tmp/part3-native-qualification-20261027/`.
Final qualification: `variadic-mode/qualification.json`.
Qualification pin: `6df622ddb30ea000eec78da41f5bf89540b6ee9134c31e8ee88d82994810e75a`.
Source four-role receipt: `pinned-four-role/receipt.json`.
Wheel-layout four-role receipt: `wheel-layout-four-role/receipt.json`.
Artifact comparison: `artifact-verification.json`.
Focused log: `/private/tmp/part3-native-qualification-focused-v2.log` (115 passed, 19.18 seconds).
Installed log: `/private/tmp/part3-native-qualification-installed-tests.log` (75 passed, 16.40 seconds).
Host source identity: `bb8d9a85acdf91fd37e22eb2d6882667a980d93623dd07b88d1de99f05cc7092`.
Wheel SHA-256: `1d80f2c49fdf6fe22d19717186451a31106670d2a2c66fcea3b4d26da806689e`.

Earlier unsuccessful producer runs are retained under `first`, `streamed`, `indexed`,
`public-sysctl`, `process-info`, `verified-stop`, `diagnosed-stop` and `complete`. These include
bounded scanner/index integration failures, the environment-policy gap, uncertain upstream
stop, invalid read-probe header and shared-memory control failures. None was relabeled.

The default suite passed 1,147 tests with 65 skips in 331.05 seconds. Its log is
`/private/tmp/part3-native-qualification-default-tests.log`. The final probe suite passed 44 tests
in 7.35 seconds, including two fixture-option tests added after default-suite collection. Its
log is `/private/tmp/part3-native-qualification-final-probe-tests.log`. Final documentation
contracts passed 19 tests in 0.62 seconds. Ruff and git diff --check passed. No Bayesian behavior
changed, so the optional Bayesian suite and frozen benchmark matrices were not run.
The source archive and hashes are `source-snapshot/` and `source-snapshot.json` under the evidence
root. `verification.json` records the outcome and remaining gates. Installed report/profile
replay also preserved the source-produced physical tree without a new host request.

Part 3 remains incomplete. The public CLI still refuses production dispatch. Explicit pinned
CLI configuration, unresolved physical gaps, real-auth/provider conformance and the separately
authorized matched Leaf River pilot remain. Native qualification grants no live allowance.
No scientific closure, frozen gate, global CLI/configuration, dependency environment, commit or
push changed. The original main checkout remains unchanged.

## Explicit pinned host configuration in the CLI

Validate, run and resume now accept an explicit `--host-config` TOML file for Codex subscription
runs. It contains only a schema version, native qualification root/digest, prepared credential
path and lease ID. The run specification selects the model and pins the same qualification.
The parser rejects unknown/duplicate fields, wrong types, unsupported versions, oversized files,
relative paths and symlinks. It checks private physical parents without opening the lease.
Credential paths must be outside the qualification, worker and scientific campaign directories.
There is no cache discovery, login, refresh, API-key fallback or endpoint/executable override.

The host validates selection and native time/output/workspace bounds before worker creation.
The scheduler applies the same limit checks for direct use of this adapter. Invalid configured
limits were rejected without changing the scientific campaign. A read-only validate constructs
no native client, opens no lease and makes no provider request.

A new typed HostConfigurationBinding is committed as the second hash-linked journal event,
before worker activity. It binds the normalized metadata digest and capability receipt, never
a credential hash. Resume requires the same binding even before the first invocation, and each
invocation must use those capabilities. Interrupted binding commits recover without duplicate
events. A run with only its creation receipt can finish the binding. Existing API activity with
no original binding is rejected rather than silently adopted. Historical unbound records remain
readable, and read-only reports expose the binding without requiring the host or campaign.

After the source changes, all nine native profile groups passed again with the explicit 0.155.1
binary. The new public CLI fixture used that actual pin without a qualifier stub, substituting
only authored upstream replies. Validate made no callback. Run started seven native clients over
four roles, completed two synthetic scientific attempts and retained the expected accepted
configuration. Resume changed no saved bytes and started no further work. No real model ran.

The native profile indexes 407 raw files totaling 546,058 bytes. The configured CLI and journal
focused suite passed 72 tests in 59.94 seconds, including binding commit faults, immutable resume,
lease-read exclusion, native limit preflight and abandonment. The default suite passed 1,166
tests with 65 skips in 338.19 seconds. Its log is
`/private/tmp/part3-configured-cli-default-tests.log`. Current documentation contracts passed
19 tests in 0.59 seconds. Ruff and git diff --check passed. No Bayesian behavior changed, so its
optional suite and the historical frozen benchmark matrices were not run.

The first plain installed-wheel CLI test selection failed nine tests before host launch because
the existing scientific registry requires its explicit source layout. The 12 passing tests and
all failures remain in the original log. Supplying wheel bytes plus the required synthetic source
bundle in a private checkout layout passed all 21 selected tests in 21.66 seconds, including CLI
child processes. That layout also passed the actual pinned native CLI fixture. This does not
qualify standalone installed scientific campaigns without their source bundle. All 122 installed
Python package files match the worktree. Installed read-only profile/report replay preserved the
source-produced physical tree and started no host or provider work.

The new [live execution design](../implementation-plans/part-3-live-conformance.md) proposes
concrete conformance and matched-study ceilings. It explicitly leaves the batch counter,
interruption runner, single-agent route, source-separated Leaf River preparation and comparison
driver unfinished. No approval is requested while that preparation is incomplete. A saved plan
does not authorize credential access or execution. The original seven-increment objective remains.

Evidence root: `/private/tmp/part3-configured-cli-20261027/`.
Qualification: `native/qualification.json`.
Qualification pin: `48c52049f1b9150b95d73d7a4700fa1b938dca5436336008a3dbbcc09bc7c1a5`.
Source CLI receipt: `native-cli/receipt.json`.
Installed CLI receipt: `wheel-native-cli/receipt.json`.
Installed replay/source comparison: `installed-receipt.json`.
Focused log: `/private/tmp/part3-configured-cli-focused.log`.
Initial installed log: `/private/tmp/part3-configured-cli-installed-tests.log`.
Source-layout installed log: `/private/tmp/part3-configured-cli-wheel-layout-tests.log`.
Host source identity: `cefada23ceff9e59e94e8e0c2a850032dc3b905b064c98d754df11af98b78536`.
Wheel SHA-256: `0394917f1a0bff2bcae4ac50613581a2491e254d57d59af2be09852e89ef7983`.
Source archive: `source-snapshot/` with hashes in `source-snapshot.json`.
Outcome and remaining gates: `verification.json`.

Part 3 remains incomplete. The next authorized work is the conformance/comparison preparation
and remaining requirement audit. No real authentication, provider or Leaf River allowance was
used. No scientific closure, frozen criterion, global configuration, dependency environment,
commit or push changed. The original main checkout remains unchanged.

## Shared batch accounting over native and scientific starts

The shared batch now has a strict BatchSpec, ordered case configuration digests, aggregate and
case ceilings, a caller-pinned private runtime manifest and an append-only hash-linked journal.
The manifest binds its creation time, source/environment identities, host selection, capabilities
and configuration digest. It grants no execution authority. Reopening without the caller's
pin permits inspection only. Source changes block mutation, while old evidence remains readable.

A case starts before work. Every physical host or scientific invocation gets a permanent
reservation before the trusted implementation runs. One operation lock spans physical work,
while short writer locks protect commits. Any unresolved reservation blocks all subsequent
starts and case completion. Failed cases stop the batch. Duplicate physical identities cannot
be relaunched under another reservation ID. Known usage/model/request-intent evidence cannot
be erased during reconciliation. Unknown usage remains unknown, and unknown transcript bytes
retain the original ceiling. Terminal observations are immutable and identical replay is a no-op.

BatchCodexHost extends the existing qualified adapter without a new provider. It freezes batch
and case identity into capabilities, validates case scope/configuration, reserves before launch
and clips native capture to the bytes still available. Reservations cover prompt, raw capture
and final text. The bound is not a quota over the whole native home or transport directory.
Recovery verifies the original invocation digest and original effective limits, then reads the
saved SDK result before reconciling the batch. Lost batch observation acknowledgments on either
side of commit did not cause another native or upstream call. Typed role validation and logical
task completion remain the scheduler's responsibility.

BatchCampaignController reserves before calling the original controller's physical execution
method. It does not change scientific criteria, interfaces or source closures. The observation
binds the original attempt/receipt, nonce and current group absence. Reopening the controller
with a larger invocation allowance could not reset the shared cap. Outer reservations are not
refunded by inner zero-cost classification. Observation loss recovered without another model
start or a change to the original attempt's physical files. Pre-attempt gaps without committed
proof remain pending. The initial science unit test used the wrong nonce field name and was
corrected to the original launch_nonce contract.

The first native batch unit run also exposed a real resource mismatch: the global transcript
budget must account for both raw capture and final text. The adapter now clips capture rather
than requiring a larger allowance. A final inspection found that a stale reservation timestamp
could bypass a deadline check. Mutating starts now check the current clock, and execute checks
again after the durable reservation commit. If commit delay exhausts the window, the callback
is not called and the original charge stays pending. Tests cover stale timestamps after reopen
and delay during commit. Observations may still reconcile stops after expiry, without new work.

The CLI adds batch-prepare and batch-status. Preparation creates a fresh runtime ledger and
starts its clock but executes nothing. The specification should be prepared for review first,
and a live runtime instantiated only after authorization. Read-only inspection imports no
native adapter or scientific controller. Malformed/corrupt evidence fails visibly. This API is
shared accounting, not the complete live conformance driver or a scientific outcome gate.

The final source state passed all nine native profile groups with the same explicit 0.155.1
binary and unchanged strict policy. A two-case fixture then completed eight native clients,
eight authored callbacks and two original synthetic scientific attempts under one batch.
It ran all four roles plus a direct structured text probe, charged 42,813 transcript bytes and
replayed batch/worker/scientific evidence without new physical work. Qualification was not
stubbed. All replies were authored, and no real credential or provider was used.

The new batch tests passed 27 cases in 12.94 seconds. The privately installed wheel passed the
same 27 tests in 14.37 seconds using the required explicit scientific source layout. That wheel
also passed the actual-profile two-case fixture. All 125 installed Python package files match
the worktree, and installed batch/worker report replay preserved the source-produced tree.
Standalone installed scientific campaigns without a source bundle remain unverified. The final
default suite passed 1,193 tests with 65 skips in 365.34 seconds. Its log is
`/private/tmp/part3-batch-final-default-tests.log`. Final documentation contracts passed 19 tests
in 0.79 seconds. Ruff and git diff --check passed. The optional Bayesian suite and historical
benchmark matrices were not run because no Bayesian behavior changed.

Evidence root: `/private/tmp/part3-batch-20261027/`.
Final qualification: `final-native/qualification.json`.
Qualification pin: `e485d696ca8def2422cde6022e44fe2e8991ff870b7fffb74957e13e920ed1e6`.
Source fixture: `final-fixture/receipt.json` and `final-fixture/batch-report.json`.
Source runtime batch pin: `1eb17a753f6cfd8faef988736e20cf93714963349280d91c27506076041483f4`.
Installed fixture: `wheel-fixture/receipt.json`.
Installed replay/source comparison: `installed-receipt.json`.
Focused log: `/private/tmp/part3-batch-final-focused.log`.
Installed log: `/private/tmp/part3-batch-installed-tests.log`.
Host source identity: `48c3062bd486b008764d601e701331e964e621ce82a47b338ea7ecbbd009159c`.
Wheel SHA-256: `dcf4c6b6a3d5a697e04bfadd3f2384fd716d4010a1dc676f5af9d76db262d198`.
Source archive: `source-snapshot/` with hashes in `source-snapshot.json`.
Outcome and remaining gates: `verification.json`.

The earlier native profile, source fixture, wheel and intermediate suite log remain under the
same root. They predate the final clock guard and do not qualify the final source. Their original
outcomes were not rewritten. The final source has separate qualification and fresh verification.

Part 3 remains incomplete. Next, prepare the conformance-specific manifests/case runner,
interruption and invalid-candidate cases, the single-agent route and matched comparison driver,
new source-separated Leaf River manifests and their offline dry run. Complete the requirement
audit before presenting the separate live-authorization request. No real authentication, provider
or new measured-data allowance was used. No scientific closure, frozen criterion, global config,
dependency environment, commit or push changed. The original main checkout remains unchanged.

## Conformance proposal capture before runtime creation

The new preparation captures a reviewable proposal without starting the batch clock. Its fixed
protocol binds six ordered cases, their criteria, native capabilities, host configuration and
aggregate allowances. The cases allocate thirteen host calls within the sixteen-call ceiling,
with two synthetic scientific starts and no measured-data work. The four-role case has seven
calls and no repair allowance. The malformed-handoff case allows one repair. Unallocated slots
do not create automatic retry authority.

The input worker is a template. Its original bytes are retained, and a distinct conformance-roles
worker gets the fixed proposed limits. Inspection verifies that derivation. It does not change
an existing run or silently expand its budget. The proposal includes the original scientific
YAML and only the known public scalar source/data closure. The source campaign must have no
committed events. Calibration, confirmation, relaxed acceptance, extra source paths and changed
data paths are rejected before capture. The expected public data are forcing 2 and prediction 3.

ConformancePreparation is a strict bounded record. The manifest is written last, and partial
or existing output directories cannot be reused. The future runtime needs a separate absent
private root. Its path, source/environment identities, protocol digest, templates and case budgets
are frozen before review. Preparation and inspection open no credential, create no worker/runtime
journal and perform no scientific evaluation. Native profile validation remains separate from
real model/account availability.

The CLI adds conformance-prepare and conformance-inspect. Inspection requires the original
manifest pin and checks every captured artifact, public scalar identity, original template and
fixed protocol. Optional host metadata rechecks the current profile/capabilities without opening
the lease. It reports execution_ready false and all six missing execution handlers. There is
no conformance dispatch command or approval request yet. A valid proposal is neither a passing
case nor a completed live driver. The first scope test expected an overlap error before its
missing-parent check, which was corrected. A criterion test used the wrong field name and was
corrected to minimum_gain. Their failure did not trigger execution or change a scientific gate.

The final source passed all nine native profile groups with the explicit installed 0.155.1
binary. Public preparation/inspection then passed with that actual pin and tripwires against
worker/scientific dispatch. It captured 82 input files totaling 1,423,987 bytes, preserved the
input campaign and proposal during inspection, and left the future runtime absent. No qualifier
stub or real credential was used. The installed wheel passed the same preparation fixture.
All 126 installed Python package files match the worktree, and direct installed inspection of
the source-produced proposal changed no bytes. Scientific fixture generation still requires
the documented explicit source layout. Standalone installed scientific execution is not claimed.

The final conformance tests passed 12 cases in 7.68 seconds. The installed conformance/CLI
selection passed 16 tests in 16.73 seconds. The default suite passed 1,205 tests with 65 skips
in 364.89 seconds. Final documentation contracts passed 19 tests in 0.78 seconds. Ruff and
git diff --check passed. No Bayesian behavior changed, so the optional Bayesian suite and
historical benchmark matrices were not run.

Evidence root: `/private/tmp/part3-conformance-20261027/`.
Native qualification: `native/qualification.json`.
Qualification pin: `8982e2e6ff99351fc6584bbdd59a47316928bf5c2d79b0f9dc2d73ece612f515`.
Source fixture: `source-preparation/receipt.json`.
Captured proposal: `source-preparation/proposal/conformance.json`.
Proposal pin: `6f46ce25cf710d99bd2e8ac2f9ab649ec3a22f83db3427b2d3ad160d0806e9a8`.
Installed fixture: `wheel-preparation/receipt.json`.
Installed replay/source comparison: `installed-receipt.json`.
Focused log: `/private/tmp/part3-conformance-final-focused-v2.log`.
Default log: `/private/tmp/part3-conformance-default-tests.log`.
Installed log: `/private/tmp/part3-conformance-installed-tests.log`.
Host source identity: `26667552af60498a39d4315f8c12633ea77b167e11b1ebab8ee8f41b19988b5e`.
Wheel SHA-256: `90bbea06b0976bd973322e2b925245265e21f10a4f8efb9f064759b74c746946`.
Source archive: `source-snapshot/` with hashes in `source-snapshot.json`.
Outcome and remaining gates: `verification.json`.

Part 3 remains incomplete. Implement the six conformance handlers and their recovery/adverse
cases, the single-agent route and matched comparison driver, then prepare new source-separated
Leaf River manifests and their offline dry run. Complete the requirement audit before requesting
separate live authority. No real authentication, provider or new measured-data allowance was
used. No scientific closure, frozen criterion, global config, dependency environment, commit or
push changed. The original main checkout remains unchanged.

## Text, roles, timeout and cancellation conformance handlers

ConformanceRuntime now executes the supported prefix of the frozen preparation through the
shared batch. Creation starts the declared runtime clock and binds its origin to the exact
preparation and batch digests. Reopening requires both original pins and unchanged configuration.
The driver has its own operation lock. Bounded advance limits cases for that invocation without
resetting global allowances. Unsupported cases stop as incomplete and live_conformance_complete
remains false. No public conformance dispatch command or live authorization request was added.

The text handler persists its exact task, framed prompt, nonce and limits before dispatch.
Recovery reads that same context and saved SDK output. Metadata without an original batch
reservation remains pending, rather than granting a free relaunch. The roles handler creates
the original synthetic controller from captured inputs and binds its worker configuration.
It requires seven completed invocations across four roles, two certain scientific starts and
the original accepted configuration/objective. Reopening cannot increase the shared scientific
cap. Lost case/batch verdict acknowledgments recovered without another physical call.

Successful native text is insufficient evidence for provider conformance. The handlers verify
the exact fixed subscription command, original scope/model/lease metadata, owned-command recovery,
request intent, HTTP 200 and response_received metadata. These checks open no credential or
make a new provider request. Copied provider metadata and direct native captures are hash-linked
case evidence. Missing/corrupt copies fail reporting. Finished role reporting also checks the
original worker journal and its recorded head. Resolved model identity must be observed, while
missing usage remains unknown. Positive unit tests explicitly stub provider proof and do not
establish real account or service validity.

The timeout handler uses a one-second execution window and requires a verified fixed-worker
request-intent stage plus stopped owned groups. Cancellation waits for that stage, durably
records its intent, and then requests cancellation through the existing ownership mechanism.
A completed response or an earlier failure cannot count as an exercised interruption. Recovery
does not start another monitor or request. Both handlers retain unknown usage/model identity
where absent, preserve possible request dispatch and leave remote computation stop unknown.
The batch, worker and scientific uncertainties remain separate.

Preparing for abandoned-call handling also exposed a batch accounting issue: the abandoned
adapter deliberately returns no reconstructed transcript and null elapsed time. Verified local
stop does not make those bytes known. BatchCodexHost now retains the transcript reservation
ceiling in that case. A regression test verifies that no zero-byte refund is inferred.

All four supported handlers completed in authored native/profile/provider unit fixtures, charging
ten host starts and two synthetic scientific attempts before stopping incomplete at owner_loss.
The unit proof stubs are explicit. Reopening/replay added no physical work. Raw capture and
provider-copy corruption tests failed visibly. The combined final focused suite passed 31 tests
in 65.41 seconds, including preparation and batch accounting checks.

The final source passed all nine native qualification groups again under the unchanged strict
policy with the explicit 0.155.1 binary. An actual pinned native text client then completed an
authored reply, but the unmodified provider gate rejected it because fixed-worker response proof
was absent. That failed runtime verdict stopped further cases, retained its one charged call,
started no scientific work and replayed unchanged. The fixture passed only because the intended
rejection occurred. No real credential or provider was used. The installed wheel reproduced
that rejection, and direct installed reporting preserved the source-produced failed verdict.
All 127 installed Python package files match the worktree. The scientific source-layout
requirement remains unchanged.

The installed focused suite passed 31 tests in 66.35 seconds. The final default suite passed
1,220 tests with 65 skips in 420.56 seconds. An earlier run collected before the final capture
checks encountered the expected host-source mismatch while code was being edited. That log is
retained and is not final verification. The fresh final suite began after the source was frozen.
Final documentation contracts passed 19 tests in 0.74 seconds. Ruff and git diff --check passed.
The optional Bayesian suite and frozen benchmark matrices were not run because no BO behavior
changed. No criterion was relaxed to obtain any of these results.

Evidence root: `/private/tmp/part3-handlers-20261027/`.
Final qualification: `final-native/qualification.json`.
Qualification pin: `a585ef0743f3762520a00e7afaed9cc1a6a523cb92f1d1f4fbed6c654eb52140`.
Source adverse fixture: `final-source-gate/provider-gate-receipt.json`.
Source runtime verdict: `final-source-gate/runtime-report.json` (failed, as intended).
Installed adverse fixture: `wheel-gate/provider-gate-receipt.json`.
Installed replay/source comparison: `installed-receipt.json`.
Focused log: `/private/tmp/part3-handlers-final-focused.log`.
Final default log: `/private/tmp/part3-handlers-final-default-tests.log`.
Installed log: `/private/tmp/part3-handlers-installed-tests.log`.
Intermediate source-mismatch log: `/private/tmp/part3-handlers-default-tests.log`.
Host source identity: `69e3cfa85ef51972733d2f7273b6535cc9ce7c46495f24c3ac88a45902703af9`.
Wheel SHA-256: `4b02c711d3050e2043089baa628ad1efb9c2fe85dce0001376705e33bc470363`.
Source archive: `source-snapshot/` with hashes in `source-snapshot.json`.
Outcome and remaining gates: `verification.json`.

Part 3 remains incomplete. Implement owner-loss and malformed-handoff handlers, finish the
public conformance execution/recovery path, implement the single-agent route and matched
comparison driver, and prepare the new Leaf River manifests/dry run. Complete the requirement
audit before asking for separate real-auth/provider and measured-data authority. No new
measured-data allowance, real authentication, provider request, scientific closure change,
global configuration, dependency environment, commit or push was used. The main checkout
remains unchanged and the original four development-plan lines remain intact.

## Malformed handoff and one-repair conformance handler

The fifth handler is implemented in `agents/conformance_runtime.py`. It creates a separate
`conformance-malformed` worker with two host calls, one task and one repair. The shared batch
ceilings still apply. It deliberately requests a specific invalid inner payload inside the
normal transport envelope. The normal scheduler saves the bytes and parse failure before
rejecting it. Only the intended rejection, fixed-worker response proof and an observed resolved
model permit the repair call. A transport failure, different invalid payload, valid first
handoff or missing proof stops without spending a repair. The repaired result must be a complete
typed stop handoff. No broker, artifact grant or scientific controller is attached to this case.
The verdict requires no scientific actions, receipts or batch starts.

Recovery reuses the original task, host reservations and worker journal. An invalid repair
stops after two calls across reopen. Lost verdict acknowledgments do not create another call.
Case reporting rechecks the malformed worker's artifacts and terminal journal head. A pending
malformed worker reports reconciliation required, including when its inner reservation was
saved before the shared native reservation could be committed.

Focused tests use an authored native executable/profile and explicit provider-proof stubs.
Seven new cases cover the intended rejection/repair, three unexercised rejection conditions,
two verdict acknowledgment faults and a failed repair across reopen. These tests do not
establish real provider behavior. Initial development tests exposed a missing physical-work
receipt when no scientific controller is attached and an incorrect reservation field name.
Those defects were corrected. A test fault hook was also narrowed to case completion so that
it tests the stated acknowledgment fault rather than an earlier native observation.

Fresh evidence is under `/private/tmp/part3-malformed-20261027/`:

- Host source: `97b8aefc9eb90640c9af409136c68d52532087ce1ebaffb15f833d6bc1547828`.
- `native/qualification.json` passed all nine groups with the explicitly selected installed
  0.155.1 CLI, including nineteen permission checks. Qualification pin:
  `262b822ebe4d960c17c48ea18bd209ae85462efe8d4a205871a65b306cf4d84a`.
- Source and installed-wheel `check_conformance_malformed_fixture` checks passed. Each starts
  two actual native clients with authored replies and provider-proof stubs, rejects the first
  payload, validates one repair and replays unchanged. The preceding case verdicts are explicitly
  authored zero-work markers. Those cases did not execute. The native qualification is real,
  while the replies, model metadata and provider proof do not establish any real model invocation.
- Wheel SHA-256: `d09fd3b49ddbb1f195e5af2c4c9fd64b1b52960f01e64c5e843e38d6736abe02`.
  All 127 installed Python files match the current worktree and explicit scientific source
  bundle. The bundle is still required for scientific fixture setup.
- Installed-wheel focused tests: **38 passed** in 76.67 seconds, logged at
  `/private/tmp/part3-malformed-installed-tests.log`.
- Direct installed-package report replay passed without modifying saved artifacts, loading
  credentials or starting work. The check uses Python's safe-path option to exclude unrelated
  modules in the working directory. An initial attempt from `/private/tmp` encountered an
  unrelated `inspect.py` shadowing the standard library. That file was left untouched.
- Default suite: **1,227 passed, 65 skipped** in 422.51 seconds, logged at
  `/private/tmp/part3-malformed-default.log`.
- Documentation checks: **19 passed** in 0.85 seconds. Ruff and `git diff --check` passed.
- The unmodified fixed-provider refusal check also passed under this source and native profile:
  one authored native text response produced the expected failed runtime verdict, retained its
  charge and replayed unchanged. No scientific work followed.
- `source-snapshot.json` and `source-snapshot/` preserve the current package, worker tests,
  example scripts, manifests and guides. `verification.json` binds the test and fixture results.

No real credential, provider request, measured-data or synthetic scientific start was used by
the new fixtures. Real host conformance remains not attempted. The normal driver still stops
before owner-loss. That handler, complete public conformance execution/recovery, the single-agent
route and matched comparison, new source-separated Leaf River manifests and offline dry run,
the full requirement audit and separately authorized live evidence remain. Part 3 is incomplete.
## Owner-loss handler and public conformance execution

All six conformance handlers are implemented. The new owner-loss case has a fixed interruption
point before the subscription worker's launch gate opens. Its criterion is part of the protocol
digest. Old preparations cannot silently adopt the new protocol or source. The case starts one
source-bound Python supervisor. That supervisor reserves one native invocation in the shared
batch, then holds the fixed subscription worker in its launch callback. It never opens the
credential or permits that worker to reach preflight. A readiness receipt binds the supervisor
PID/start/group, both worker identities, native nonce and pinned supervision job. The trusted
parent verifies that the supervisor is live in its owned group, records interruption intent,
and terminates only that group. Independent watchdogs stop the separate native/upstream groups.

Recovery verifies the original fixed subscription policy, command, request, ownership, source
and both stop proofs. It retires the original native invocation as host failure without a
replacement call. Native duration, resolved model, usage and observed transcript size remain
unknown. The original transcript ceiling stays charged. Known supervisor instrumentation time
is not substituted for native duration. Missing stop evidence remains pending, including when
it becomes available on a later resume. Saved metadata before supervisor launch never grants
a free launch on reopen. Native inputs, ownership receipts and available supervisor diagnostics
are copied into bounded case artifacts and verified on report reconstruction.

The public commands are `conformance-run`, `conformance-resume` and `conformance-status`.
Run requires the original preparation pin and explicit host configuration. Resume additionally
requires the runtime pin. Both use the preparation's fixed runtime root and preserve original
case order, start time and all allowances. `--max-new-cases` limits only that invocation. Status
reads the pinned runtime and verifies saved case/worker evidence without importing native or
scientific execution modules. It does not check current credentials or native qualification.
Exit 2 denotes invalid input, 3 pending reconciliation and 4 a failed case. Preparation now
reports implementation readiness, with authorization still explicitly not granted. The final
live-conformance flag requires all case proofs and rejects authored provider attestations.

Eight owner-loss tests cover real owned local groups with an authored executable/profile,
unknown accounting, immutable captures, both verdict acknowledgment faults, missing launch
state, changed metadata, an unavailable native stop observation followed by reconciliation,
and a genuine native failure before the intended interruption point.
Six CLI/classifier tests cover pin checks, fresh-root refusal, negative provider-gate replay,
read-only imports and refusal to label authored or partial proofs as live conformance.
An intermediate source contract suite passed **107 tests** in 101.73 seconds. Initial checks
passed 106 tests before the unavailable-observation test was added. Narrowing the acknowledgment
fault to CaseFinished exposed a test error: after a committed verdict, allowing one new case
correctly started the next case. The corrected test uses zero new cases to inspect that already
committed verdict. The diagnostic log is `/private/tmp/part3-owner-ack-diagnostic.log`.

A final review added two corrections. A conclusively failed and stopped native process before
readiness now closes as a failed, unexercised case, with its raw output retained. A completed
native process without an approved provider response still follows the existing pending
contract. The initial edge test incorrectly used that pending fixture to represent native
failure. It was changed to a genuine nonzero native exit. The review also exposed a batch
adapter contradiction when local stop was proven but response reconciliation remained pending.
The adapter now records local termination separately and retains the unresolved batch charge
and transcript ceiling. It does not turn that pending transport into success or failure.
The final edge suite passed **20 tests** in 28.31 seconds.

The CLI now emits the preparation/runtime pins and root to stderr before dispatch. This gives
an interrupted caller its original runtime pin before the final report. A new actual-native
CLI refusal fixture verifies run, startup receipt, expected failed verdict, resume and status.
Only its response is authored. The fixed-provider proof gate is unmodified. Source and installed
wheel fixtures passed, each with one native client, no provider and no science.

Fresh artifacts are under `/private/tmp/part3-owner-20261027/`:

- Host source: `affe49837e4614642086bdaea472d569bc8b7123308190e1e0f87ef77ce73011`.
- `final-native/qualification.json` passed all nine groups and nineteen permission checks with the
  explicitly selected installed 0.155.1 CLI. Pin:
  `9b2d1b179ab2517fdcacc45d728993e6e7d19105e45110f6a0b5cb151e67cfa8`.
- `final-source-owner/owner-fixture-receipt.json` and
  `final-installed-owner/owner-fixture-receipt.json` passed with the unmodified handler and fixed
  subscription command. Each starts one actual native client, interrupts before credential
  preflight, verifies stopped groups, retains unknown cost and replays CLI resume/status
  unchanged. Only preceding zero-work verdicts are authored. Those cases did not execute.
- Wheel SHA-256: `17f896914d38174d68495ada19186ec1197d43d9831e7939f9358623735fa366`.
  All 130 installed Python files match the worktree and explicit scientific source bundle.
  Scientific fixture setup still needs that source layout.
- Final edge tests: `/private/tmp/part3-owner-edge-tests.log`.
- Installed contracts: **114 passed** in 127.43 seconds, logged at
  `/private/tmp/part3-owner-frozen-installed-tests.log`.
- `final-source-cli/cli-provider-gate-receipt.json` and the installed counterpart preserve
  the expected provider refusal and original startup receipt.
- Direct final installed-package status replay passed without physical implementation imports,
  credential access, new work or changes to saved artifacts: `final-installed-receipt.json`.
- The intermediate 1,240-pass/65-skip suite and its source snapshot remain under `intermediate/`.
  It predates the two final edge fixes and startup receipt. Its wheel/profile and original
  source/installed fixtures remain in the earlier sibling directories.
- Final default suite: **1,242 passed, 65 skipped** in 489.76 seconds, logged at
  `/private/tmp/part3-owner-frozen-default.log`.
- Documentation checks: **19 passed** in 0.58 seconds. Ruff and `git diff --check` passed.
- `source-snapshot/` and `source-snapshot.json` preserve the final source and hashes.
  `verification.json` binds the final tests, profile, wheel and fixture receipts.

This qualifies local owner interruption before preflight only. No real credential, provider
request or Leaf River pilot was used. The new owner fixtures start no science. Model availability
and real-cache compatibility remain unproven. Real-provider text, role, timeout, cancellation
and malformed cases remain not attempted. The single-agent route, matched comparison driver,
new source-separated Leaf River manifests/dry run, full requirement audit and separately
authorized live evidence remain. Part 3 is incomplete. No commit or push was made.

The live-comparison design now explicitly permits offline preparation, validation and dry-run
work before live authority is requested. Live matched execution still requires passing host
conformance and separate authorization. This removes a circular preparation gate without
changing scientific criteria or granting any execution allowance.
## Single-agent supplied comparator

The supplied-only single-agent route is implemented under the
[single-agent design](../implementation-plans/part-3-single-agent.md). Run schema 1.1 requires
an explicit `single_agent` route, one template and a separate policy digest. Its task/grant
schema is 1.1 and its handoff schema is 1.2. Legacy schema 1.0 run serialization stays unchanged
and rejects an explicit route field. Four-role prompts, policy, fresh reviewer context and
journal contracts remain. Route/version mixing and generated source are rejected.

The same trusted broker transitions, controller, supplied catalogue, scientific rules and
request envelopes serve both routes. One persona proposes, configures, reviews its own work
and freezes. It makes no orchestrator calls and cannot delegate. Review is explicitly reported
as self-review. Executed checks still determine scientific eligibility. A blocking self-review
stays blocked until a trusted caller records its disposition. Candidate allowances are checked
before staging, including when an untried candidate remains after the allowance is exhausted.

The persona receives the approved scientific summary and at most four whole previous normalized
own handoffs, bounded to 8 KiB. Included and omitted invocation IDs are recorded. Raw transcripts,
private labels and candidate workspaces are excluded. Old IDs mentioned in history do not become
artifact capabilities. The full journal preserves every original output and failure. The existing
validate/run/resume/report commands select the frozen route. Status retains its compact summary.

Four calls complete the one-candidate synthetic route, versus seven calls for four roles. Both
make two numerical executions and reach the same scientific decision and configuration. These
are scripted comparisons of implementation behavior, not the frozen matched study required by
the original plan. The route has not run a real model or used Leaf River data.

Fourteen new tests cover versioned records, legacy serialization, one-persona counts, scientific
parity, bounded whole-item history, private raw output exclusion, exact grants, stage errors,
candidate limits, invalid candidates, repair exhaustion across restart, blocking self-review,
trusted dispositions, raw/completed handoff acknowledgment recovery and CLI replay. The final
combined source checks passed **89 tests** in 106.87 seconds. Existing four-role contract,
scheduler and broker tests also passed before the final combined run. The full suite passed
**1,256 tests with 65 skips** in 513.91 seconds. Ruff and `git diff --check` passed.

Fresh evidence is under `/private/tmp/part3-single-20261027/`:

- Host source: `1d103436951b57028c5e114aee18dc7e67b209b23726f535e3783f76fdbc53a6`.
- Native qualification passed all nine groups and nineteen permission checks using the explicitly
  selected installed 0.155.1 binary. Pin:
  `6a0eecbde22bb897ae7d92398783a4bb5c33df5ff460d14b1f9168b7f1bcbb18`.
- `final-source-fixture/single-agent-fixture-receipt.json` and
  `final-installed-fixture/single-agent-fixture-receipt.json` passed. Each uses four actual native
  clients, authored responses and two synthetic executions. CLI resume, compact status and full
  report preserve the evidence without another host/scientific start. Qualification is real,
  but streamed model names and usage are authored fixture metadata. No credential/provider is used.
- Wheel SHA-256: `8897777d10d2b013d2f8f94092dde0bc5793670cf9a02b45d1abe86ea255b0f8`.
  All 131 installed Python files and the prompt bytes match the worktree. Scientific example
  setup still needs the explicit source layout. Installed focused tests: **89 passed** in
  109.97 seconds, logged at `/private/tmp/part3-single-installed-tests.log`.
- A normal installed-package read-only report reproduced the source fixture unchanged without
  importing the single-agent broker, native host, scientific controller or host SDKs:
  `installed-receipt.json`.
- Source contract log: `/private/tmp/part3-single-final-contracts.log`.
  Default log: `/private/tmp/part3-single-default.log`.

The initial native example harness attempted to replace its already written scripted run file
through the immutable writer. It failed before native/scientific execution. The corrected
harness retains the template and writes `native-agent-run.json` separately. The next harness
version completed both workflows correctly but incorrectly compared compact status with the
full report, producing failed fixture verdicts. It now checks the documented status projection
and compares full report separately. The incomplete roots, failed receipts, underlying completed
journals and logs are retained. Scientific criteria, controller decisions and old evidence were
not changed. Final positive fixtures use separate roots. The initial unit route-mixing check
also omitted the required journal writer lock; correcting that test exercised the intended
route rejection without changing the store contract.

The documented module example passed end to end with one persona, four scripted calls and two
synthetic executions. Final documentation checks passed 19 tests. Source snapshot hashes and
`verification.json` preserve the final evidence. No real authentication, provider, measured-data pilot, dependency
installation in the project environment, global configuration, commit or push was used.
Part 3 remains incomplete. Implement the matched comparison driver, prepare fresh source-separated
Leaf River manifests and an offline dry run, complete the original requirement audit, and obtain
separate authorization before real-provider conformance and measured-data evidence. The original
scientific criteria and 2020 exposure/confirmation limits remain unchanged.

The next contract audit must also address model-visible output instructions. The current
scheduler supplies the task's schema name and the native transport enforces its outer string
envelope. It does not yet supply the complete inner handoff field/type contract in the prompt.
Authored reply constructors know those fields from Python and cannot prove that an unassisted
model will emit them correctly. Add that contract exposure before live conformance. This finding
adds no model authority and does not change the strict parser or any scientific rule.

## Model-visible output contract and preparation deadline

The scheduler now includes the complete inner handoff structure in every model prompt. The
new `agents/output_contract.py` derives fields, required values, nested records and types from
the authoritative dataclasses. It binds task, invocation, role, schema version, revision, exact
grants, allowed actions, supplied implementation choices and current candidate/evaluation IDs.
It covers the original four roles, the single persona, generated source drafts and the older
implementation-bundle record. Unknown annotation types fail explicitly instead of producing
an incomplete contract. The document has a 32 KiB bound and consumes the existing prompt
allowance. It grants no access or scientific authority.

This is instructional JSON Schema. It is not a second runtime acceptance engine or a claim
that every semantic rule can be expressed by this schema. Strict record parsing, exact grant
checks, phase checks, source admission and the scientific controller remain authoritative.
The native outer `handoff_json` string envelope remains separate. Authored native responses
still cannot establish real-model usability.

The exact prompt is persisted before dispatch. The scheduler now rechecks the task and run
deadlines after prompt preparation, immediately before creating the invocation reservation.
Preparation cannot extend the worker timeout. Tests advance the clock during contract
construction to verify a shortened timeout or no invocation when the deadline expires.

Twenty-six new tests cover independently written JSON replies for every output variant,
nested required fields, extra keys, identity types, ungranted citations, wrong implementations,
action/output association, single-persona delegation denial, generated-source restrictions,
empty grants, contract size, prompt durability and preparation deadlines. A test-only schema
interpreter checks the emitted subset. No schema-validation dependency was installed.

Source focused checks passed **123 tests** in 147.31 seconds. The full suite passed
**1,282 tests with 65 skips** in 495.49 seconds. Documentation checks passed **19 tests**.
Ruff passed. Final evidence is under `/private/tmp/part3-output-contract-20261027/`:

- Host source: `83a83f1849f83072ad09b4d275942079b28da52eb295abf39275057a7898cedb`.
- Native qualification passed all nine groups and nineteen permission checks using the
  explicitly selected installed 0.155.1 binary. Qualification pin:
  `930c439fee16a72c5a5548522eefc83a2788f7d40987ee545d030bb19645d1ae`.
- Source native fixtures passed for both routes: four single-persona calls and seven four-role
  calls, each with two synthetic scientific executions, unchanged replay, authored streams,
  no real credentials and zero provider calls. The installed single-persona fixture also passed.
- Wheel SHA-256: `87239b095ed4f45c666c05f88a321a54bcfd02d0505b4b635196e088b30097ff`.
  All 132 installed Python files and five prompts match the worktree. Scientific example tests
  use an explicit source layout containing those installed package bytes.
- A direct installed-package read-only report reproduced the source report unchanged without
  importing a host, scientific controller, single-persona broker or output-contract generator.
- Source logs: `/private/tmp/part3-output-contract-final-contracts.log` and
  `/private/tmp/part3-output-contract-default.log`.

The first installed focused test invocation ran inside the restricted tool sandbox, which
forbids `/bin/ps`. Seventeen tests failed and seventeen setup checks errored because scientific
process ownership inspection could not run. The controller retained uncertain reservations
instead of claiming success. The failed log and journals remain. The same tests are rerun
with authorized local process inspection, without weakening the supervisor or changing code.
That installed rerun passed **123 tests** in 153.40 seconds. Its log is
`/private/tmp/part3-output-contract-installed-authorized-tests.log`. The initial restricted
log is `/private/tmp/part3-output-contract-installed-tests.log`, and the captured restriction
is `sandbox-process-inspection.json` in the evidence root. Final documentation checks again
passed 19 tests, and `git diff --check` passed. `verification.json`, the source snapshot and
the final documentation hashes bind these results. The main checkout remains clean, and the
original four-line addition to `docs/development-plan.md` is unchanged.

Part 3 remains incomplete. The matched comparison driver, fresh source-separated Leaf River
manifests, offline comparison dry run and complete original requirement audit remain. Real
provider conformance and measured Leaf River execution were not attempted. This increment
changes no scientific criterion, old manifest, benchmark evidence, project dependency,
credential state or global configuration. Nothing was committed or pushed.

## Fresh matched Leaf River preparation

`examples/agent_campaign/prepare_leafriver.py` now prepares the three scientific campaigns
required by the matched comparison: scripted, single persona and four roles. It verifies the
checked Part 2 campaign template by SHA-256 before deriving new profiles. Data, daily port
contracts, parameter bounds, fitting policy, seeds, acceptance tolerances, checks, candidate
pool and exposure remain unchanged. New campaign names, an explicit scientific source closure
and a reduced execution ceiling produce fresh identities without rewriting the old profile.
The scientific source list contains the supplied hydrology modules and the shipped version 1
closure. Host modules and role prompts are excluded. The preparation recipe is retained
separately from the scientific inputs.

The builder audits the cached 2019/2020 data and compares the original saved NPZ forcing and
labels with their 2019 splits. It captures the cache audit sources and binds them through the
historical template and original cache provenance. Inspection checks every captured artifact,
all three specifications, exact scientific identities and the complete fixed audit. Changed
metadata, repinned relaxed science, repinned historical data, invented split counts, missing
inputs and symlinks fail validation. Added unrelated host files do not affect scientific
identity. Preparation requires an absent output under a private parent and writes its manifest
last. It initializes no campaign, worker, host, execution clock or credential lease.

The static complete-pool allocation matches the current controller and child-study code:

| Work | Maximum physical executions |
| --- | --- |
| Existing Hamon baseline default | 1 |
| Hamon child fitting and fresh comparison | 16 + 1 |
| Hargreaves additional default, fitting and fresh comparison | 1 + 16 + 1 |
| One causality replay for each selected comparison | 2 |
| Each route / three routes | 38 / 114 |

These are ceilings for the complete pool when both fitting studies select feasible
configurations. Early stops, rejection or failed fitting may use less. No physical execution
is claimed. The matched driver must still enforce aggregate reservations and verify actual
accounting. The preparation records the proposed equal live-route limits and aggregate 40 host
calls but starts no batch clock and grants no dispatch authority. It explicitly reports
`execution_ready: false` and the missing matched driver.

Seventeen new checks cover the preparation and adverse cases. Together with the existing
scientific-source identity checks, **29 tests passed** in 13.97 seconds. The installed package
plus explicit scientific source bundle passed the same **29 tests** in 13.72 seconds. A
preparation test forbids subprocess launch, campaign creation and hydrology adapter preparation
or execution. The source and installed module commands produced identical bytes for all
**100 artifacts**, including **93 captured inputs**. Read-only inspection preserved them.
Documentation checks passed **19 tests**. Ruff and `git diff --check` passed.

Evidence is under `/private/tmp/part3-matched-leaf-20261027/`:

- Final source and installed preparations: `final/` and `installed-final/`.
- Preparation pin:
  `f054946aea8f072579350909c5307f313e253be27b40c5e00f6f436b5dc25934`.
- Scripted scientific identity:
  `554ccd3a4bf70f4850bf9dc0ade32663ba5ceaca3ec417d702e105d8c982327a`.
- Single-persona scientific identity:
  `b6b78b4b25d0f7bc21e552b9f1e8f9b704dd3116a85a67b5427db7b82ecfae66`.
- Four-role scientific identity:
  `b52fbc128213c085a264d40b81d92027e6724bf857d1d200af033c3a3ac37d4a`.
- `parity-receipt.json`, `prepared-artifact-sha256.json`, `source-identities.json` and
  `installed-package-bytes.json` preserve the checks and hashes. The unchanged package bytes
  match the previously verified wheel, SHA-256
  `87239b095ed4f45c666c05f88a321a54bcfd02d0505b4b635196e088b30097ff`.
- Focused logs: `/private/tmp/part3-matched-leaf-focused.log` and
  `/private/tmp/part3-matched-leaf-installed-tests.log`.

An early manual command correctly rejected the nonprivate temporary parent. A subsequent
implementation smoke exposed an omitted required artifact media type and stopped before any
output writes. That argument error was fixed. A private source-bundle copy also needed
`dirs_exist_ok` when filling an existing copied example directory. Neither failure launched
work or changed scientific evidence. The first 13 preparation checks passed before the final
historical-data and exact-audit validation checks were added.

The checked template still has SHA-256
`f2c35df440ea5b622e1da2d568c4db78d806ca5c120cca5a28267401555f0766`.
The host source remains
`83a83f1849f83072ad09b4d275942079b28da52eb295abf39275057a7898cedb`.
No host/package source changed in this increment, so the prior offline native qualification
was not rerun. No credential, provider, measured model execution, scientific benchmark matrix,
new dependency, global configuration, commit or push was used. Independent measured-data
confirmation remains `confirmation_not_attempted`. The implementation design now records the
remaining matched driver, synthetic dry run, complete original requirement audit and separate
live authorization. Part 3 remains incomplete.

Final default verification passed **1,299 tests with 65 skips** in 508.95 seconds, logged at
`/private/tmp/part3-matched-leaf-default.log`. The command used the main checkout's Python
3.12 environment, explicit worktree `PYTHONPATH` and local process inspection. No source code
changed during that run. The main checkout remains clean, and the original four-line addition
to `docs/development-plan.md` is unchanged. The evidence root's `verification.json`, copied
logs, prepared artifact hashes and final changed-file snapshot record this increment.

## Authored three-route comparison driver

`examples/agent_campaign/comparison.py` and `synthetic_comparison.py` implement the serial
three-route synthetic driver over the existing broker, worker journal and batch scientific
controller. Inputs are fabricated deterministic weather and labels for 2001 at a synthetic
basin. The supplied Hamon/Hargreaves equations, parameter bounds, sixteen-call Sobol fitting,
seed 17, scientific checks and common thresholds remain shared. No measured arrays are used
for numerical execution. Source capture retains the original template/graph and parent Leaf
preparation separately, with three driver-source hashes and the package/runtime identities.

The driver fixes candidate IDs and order for both role routes. Early freeze is rejected while
candidates remain, and an explicit stop is preserved without inventing a repair. The same
captured static control runs for each route: a valid snapshot passes, then changing only the
first output's units fails the actual admission validator with
`candidate topology/interface differs`. It creates no proposal, numerical start or worker
feedback. Its bytes and result are private operator evidence. This is a trusted negative
control, not a claim that an LLM generated a bad candidate or completed an admission request.

Runtime creation starts one immutable shared clock. A separate driver lease prevents competing
execution, while scientific starts retain permanent batch reservations. Case and numerical
pause flags do not change the original caps. Recovery reuses completed handoffs and scientific
receipts. Pending workers remain visible and block another call. Verdicts bind both journal
heads, full worker reports, comparison/diagnostic evaluations, selection, calls, repairs,
recorded trusted dispositions and case wall time including pauses. Reports reread the saved
negative-control receipt and input blob. The CLI distinguishes newly charged work from
cumulative totals and already recorded verdicts.

Final default verification passed **1,320 tests with 65 skips** in **920.15 seconds**. This
includes all **21 new driver tests**, the complete three-route numerical run, a pause/resume,
committed-handoff acknowledgment loss, order/identity/early-freeze repairs, explicit stops,
competing drivers, pending workers, changed pins/inputs/limits, and corrupted copies of the
completed matrix. All three routes selected the same scientific configuration/objective and
each used **38 physical synthetic starts**, **114 total**. Authored logical calls were
**13 scripted, 7 single-persona and 13 four-role**. Completed replay added no starts or calls.
No practical role advantage or real-model usability follows from this result.

The final installed package plus explicit source bundle passed **20 tests with one deliberate
deselection** in **74.17 seconds**. The full numerical matrix was not repeated there. Its
read-only CLI reconstructed the archived source matrix exactly while array loading, fake-host
invocation and scientific execution were forbidden. Package bytes still match the previously
verified wheel: all 132 Python files and five prompts are unchanged. Current host source
remains `83a83f1849f83072ad09b4d275942079b28da52eb295abf39275057a7898cedb`.
No native qualification rerun was needed for these separately captured example sources.

Evidence is under `/private/tmp/part3-matched-driver-20261027/`:

- `matrix-readonly-copy/`, `matrix-preparation-copy/`, `matrix-report.json` and
  `matrix-archive-receipt.json` preserve the completed final-source matrix. The copies are for
  read-only audit, not relocated executable runtimes. Runtime pin:
  `f1a5a80e5ddff4549e999d2e5f2674f6311be18593edaaa58ba1109cea3e1238`.
- Its source preparation pin is
  `273d5eb81fbd6a5f264c68fcd5f7ade1885926ff99b9c874fe13e5c7720a0921`.
  Driver SHA-256:
  `f830306a53b0646b511052d331910dd3ee3403286415ba4911df8b03a86b99d0`.
- `final-report/` is a separately prepared proposal for review with no runtime started.
  Its pin is `f1566cc4ae012bd14971b091821628384f6aff152447c20cdc76514cbecd4040`.
  Runtime location participates in that preparation identity, so this differs from the test pin.
- `installed-package-bytes.json`, `installed-matrix-report.json` and
  `installed-report-receipt.json` record installed-byte and read-only report checks.
- The earlier CLI numerical-pause smoke recorded one synthetic start and four authored calls,
  with startup and delta receipts. It remains an incomplete paused fixture, not a completed
  comparison. Its source predates the final report-integrity fix and cannot silently resume
  with changed driver bytes.
- Full log: `/private/tmp/part3-matched-driver-final-default.log`.
  Installed log: `/private/tmp/part3-matched-driver-final-installed-tests.log`.

The first manual run stopped before any scientific or worker start because the static-control
artifact parent directory was missing. That initialization was fixed. An initial sixteen-test
run then passed, including the three-route matrix. Further checks found an explicit-stop
validation error and incomplete pending-worker reporting; both were corrected and tested.
One subsequent test expected different error wording from the correct unresolved-stop message.
That assertion was corrected without changing runtime behavior for that failure.

Review then found that completed reports did not reread the saved negative-control blob.
The owned default test process was interrupted with SIGINT after its log writer, exact command,
working directory and start identity were checked. That incomplete run ended with 168 passed,
five skips and exit 2. It is not acceptance evidence. The artifact checks and corruption tests
were added before the final passing run. The interrupted log remains. Its temporary test root
was later removed by ordinary pytest retention, as recorded in `interrupted-fixture-audit.json`.
No experiment ledger was reset or relabeled. `retained-failure-audit.json` distinguishes these
cases. The completed final matrix was copied before test retention could remove it.

The [acceptance inventory](part-3-completion-audit.md) now maps the original increments and
remaining evidence. The synthetic driver deliberately has no real-host option. Native matched
preparation/dispatch, real-provider conformance binding, native interruption within the original
matched allowances, a lightweight comparison status entry point, final nested-contract/boundary
verification and authorized Leaf River evidence remain. Source/installed fake responses and
acknowledgment recovery do not satisfy those gates. No credential was opened, provider called,
measured model executed, dependency installed, global configuration changed, commit made or
push attempted. Part 3 remains incomplete.

## Bounded comparison inputs and status without execution imports

The comparison CLI is now a light facade. Execution lives in `comparison_runtime.py`, and
`comparison_status.py` reconstructs reports without a host, broker, scheduler, scientific
controller or supplied model import. Existing Python entry points remain available through
lazy exports and a reader wrapper. The same CLI status command reads both version 1.0 and
version 1.1 origins. A new preparation uses `synthetic-matched-comparison-1.1` and binds all
five driver sources. Old preparations and journals are preserved; execution does not silently
adopt changed source bytes. Reading the archived version 1.0 matrix produced the exact prior
report without new work or execution imports.

Synthetic verification now calls the core `read_arrays` before checking expected values.
The protocol freezes a five-member limit, 64 KiB compressed, 4 KiB for each uncompressed member
and 32 KiB total. Core checks verify digests, confinement, safe member names, NPY headers,
object-array exclusion and declared sizes before NumPy allocation. The example additionally
requires real numeric types. Ten new regressions exercise object arrays, oversized compressed
and uncompressed input, excess members, unsafe names, truncated archives, complex values,
malicious repinning before runtime creation, foreign origins and fresh-process import isolation.
The numerical engine, generated boundary and scientific model equations are unchanged.

The combined source focused run passed **30 tests with one deliberate deselection** in
89.13 seconds. The installed package plus explicit source bundle passed the same **30 tests**
in 93.35 seconds. The final default suite passed **1,330 tests with 65 skips** in **935.68 seconds**.
It includes the complete version 1.1 three-route synthetic run, 114 scientific starts, identical
scientific selection, 13/7/13 authored calls, pause/recovery, unchanged replay and corrupt-evidence
rejection. Source and installed read-only commands reconstructed the new archived matrix without
execution imports. Documentation checks passed 19 tests. Ruff and `git diff --check` passed.

Evidence is under `/private/tmp/part3-comparison-readers-20261027/`:

- `matrix-readonly-copy/` and `matrix-preparation-copy/` preserve the completed source run for
  read-only audit. They are not relocated executable runtimes. `matrix-report.json` and
  `matrix-receipt.json` record its pins and all five source hashes.
- Runtime pin: `da9545000495b6250ed64e467294c56dab55506c5663f05b448b921f094b0acc`.
  Preparation pin: `41ac6b25d9dd6cc95bd506dbd302605a1a76718c7a118d814859a93e6adac56a`.
- `legacy-report.json` records exact compatibility with the prior version 1.0 matrix.
  `installed-report.json` records version 1.1 report parity and absent execution imports.
- `installed-byte-receipt.json` verifies that the unchanged 132 package Python files and five
  prompts match the prior installed wheel. No new package build or installation was required.
- Logs: `/private/tmp/part3-comparison-readers-focused.log`,
  `/private/tmp/part3-comparison-readers-installed.log`, and
  `/private/tmp/part3-comparison-readers-default.log`.
- `default-process.json` records the owned verification process before it exec'd pytest.
  That session completed with exit zero. Source/archive hashes and `verification.json` retain
  the final evidence.

An initial mechanical extraction renamed parts of the JSON helper names. Ruff caught those
undefined names before execution, and they were corrected. The first focused compatibility
run then found that import cleanup had removed the public reader alias. An explicit wrapper
restored the API, after which the combined source, installed and full runs passed. The initial
failed log is retained. No scientific criterion or old result was changed for either correction.

The acceptance inventory also records a separate source-audit finding: ordinary
`SingleAgentBroker._role` rejects a typed `NextStep stop` where its control branch admits only
an investigator freeze. The matched proposal override already handles stop, but it does not
prove the ordinary route or later stages. Fix and test this before final host qualification
and native comparison integration. Native preparation/dispatch, conformance/account binding,
interruption inside matched ceilings, remaining contract/boundary audit and separately
authorized real-provider/Leaf River evidence still remain. Part 3 is incomplete. No credential,
provider request, measured numerical run, new dependency, global configuration, commit or push
was used in this increment. Host source remains
`83a83f1849f83072ad09b4d275942079b28da52eb295abf39275057a7898cedb`.

## Native comparison preparation and corrected stop audit

The ordinary single-agent stop finding was incorrect. `CampaignBroker._role` preserves a valid
stop before calling the phase-specific validator. Four new tests cover proposal, configuration,
review and final freeze. Each stop is saved as a completed typed handoff, consumes no repair,
starts no additional scientific work and replays after reopening without another call. No
broker or policy change was needed. The existing runtime source identity and qualification
therefore remain unchanged.

`examples/agent_campaign/native_comparison.py` now captures the native comparison proposal.
It verifies and copies the frozen Leaf and conformance preparations, the original four-role
worker template, selected host/configuration and its own recipe. Derived workers retain the
same scientific identities, supplied pool and limits. The scripted baseline has no physical
host allowance, while the two live cases have twenty each. Each case has 38 scientific starts,
114 in total. No measured model, credential lease or execution clock is touched by capture.

Inspection reconstructs the exact derived workers and shared batch specification and checks
both child preparations and all source/profile/configuration bindings. The prerequisite reader
requires a caller-pinned completed real-provider conformance runtime from that exact captured
preparation and batch specification. An authored or incomplete report cannot satisfy it. Unit
coverage includes an explicitly stubbed positive report and mismatched preparation/specification
cases; these stubs are not real-provider evidence. The native runner, interruption, per-call
provider checks and native report still need implementation. Preparation and prerequisite checks
both leave `execution_ready: false` and grant no execution authority.

The first ten-test run found nonprivate intermediate directories in the captured conformance
tree. Python's recursive mkdir had created intermediate parents with the default mode, although
the enclosing proposal was private. The verifier rejected the tree. The writer now creates and
checks every parent with mode 0700. A regression checks all capture-directory modes. An initial
fixture import alias also needed the explicit pytest re-export convention for Ruff; that changed
no runtime behavior. The corrected native preparation tests passed ten cases before additional
prerequisite-binding cases were added.

Combined focused verification passed **31 tests** in 119.49 seconds. The installed package plus
explicit example source bundle passed the same **31 tests** in 124.92 seconds. These tests
forbid dispatch, runtime creation and lease reads during preparation. The existing package's
132 Python files still match the verified installed wheel; no package source was modified.
A genuine pinned-native-profile conformance preparation also passed without a worker/model
start. Source and installed native proposals derived identical case/batch records and captured
recipes. Their different future runtime roots produce deliberately different preparation pins.

Evidence is under `/private/tmp/part3-native-comparison-20261027/`:

- `conformance/receipt.json` uses the real, previously qualified native profile, without a stub.
  Qualification pin: `930c439fee16a72c5a5548522eefc83a2788f7d40987ee545d030bb19645d1ae`.
  Requested model metadata does not establish model availability.
- `source-proposal/` and `source-cli-output.json` record the native proposal. Pin:
  `18de15ccfe605ab30ba331017d2339f970436a4c7fe28ff10885a2a0d07abf10`.
- `installed-proposal/` and `installed-genuine-receipt.json` record installed parity. Pin:
  `d87c01f97472f4b04854094dea8b5449d7b3200af8b00e2e46342253d3ccd734`.
- No source, installed or conformance runtime directory was created, and the placeholder lease
  file does not exist. These are prepared inputs, not completed studies.
- `/private/tmp/part3-single-stop.log` records the four phase/replay tests.
  `/private/tmp/part3-native-preparation-initial.log` retains the initial private-directory
  failure. Combined logs are `/private/tmp/part3-native-comparison-focused.log` and
  `/private/tmp/part3-native-comparison-installed.log`.

Read-only generated-boundary auditing also checked the latest saved qualification without
rerunning its probes. The current source/platform verifier accepted
`/private/tmp/part3-interface-boundary-mz2h782u/qualification`, pin
`42e918316fd97d113c4216af6a6c01f7b38dc9ac048a9e5cc9dedb2a25d0b5ed`, with boundary identity
`c4bba04d7b191a31ae4ba4a4d0396c790abba0216d43c4acfcc463f021fa5e86`. Current local Docker
context, image, client and server metadata match the saved runtime. The earlier receipt was
correctly rejected as stale. JSON audit receipts preserve both outcomes. No container, image
download, generated implementation or scientific execution was started by these audits.

The remaining nested bundle/review audit added thirteen tests in
`tests/test_agent_nested_contracts.py`. They mutate every input artifact metadata mapping,
source/interface collection, review finding/check/evidence collection and exported dictionary.
The saved records stay unchanged and nested fields remain frozen. Additional cases reject
invented nested authority fields, out-of-scope evidence, unresolved recommendations, duplicate
findings and oversized nested payloads. Source checks passed thirteen tests in 0.62 seconds;
installed checks passed thirteen in 0.60 seconds. These were collected after the running full
suite began, so they are separate evidence, not part of that suite's total. The first focused
run had one assertion mismatch: optional artifact fields report the union's invalid-value error
rather than the inner unknown-field error. Rejection already worked. The assertion now accepts
both parser contexts. No package runtime code changed.

Read-only admission verification rejected the two earlier registration pins as stale. Comparing
all 89 execution-closure files against the final handoff fixture reproduces its old identity
exactly. Only `cli.py` differs. The current execution identity is
`0395e8237a0c6406c26d1a77a62ec3db869bdf1c89f5ca15b6e0a697db4d1802`.
This difference is retained rather than removing the CLI from the frozen closure or repinning
an old admission. Current-source registration qualification remains pending.

The historical handoff's portable interface packet independently reconstructs under the current
runner and boundary, with two passing public checks and receipt
`2150fa5f7e2c64879ccce13a8898784b1d593c216d11feb9b238b253d43e74cd`.
This verifies historical interface evidence, not current registration acceptance. The first
read-only guard also blocked Python's standard-library `uname` metadata query. Reading platform
metadata before installing the no-process guard allowed reconstruction without any container or
scientific launch. Audit receipts and the exact source difference are retained under the same
evidence root. No new registration, trusted approval or execution authority was created.

Final default verification passed **1,347 tests with 65 skips** in 1,016.61 seconds. Its process
exited zero, as did the separate thirteen nested-contract tests in each layout. The full-suite
log is `/private/tmp/part3-native-comparison-default.log`. The additional contract tests were
collected after the suite started and are not included in its count. Final documentation checks
passed nineteen tests in 0.91 seconds. Ruff and `git diff --check` passed. Optional Bayesian tests
were not run because no Bayesian implementation changed. The source and installed preparation
pins, all captured proposal bytes and absent runtime/lease paths were rechecked. The original
checkout remains clean, and its four-line development-plan addition is preserved in this worktree.

This increment does not complete Part 3. The next implementation is the native matched runtime,
including an interruption charged inside each live case's original host/task/time/byte ceilings,
per-call fixed-worker evidence and a separate read-only native report. It must bind completed
real-provider conformance before starting a matched clock. Current-source registration evidence
also remains pending. Real-provider conformance and measured Leaf River execution still require
separate authorization after their commands and immutable inputs are reviewable. No commit,
push, credential read, provider request or measured-model execution occurred.

## Native matched runtime and owned interruption

The native matched runner is implemented in `native_runtime.py`, with separate interruption,
provider-proof and status modules and the `native_run` CLI. Native preparation version 1.1
captures those drivers, the common broker/control readers and its recipe. Earlier 1.0 proposal
bytes stay unchanged. A changed source cannot resume an old preparation. The existing package
sources and five role prompts did not change in this increment.

Creation verifies the actual caller-pinned conformance report, original preparation, exact
batch specification and journal head before creating the matched clock. Runtime origin binds
the report digest and head. Resume rechecks them. Authored or incomplete conformance cannot
satisfy the unmodified prerequisite. Source/configuration/pin changes reject before dispatch.
Preparation still grants no execution authority and returns `execution_ready: false`.

Each live case starts one fixed control task in its ordinary worker journal. An owned
supervisor dispatches through the existing batch adapter. It is interrupted only after the
native client and fixed upstream have separate ownership receipts, with credential preflight
still behind its closed launch gate. Independent watchdogs prove both groups stopped. The
same scheduler reconciles the original invocation as `host_failure`, retaining unknown model,
usage, duration and transcript cost. The original transcript ceiling stays charged. No repair,
replacement supervisor or free invocation is created. Readiness/stop uncertainty blocks further
work and is visible in status. The task and invocation consume the original case and aggregate
allowances. Both live cases retain twenty host calls, sixteen tasks and four repairs each.

The native case handler reuses the existing scientific controller, frozen supplied candidate
order and exact static invalid-unit control. Its role context names the native protocol.
Provider evidence is required for every later native invocation, including rejected handoffs.
The fixed command, response receipts and bounded response stream must agree with the observed
model/usage. Missing proof cannot pass a case. Physical host starts, request intents, confirmed
responses and logical calls remain separate; unknown request counts remain unknown. The status
reader verifies saved heads and artifact bindings without host/model imports or lease reads.
It rejects synthetic batches as live evidence. Exposure and confirmation limits stay unchanged.

Focused source checks passed **45 tests** in 157.37 seconds. A subsequent context-version
correction was exercised by the native case handler's declared synthetic/fake baseline test,
which passed in 114.58 seconds: 38 scientific starts, thirteen logical calls, zero provider
calls and unchanged work on replay. Installed verification passed **46 tests** in 275.12
seconds, including that handler test. All 132 installed Python package files and five prompts
match the prior verified wheel. The complete current-source suite is running in session 39956;
its final result is not yet claimed here.

Source and installed `native_run status` commands also passed against an empty authored
runtime, with zero charged work and `live_comparison_complete: false`. Missing execution
arguments return the parser's exit code 2 without creating the genuine runtime. Receipt:
`native-cli-readonly-smoke.json` under the evidence root below. These commands are distinct
from the unit test's direct reader-import check.

The first scoped run found a missing origin in the authored empty-conformance fixture and
restricted `ps` access during ownership inspection. The fixture now includes the real origin
format, and scoped ownership tests run with the required local process-inspection permission.
Two later assertions expected a nonexistent generic `failed` invocation state. Actual recovery
correctly produced `host_failure`; the driver/tests now preserve that explicit state. The first
installed run used the package outside its required example source layout and rejected missing
registered source files. Repeating with the verified wheel files beside the explicit bundle
passed without changing validators. An initial safe-path CLI check also needed the example root
in its explicit import path. All failed logs remain preserved.

Evidence is under `/private/tmp/part3-native-runtime-20261027/`:

- `genuine-proposal/` is prepared against the actual qualified 0.155.1 profile, with no stub.
  Pin: `889722abcbb0e7ddc109b8984f61dbb74e3dc42b73228db6bde43cd1a87afda6`.
  `genuine-runtime/` remains absent. This does not establish model availability.
- `offline-native-profile-receipt.json` records two actual-profile ownership probes, one for
  each live route. Both passed and replayed without work. Qualification is unmodified, but the
  conformance prerequisite is explicitly stubbed. These controls used two host reservations,
  zero scientific starts, no ordinary model tasks and no credential preflight/provider calls.
  Their native preparation pin is
  `9393d63ff86ba9dc779fe34be9f26f9fafdec85cb733c5b18f0f4b078f94b416`.
- `offline-native-profile-probe.py` and its supervisor wrapper preserve the executed fixture.
  Skipped scientific cases carry unit-only attestations. This is not real-provider conformance
  or a completed matched comparison.
- `verification-pending-default.json`, source snapshot, installed layout and logs retain the
  focused checks. Full-suite output is captured from session 39956, with an initial checkpoint
  in `default-output-checkpoint.log`. The process receipt identifies the exact running command.
- `pending-run-requests.json` records reviewable commands and separate maximum allowances for
  the current-source generated fixture, actual conformance and measured comparison. Nothing
  in that file authorizes execution. The combined ceilings are 56 host calls, 114 measured
  starts, two public conformance starts, three authored generated-fixture starts, three container
  starts and 2,640 elapsed seconds. The generated-boundary qualification itself is reused only
  after current-source/platform verification; no probes or containers were rerun here.

The managed-cache helper's 900-second lease lifetime is shorter than those combined maximum
deadlines. Each fixed worker checks remaining lifetime before dispatch. Expiry can stop the run;
there is no automatic refresh, fallback or allowance extension. Exact account/source selection,
lease provisioning/timing and live execution require separate authorization after verification.
Current-source generated registration evidence also remains pending because the old execution
closure rejects the changed CLI. The original checkout and user development-plan addition are
preserved. No commit, push, credential read, provider request or measured execution occurred.

## Original-matrix audit, reporting correction and current registration

The previous broad run exited nonzero: 1,392 passed, 65 skipped and one command-fixture failure
in 1,245.26 seconds. The harness invoked Python by absolute path but omitted its directory from
PATH. The fixture's explicit `python` command therefore exited 127. This is retained in
`default-tests-superseded.log`, not reported as a passing suite or a package defect. The corrected
full run uses Pixi's Python directory in PATH, preserves a process/source receipt and writes a
JUnit file. It is active in session 22549, with log `corrected-default.log` and process receipt
`corrected-default-process.json` under the same private evidence root.

The section 10 audit added four exact privilege attacks to the permission tests: investigator
evaluation, implementer acceptance changes, reviewer source edits and orchestrator budget
expansion. All fail typed handoff parsing, leaving the original run unchanged. The permission
file passed thirteen tests in 0.60 seconds. These additions were collected after the earlier
broad run started, so they are separate evidence until the corrected full result is available.

The audit also found a native reporting defect. An unavailable provider proof made `all(...)`
stop verification, so a later missing provider artifact could remain unchecked in a failed case.
`test_agent_native_reporting.py` reproduced the missing rejection before the fix. The reader
now verifies every proof before combining pass flags. The regression and related proof,
permission and command-contract checks passed 38 tests in 1.03 seconds. Corrected installed
native/preparation/reporting/permission checks passed 59 tests in 156.70 seconds. An initial
installed command selected an unrelated research test absent from that explicit bundle and ran
no tests; the corrected command selected the actual bundled files. The research command case
was checked in source and is included in the full run. No validation rule was relaxed.

Only the example evidence reader changed, so the package's 132 Python files and native host
qualification remain unchanged. New preparation roots capture the corrected reader; earlier
proposal pins are not rewritten. `review-proposal/` has pin
`806e5585519ec5634e3f20cd9a26fc00fa693769b4d994e9467c0800cda8c245` and remains unexecuted.

The generated admission audit found that a new container/scientific fixture is unnecessary for
the current registration. The original captured source, interface runner and actual passing
interface/qualification packet still verify. Its separately pinned authored fixture review
names those same unchanged bytes and checks. The trusted `register_candidate` API accepted
them unchanged and created a new standalone local fixture registration bound to the current
execution closure. It did not edit the old registration, parent campaign or any budget, and
did not invent a new human review or scientific observation.

Current fixture registration:
`92c7a82cad845a4a6fce7d5a1ef36231681be902913b6febdbee36640d0eabdd`.
Execution identity remains
`0395e8237a0c6406c26d1a77a62ec3db869bdf1c89f5ca15b6e0a697db4d1802`.
Original fixture review:
`b4e58093de882d9c11217c063681458cd3b82659d8eb1b4ddb9764afa0490758`.
Interface receipt:
`2150fa5f7e2c64879ccce13a8898784b1d593c216d11feb9b238b253d43e74cd`.
Source and installed readers verified the new registration and portable evidence. A no-process
guard prevented execution during both verifications. Receipts are
`current-fixture-registration-receipt.json` and
`installed-current-fixture-registration-receipt.json`. The old stale registration remains intact.
This is authored fixture admission, not live model generation, human author approval or new
scientific utility evidence.

Current Docker context/image/client/server metadata also match the saved qualification.
`current-runtime-metadata.json` records the match, with zero new containers, downloads or probes.
The first receipt writer used a nonexistent `ContainerRuntime.to_dict` method after the match
had passed. The corrected writer uses the dataclass serializer. No boundary check changed.

Final preparation uses a dedicated empty owner-private lease directory. It contains no credential
or attempted lease preparation. `lease-placeholder.json` records its ownership and empty state.
After separate authorization, the caller can verify/remove only this owned empty placeholder
immediately before the existing one-shot helper recreates its absent output. An attempted,
partial or nonempty lease directory must never be reused. Manual provisioning remains an
alternative. No source-cache path or expected account has been selected or read; an asynchronous
question requests that information without authorizing execution.

The final metadata-only roots are `live-conformance-proposal/` and
`live-comparison-proposal/`, with pins
`5fae7c70181ca6831814b10d9b41c13f943e69f24e60d2eeed9db390307fcee9` and
`ee94e281ef1ab4d4a147d963dcc7a6a013143c272d0f85d40e75a48ecead1a01`.
Host configuration digest:
`8bdc22ccd49858de09f88a82bc562137db31df2ebaf549fe0e4ac6931b49738e`.
Both runtime roots remain absent. `pending-run-requests-v3.json` supersedes earlier run requests:
no new generated fixture is needed. Remaining combined ceilings are 56 host calls, 114 measured
scientific starts, two public conformance starts, zero container starts and 2,520 elapsed seconds.
The lease helper still permits at most 900 seconds and performs no refresh or fallback. Expiry
can stop the run before its batch deadline. The source/account choice and actual execution still
need separate authority. Part 3 remains incomplete and active. No commit or push was made.

## Final offline verification and live authorization handoff

The corrected full suite exited zero: **1,398 passed, 65 skipped** in 1,209.07 seconds.
`corrected-default.xml` contains 1,463 cases with zero failures/errors. The JUnit audit checks
the named contract, four role-attack, grant, injection, handoff, host, parent-death, scientific
recovery, generated-boundary, scientific-authority, reporting and command-fixture cases
individually. They all passed rather than being skipped. `junit-verification.json` retains that
mapping, every skip reason and the log/XML hashes. This supersedes the prior PATH-harness failure,
which remains preserved. Corrected installed focused checks passed 59 tests. Final Ruff,
documentation and diff checks passed; no optional Bayesian run or old frozen matrix was launched.

Final input verification confirms the worktree import path, unchanged checked source hashes,
132 package Python files matching the verified wheel, host source identity, exact native binary
SHA-256, preparation pins and current fixture registration. Both live runtime roots remain
absent and the dedicated lease directory remains empty. Its receipt is
`final-input-verification.json`. No real cache/credential was read and no provider or measured
model execution occurred.

The original verification matrix is now mapped in the acceptance inventory, with its platform
and evidence limits retained. The remaining gaps are real-provider conformance and the
conditional measured comparison. The source/account selection question remains pending and
does not grant read or execution authority. The reviewable
`docs/reviews/part-3-live-authorization.md` binds the commands, pins, roots, 56 host-call ceiling,
two public and 114 measured starts, zero new container starts and 2,520-second dispatch windows.
It also states the 900-second lease limit and expiry behavior. This new document could not be
opened by macOS's default Markdown handler (error -10661), so its file link remains the review
entry point. No viewer installation or global setting was changed.

Part 3 remains active and incomplete pending explicit source/read/execution authority and actual
results. No commit, push, publication, source-cache discovery or automatic refresh was performed.

## Live approval received; automatic egress review rejection

The user approved the live validation and explicitly selected `~/.codex/auth.json` with the
account recorded there. The goal was resumed as active. `live-authorization.json` preserves
that instruction and its original ceilings. Metadata-only input verification passed again.

The prepared operator script reads only that named cache, derives its recorded account in
memory, uses the existing one-shot 900-second lease helper, runs conformance, and starts the
measured comparison only if the real conformance gate passes. It performs no refresh/fallback
and does not print exception text, cache values, account IDs or response bytes.

Automatic approval review rejected the requested execution before process creation. Its stated
reason was insufficient explicit destination/payload authorization for credential and scientific
data egress, despite the user's approved budget and cache choice. No workaround or indirect
execution was attempted. Filesystem verification confirms no operator log, source-read attempt,
runtime or lease exists, and the untouched lease placeholder is still empty.

The fixed destination is HTTPS POST to `https://chatgpt.com/backend-api/codex/responses`.
The bearer credential/account ID are authentication headers. Body content includes role/task
instructions, schemas, permitted task context, candidate configuration, aggregate evaluation
metrics/checks and allowed role history. Broker allowlist and fixed-worker source inspection
confirm that raw forcing/observation arrays and refresh tokens are not sent. The source itself
was not opened for this inspection.

`auto-review-egress-rejection.json` records that scope and the unchanged approved ceilings.
The authorization document now states them explicitly. The original approval request omitted
that exact endpoint/payload description, so the additional question addresses automatic review's
stated reason. No cache read, provider request, numerical execution, installation or global
configuration change occurred.

## Approved launch stopped at source-directory privacy preflight

The user manually approved the exact previously rejected execution command, and the goal
returned to active. That command ran without changing its script or payload. It exited 2 in
the preliminary lease-source read, before the one-shot helper, conformance or measured stage.
The sanitized result is `lease_source_unavailable_or_invalid` in `live-operator.log` and
`live-operator-result.json` under the private evidence root.

Metadata-only diagnosis found that `/Users/cam/.codex/auth.json` is a regular, single-link,
owner-matching file with mode 0600, while its physical parent `/Users/cam/.codex` has mode 0755.
The frozen `private_read` implementation rejects a nonprivate parent before opening the file.
Thus no credential bytes were read. The helper was never called, the lease directory remains
absent after the approved removal of its untouched empty placeholder, and both runtime roots
remain absent. No provider or scientific allowance was consumed. The original attempt/result
records remain intact; no partial destination or budget was reset.

`live-source-preflight-failure.json` records the diagnosis and required mode 0700. No cache
contents, auth-file permissions or directory permissions were changed. Restricting this global
directory needs the user's approval; the private-reader boundary is not weakened to accept it.
The existing live budget, destination/payload approval and source choice remain in force.

The continuation is prepared at
`/private/tmp/part3-native-runtime-20261027/resume-authorized-live.py`, with its hash/conditions in
`live-continuation-preparation.json`. The original approved script remains unchanged. The new
preflight requires the recorded before-open failure, absent lease/runtime roots, unchanged
authorization/source/configuration hashes and an owner-matching physical source parent already
at mode 0700. It performs no chmod itself. It preserves the original attempt/result and writes
separate continuation artifacts. Its conformance/comparison body is the original approved code,
apart from those result/error names. No counter, budget or partial helper output is reset.
The program was parsed but not executed. Source-parent metadata is still 0755, and permission
to restrict that global directory remains pending. No cache bytes or live work were accessed.

## Real provider failure and offline transport repair

The user approved the exact provider destination/payload and the recorded account in
`~/.codex/auth.json`, then approved changing its parent directory to mode 0700 after the private
reader refused mode 0755. The credential contents and file mode were unchanged.

The authorized continuation created one 900-second lease and executed the first conformance
case. The provider returned HTTP 400. Conformance failed with one charged host invocation,
zero scientific starts, no pending reservations and verified local stop. No comparison started.
The original result is preserved under `/private/tmp/part3-native-runtime-20261027/`.
The expired generated lease copy was removed after stop without reading it. No remote
computation termination or server revocation is inferred.

The normalized request lacked instructions present in the native client's request. The original
response body was not read, so this difference does not establish the HTTP failure's cause.
The repair supplies a fixed trusted instruction and adds bounded error classification. It
retains only fixed codes/parameter names and rejects reflected credential/account values.
Seventy focused subscription, exchange and TLS tests pass. Fresh native qualification passed
with digest `676d12cee6a697f7aef6b8d03d82667f57fcdafef9359c0dada0e8cc16a3e58d`.
These checks use authored local responses with no provider or credential access. Ruff passes.
The full source suite is running against the repaired source. Earlier wheel and host pins remain
historical. Fresh preparation preserves the original failed run and charges its one call against
the original total. No second live request has occurred during this repair.

The bounded repaired launch used the existing user authorization, selected credential source,
account, endpoint and model. Its fresh conformance preparation digest is
`fb755ef10e33b41d3fb3b30a5e5d38e7234a759da3ec96e8a7b6bb45f6940d37`.
The first repaired text request also returned HTTP 400. The sanitized provider diagnostic now
records `model_not_found` for requested `gpt-5.5`. This establishes provider rejection of that
selection, not general model availability or account validity. The original response body is
not persisted. No fallback or further live request followed.

The repaired runtime failed with one charged invocation, zero scientific starts, no pending
reservations and verified local stop. Across the original and repaired runs, two host calls are
charged. Neither comparison started. The generated lease copy was removed without reading its
contents after verified stop. The original cache remains unchanged. The user was asked to
select an exact replacement model or stop live validation. A replacement needs fresh model-bound
preparations and must retain both charges and the original elapsed/scientific ceilings.

## Selected GPT 6.1 Sol and bounded protocol failures

The user selected GPT 6.1 Sol. The exact local catalog slug is `gpt-6.1-sol`.
The original 0.155.1 executable lacked metadata for it and emitted an error item. The 0.163.0
local probe failed managed-preference startup. Both offline failures remain under
`/private/tmp/part3-sol-validation-20261027/`; neither used real credentials or a provider.
No failing profile was promoted and error parsing was not weakened.

The transport now accepts explicit model-catalog bytes from a trusted qualification. The
catalog must contain exactly the selected model, fit 65,536 bytes and pass strict JSON parsing.
Its artifact is bound to the profile and each invocation. Recovery rejects changed bytes in the
client copy. There is no runtime catalog/cache discovery. The selected local model record stays
outside the repository. Its derived text-only copy changes only `tool_mode` to null, leaving
Code Mode and every native tool disabled. Original and derived hashes and the reason are in
`text-catalog-provenance.json`. The provider request still contains only the approved normalized
text/schema payload, not the catalog or native instructions.

The first Sol profile passed all nine original native qualification groups. Its actual text
request received HTTP 200, then failed the strict response-header check before reading a body.
The conformance gate failed, with verified local stop, no pending work and zero science starts.
The temporary credential copy was removed without reading it. Cumulative host charges became
three. The comparison remained unstarted.

Sanitized header diagnostics were then added. They retain only fixed content-type and encoding
categories. Source focused checks passed 140 tests. The final fresh native qualification passed
with digest `039bf78ef38107a32dfce1b36e94dacd563b6680297c2d975e52ceb2e1ec7593`.
The last bounded preparation preserved all three prior charges and used only 540 seconds of
new conformance dispatch time after conservatively charging 180 prior seconds. Its conformance
preparation is `39f051a3e70548c7f0634b3aa7042849b2bc1f426ded974618b26a3f08997dfd`.

That real Sol text request also received HTTP 200 and failed strict headers. Its sanitized
content-type category is `other`, and its encoding is `identity`. The exact unsupported MIME
value was not retained, so no specific replacement protocol or header relaxation is justified.
This is not passing conformance, verified model resolution or a scientific result. Evidence is
under `/private/tmp/part3-sol-header-20261027/`. Cumulative charged host invocations are four.
All scientific starts remain zero. No comparison started, no reservations remain pending, and
the generated lease copy was removed after verified local stop. The original credential cache
was unchanged. No further live execution followed.

Before the catalog changes, the full source suite passed 1,411 tests with 65 skips in 1,253.66
seconds. The next run was deliberately interrupted before changing diagnostics, retaining its
169 passes and five skips as incomplete evidence. The complete final-source suite is running
under the final evidence root. Passing prior totals do not substitute for that result.

## Missing MIME and provider metadata compatibility

A diagnostic-only launcher spent one additional approved text-probe slot, capped at one call
and zero science. It identified the actual missing `Content-Type` header. The candidate then
allowed an omitted MIME header only through bounded stream framing and the existing complete
pre-delivery response validator. Explicit non-SSE types, encoding changes, HTML/JSON bodies,
tools, missing identity/usage and incomplete responses still fail. Bounded MIME diagnostics now
redact reflected credential/account values. No raw arbitrary header or provider message is used
as an instruction. The missing-MIME behavior and negative controls pass local tests.

The next one-call probe received a complete, credential-checked provider stream from
`gpt-6.1-sol`. It was rejected before client delivery on the previously unsupported
`response.metadata` event. Total charged live calls became six. No science or comparison ran.
Every original failed gate and unknown-usage ledger record remains unchanged. All generated
credential copies were removed after verified local stop, without reading their contents.

The response decoder now accepts only a bounded, typed metadata envelope for the same completed
response ID. Metadata is discarded rather than copied into client output. Foreign response IDs,
malformed metadata, action fields and post-completion metadata are rejected. Other unknown events
still fail. The decoder version is `text-response-1.1`, and the fixed worker version is
`codex-subscription-1.3`.

The actual captured response SHA-256
`6e2ede471ed6de93e9759af7cb79f4525fe5c3198a3f23d21315ef2514399797` passes offline replay with
the final decoder. It contains the requested public acknowledgment, reported model `gpt-6.1-sol`,
133 input tokens and 21 output tokens. This recovered usage is separate from the unchanged old
ledger. A sandboxed native replay of the same saved response also passed with verified stop and
an identical normalized request. Its receipt writer initially used the wrong stop-field name.
Read-only recovery corrected the receipt without another invocation. Both replays made zero
provider calls and do not turn the failed live gate into a pass.

The final source and wheel focused runs each passed 171 tests. The wheel SHA-256 is
`cd6a88758d92514ad9d476891a567859ac5cee9af5f5d9e637b0cf1e4192f5c6`, and all 138 package
source/prompt files match. Final native qualification passed all original groups with digest
`5533596bbe49697d692c3b00814c7839afbd234ad483b80fc460676f321ea265`.
Before these last compatibility changes, the full suite passed 1,424 tests with 65 skips in
1,180.51 seconds. The final-source full suite is running under
`/private/tmp/part3-sol-final-20261027/`. No earlier count is claimed for that changed source.

A supplemental proposal is prepared under `/private/tmp/part3-sol-final-live-20261027/`.
It preserves six prior host charges and all failed runtime roots. The full frozen conformance
cases permit thirteen new slots and the comparison forty. Their cumulative maximum is nineteen
conformance and fifty-nine total slots, three above the original sixteen/fifty-six ceilings.
Public science stays at two starts and measured science at 114. Charging sixty seconds for each
prior attempt gives 360 prior seconds plus 720 new conformance and 1,800 comparison seconds,
for 2,880 cumulative seconds. This is six minutes above the original 2,520-second allowance.
The fresh proposal clocks have not started, and its lease placeholder is empty. Its launcher
requires an explicit supplemental authorization bound to the final execution packet and a
passing final offline-verification receipt before opening the selected credential source.

The final-source suite completed: 1,438 passed and 65 skipped in 1,174.34 seconds. JUnit confirms
1,503 cases, zero failures/errors, and no skips in sixteen required contract/permission/host/
recovery families. The final source and wheel focused checks each passed 171 tests. The source,
wheel, native qualification, saved actual response replay and unchanged generated-fixture
registration all verify. No scientific run, container probe, old BO gate or provider call was
added for this final verification.

The ungranted supplemental draft was tightened before requesting approval. It now keeps the
original 2,520-second cumulative dispatch allowance: 360 conservatively charged prior seconds,
a 360-second owned supervisor for new conformance, and 1,800 seconds for the conditional
comparison. The immutable inner conformance specification retains its original limits and
criteria. No extra elapsed time is requested. Only the three additional cumulative host slots
are needed. The final launcher refuses credential access without a user authorization bound
to the final packet and a passing offline-verification receipt. All runtime roots remain absent.

## Approved supplemental run, launcher failure and recovery

The user approved the three additional host slots for packet
`da30a4d0a16b23fbbff1d763b1cf9282e82fafb9a0d2a9fcaba81861bf8249cb`.
The fresh live text case passed with actual provider evidence. The role case then reserved its
first public scientific attempt. The outer launcher's sanitized environment omitted the explicit
project import roots from nested scientific processes. Python could not import the campaign
trampoline, so no numerical result was produced. The attempt remains charged and its cost is
unknown. Saving the second report also failed because the wrapper used immutable writes for a
latest-report projection. Both are launcher mistakes, not a model/account failure.

The original first report remains intact. `conformance-report-after-stop.json` reconstructs the
pending state. The stopped process identity, nonce, supervisor result and group absence were
verified. Standard review reconciliation exposed a transition-table defect for fixed failures.
The original attempt was then closed with the existing cancellation/recovery APIs. A trusted
stop observation was appended without refunding the charge or clearing unknown cost. The role
case is failed, all physical reservations are closed, and the generated lease was removed.
`bootstrap-reconciliation.json` records seven cumulative live host calls, one charged public
reservation, zero measured starts and no comparison. The old gate was not relabeled as passed.

The launcher now establishes explicit project imports only for trusted scientific descendants.
Native CLI processes retain their separate environment. Latest reports use replaceable
projections with immutable content-addressed snapshots. A nested import-only check exercised the
actual sanitized outer process and campaign trampoline with valid start/finish receipts. It
performed no numerical evaluation or provider call. Multi-case stage tests preserve six report
snapshots and verify the conditional comparison path. Bounded traceback records retain only
file names, function names and line numbers, never exception messages or local variables.

The campaign review rule now permits the terminal states already returned by its fixed-attempt
reconciliation handler. Two regressions verify fixed failure and unavailable confirmation without
launching science or clearing unknown cost. The full suite passed 1,440 tests with 65 skips in
1,185.42 seconds. Source focused checks passed 180 tests. The first installed harness run had
three recovery failures because its working directory let canonical examples shadow the bundled
copies. The registered-location guard correctly rejected those imports. Running from the
standalone wheel project passed all 180 tests. Both logs remain. The wheel SHA-256 is
`2242e0a56887be0caabe11f4bac7cdb405f331e83bf786ca777604b235fde0c6`, with all 140 source,
prompt and configuration files matched. No global installation changed.

The recovery fix changes one input in the 93-file Leaf capture: `campaign/service.py`. All data
arrays, model implementations, seeds, splits, limits and scientific criteria remain unchanged.
The fresh Leaf digest is `2148dc850b6876878ffc3cadd5488c6e9bc2819fd0ccb66df352b5050c7bb63b`.
The native source/policy closure is unchanged and its qualified pin remains valid. The generated
fixture has a fresh execution binding `99a956bafa8c135b256521c873f87698a84b4d9c44b7cf43495e39500e599b01`
and registration `04cb63c053c374ec42a9719c51bb0b16a82738b8d0cc236f00d6d1ede76b87a4`.
Its component, driver, archive, interface evidence and original authored fixture review are
unchanged and verify. No human approval, container start or new scientific result is inferred.

The corrected fresh proposal is under `/private/tmp/part3-bootstrap-fixed-live-20261027/`.
Packet `ed81950801876f02abde927ba67a7d98112c704d76a381493094774ec7ebb09c` requests one
additional host slot (59 to 60 cumulative) and one public reservation (2 to 3 cumulative).
This includes the seven prior calls and one failed public charge. Each new conformance case
retains its original criteria and allowances. Measured starts stay 114 and cumulative dispatch
time stays 2,520 seconds: 420 prior seconds charged conservatively, 300 new conformance seconds,
and 1,800 comparison seconds. Its runtime roots are absent, the credential placeholder is empty,
and additional authority has not been inferred from the previous approval.

## Approved launcher recovery: failed investigator eligibility

The user approved the exact recovery packet above. The live run used the selected account
and `gpt-6.1-sol`. Text passed and the scientific baseline executed successfully. The second
role invocation returned a candidate brief with nonempty eligibility gaps. The frozen role
case has zero repairs, so the response is rejected. The broker then attempted a repair and
raised `StoreError: repair allowance exhausted`. No additional call was launched.

The failed role verdict was explicitly recorded after checking the worker journal, completed
outer supervision, known scientific cost and absence of pending actions or reservations.
`/private/tmp/part3-bootstrap-fixed-live-20261027/conformance-report-reconciled.json` records
text passed and roles failed, with three host calls and one public scientific start in this
batch. `invalid-role-closeout.json` records cumulative charges of ten host calls and two public
scientific reservations. All earlier failures and unknown cost remain visible. No measured
comparison started. The temporary lease was removed without claiming server revocation.

The rejected brief listed candidate evaluation and independent confirmation as proposal
eligibility gaps. The investigator prompt now explains that those later checks are scientific
limitations, while unmet proposal prerequisites remain blocking eligibility gaps. No missing
evidence is invented and the nonempty-gap rejection remains unchanged. The broker now raises
an explicit `WorkflowStopped` before dispatch when its frozen repair allowance is exhausted.
Two regressions exercise zero and one allowed repairs across reopening, preserving the
baseline, invalid responses and exact call counts.

The first restricted test run could not perform required subprocess inspection. A subsequent
run passed 32 tests but failed one template identity check because the prompt changed during
that run. Its failure and the passing isolated rerun are retained. Final checks use unchanged
source. Earlier profiles and preparations remain immutable and require fresh qualification
before execution. Another full conformance run needs two public starts, exceeding the one
remaining under the approved cumulative ceiling. No replacement run was launched.

Final unchanged-source checks passed: 73 broker, source-preparation, conformance-runtime and
documentation tests in 155.45 seconds. Full Ruff and `git diff --check` passed. Logs are
`repair-stop-final-tests.log` and `repair-stop-lint.log` in the latest live root. These checks
do not replace real-provider acceptance or update the earlier full-suite/wheel evidence.

## Exact-source recovery packet prepared without live execution

The current wheel passed the same 73 focused tests in 154.61 seconds. All 140 package
source/configuration files match. The final source remains
`bb78821c5a141babe39236e75cb7abe160fe8fb5b6624fe952610819b6e5cc16`.
A new offline native qualification passed, with digest
`6486baa9e1f2d9337a6d421f9c5c13534e3219fc7cbf981316fbd841df2b019e`.
No account cache or live provider was used. The existing Leaf preparation still verifies
unchanged, including numerical sources, data, seeds, splits, criteria and allowances.

Fresh conformance and comparison proposals are prepared under
`/private/tmp/part3-eligibility-recovery-20261027/`. The operator passed eight authored fixture
cases covering missing/mismatched approval, changed source, insufficient budget, conditional
comparison dispatch, six immutable report snapshots and sanitized supervisor environment.
All 507 execution-packet file hashes match. Conformance reports ready; comparison correctly
reports not ready until its actual live conformance gate passes. Runtime roots are absent,
the credential placeholder is empty and no actual authorization file was created.

The [supplemental request](part-3-eligibility-recovery-live-request.md) binds exact packet
`21176a8b027a107b10154e11a1f0bc522d0ea834a69c1a03d5fa77d449c7a817`.
It requests three additional host calls, one public scientific start and 300 dispatch seconds,
raising cumulative ceilings to 63 calls, four public starts and 2,820 seconds. Measured starts
stay 114. Ten prior host calls, two prior public starts and 720 conservative prior seconds remain
charged. Model, account, destination, payload scope and frozen criteria remain unchanged.
No fresh live execution is authorized by the automatic goal continuation.

## Full-suite watchdog race and withdrawn packet

The next full default run completed with 1,441 passed, 65 skipped and one failure in 1,186.84
seconds. Its JUnit report and failure analysis are under the eligibility recovery root. The
failing SIGTERM-ignoring timeout test raised `PermissionError` in the supervisor's `os.killpg`
call while the independent watchdog stopped the group. The saved `host_failure` was exception
cleanup, not proof of the initially suspected normal exit-classification path. The full
traceback corrected that receipt-only diagnosis. Original receipts were copied before cleanup.

Packet `21176a8b027a107b10154e11a1f0bc522d0ea834a69c1a03d5fa77d449c7a817` is withdrawn.
Its source, profile, wheel, failure and request records remain intact. No live run or credential
read occurred and no additional allowance was inferred from the outstanding question.

After the suite was terminal, `_stop_owned` was changed to check group absence before each
signal and after `PermissionError`. A denied signal with live members returns unverified,
without another signal. An absent group allows reaping the owned direct child and recording
the stop. This preserves the timeout cause from the supervisor without broadening signal
authority. Two regressions use real owned groups to simulate both outcomes. All 26 focused
process/watchdog tests passed in 9.61 seconds. Ruff passed. Fresh current-source full-suite,
native profile and disposable package verification must precede any replacement live packet.

The corrected source is `691a414f19e6f4c7437d989300f11317d921393f562a6395970ee957c61947ca`.
Its fresh offline native qualification passed with digest
`48ae920411c7041c76be189566cd133e8bbce3edc0c430001ea1b501cda0fe49`.
The rebuilt wheel is `0ecfc1694eaff585b280b3f55a91975ea76b9a714f488d8c85fe374e07f9dff3`,
with all 140 package source/configuration files matching. Its disposable installed layout
passed 99 focused tests in 174.26 seconds. JUnit inspection confirms both new denied-stop
cases, all three existing watchdog stop cases, both repair-limit regressions and scientific
lost-response recovery executed without skips. Full Ruff and whitespace checks passed.

A new full default run is active under `/private/tmp/part3-watchdog-race-20261027/`.
Its starting source snapshot contains 3,334 files and still matches. Fresh conformance
`eac9c058d000189f10ecd7e293423f5f6fbf9f4883b9c6a101b55a54f307594c` and comparison
`7b439dd6748ecb18207a567f63b87b8d522fa2ebe4d630b1930281bc0ef2bbdf` proposals are prepared.
They retain the unchanged Leaf preparation and frozen limits. Runtime roots are absent and
the credential placeholder is empty. No replacement live packet or approval has been created.

The new full default suite is terminal and passed: 1,444 passed, 65 skipped in 1,191.32 seconds
according to the pytest summary. JUnit records 1,509 cases with zero failures or errors and
1,191.26 seconds of suite time. `default-verification.json` confirms the named permission,
reporting, recovery and stop cases ran, including both new denied-signal cases and all three
watchdog stop cases. All 3,334 captured source files remain unchanged.

The replacement operator passed nine authored cases, adding explicit rejection of a withdrawn
packet before credential access. Conformance and comparison inspections verify their exact
pins. Conformance is ready; comparison correctly remains gated on actual live conformance.
`preapproval-verification.json` checks all 511 packet file hashes, the current native profile,
absent runtime roots, empty lease placeholder and absent actual authorization.

The [replacement request](part-3-watchdog-recovery-live-request.md) binds packet
`24f28077a3cd16112bbafb7767c768a6cbc59c0b6c15f22d9dc2b5c0dbb873fc`.
It requires the same additional three host slots, one public scientific start and 300 dispatch
seconds requested by the withdrawn packet. No such increase has been inferred from automatic
goal continuation. Existing cumulative ceilings remain 60 calls, three public starts and
2,520 seconds until the user approves the replacement. Measured starts remain zero out of 114.
No live call, new scientific start or credential read occurred during this recovery.

## Standing ChatGPT approval, failed reviewer citation and exact-name diagnostic

The user approved all agentic calls to ChatGPT and resumed the goal. The exact watchdog
recovery packet was reverified and executed using the selected source/account and model.
Text passed. Investigator, implementer, orchestrator and reviewer all ran, and the two public
scientific attempts finished with known cost. The reviewer returned descriptive strings such
as an evaluation ID followed by `finite`, version and status. Its `supporting_checks` must
instead contain literal check names. The unchanged broker rejected these citations. With
zero repairs, the role case failed after six role calls, plus one text call. No comparison ran.

`/private/tmp/part3-watchdog-race-20261027/review-failure-closeout.json` verifies the stopped
supervisor, empty pending reservations, removed lease, cumulative seventeen host calls and
four public starts. All earlier failures and unknown earlier scientific cost remain. The
scientific state stays unaccepted at evidence review. The graceful repair-limit stop worked.

Output contract `role-output-contract-1.1` and reviewer template 1.1 now explain that findings
copy exact `check.name` strings from the current evaluation. IDs, versions, statuses and prose
belong in `description`. The authoritative exact-name validator is unchanged. A new regression
keeps descriptive citations rejected, with no acceptance, extra evaluation or repair across
reopening. Its initial two test-authoring failures used the wrong state accessor. The corrected
test reads the authoritative projection and passes. The other 57 focused cases passed in the
original focused run. Those separate results do not substitute for the pending full suite.

The fresh native qualification is
`654c9f3ddf7511f44098a03a71a86b405080ae845f26af2bfd622751d629891c`, bound to host source
`149e6ad5b7561f75b9b093d6221d04af75c45b5c6bd465744d554691d8840218`.
A separate review-only diagnostic used the captured public scalar evidence. Its first launcher
stopped before any host reservation/provider call because its lease client root was absent.
That setup failure is preserved. A fresh diagnostic directory fixed the preflight and executed
one call under standing user approval. The real reviewer returned `finite` check names and
passed the strict parser and exact-name validator. Its advisory recommendation was `proceed`.
No scientific controller, evaluation, acceptance or confirmation ran. The old failed gate was
not relabeled. The stopped diagnostic has no pending invocation and its lease was removed.

Records are under `/private/tmp/part3-review-contract-20261027/`, including
`diagnostic-v2/closeout.json`. Cumulative charges are eighteen host calls, four public starts,
zero measured starts and 1,080 conservative dispatch seconds. Source
`standing-authorization-scope.json` records the user's wording and the operator's interpretation:
standing authorization covers the agentic validation workflow and its local public conformance
prerequisites. Future fixed run caps are derived and recorded, not claimed as numbers separately
specified by the user. The next allocation is 71 cumulative calls, six public starts and 3,180
dispatch seconds: eighteen prior calls plus thirteen fresh conformance calls and forty conditional
comparison calls; four prior public starts plus two new public starts; 1,080 prior seconds plus
300 conformance and 1,800 comparison seconds. The original measured ceiling stays 114.

The new full default suite and disposable installed checks are running. Full Ruff passes, and
all 140 current package source/configuration files match wheel
`4c240476b215a55826492cb66a7a85e21d836be4702dd6ecf691a383f3c351d2`.
Fresh proposals under `fresh-live/` bind conformance
`8b497424c25f37fb1093f334e4cdcdb439ff5efe5f4fbf6b4fa8d46d670fe428` and comparison
`0bd56acb178a8b0442941177d408a84b3eac0b9054597936d0f6c12eb07365f1`. They preserve the
unchanged Leaf preparation and all per-attempt criteria. No fresh live runtime has started.

## Exact successful receipt recovery and preserved source boundaries

Installed checks for the clarified review source passed 144 tests in 239.39 seconds. Its full
default run was then interrupted intentionally after a separate read-only proof check exposed
a producer/reader mismatch. The fixed worker 1.3 records `header_diagnostic` when a successful
SSE response omits Content-Type. `recover_subscription_response` still expected the older
success dictionary with no diagnostic. That would prevent complete comparison provider proof,
even with a valid actual response. The first command/scope verification was narrower than
complete provider proof. `diagnostic-v2/verification-scope-note.json` records that distinction.

The owned pytest process received SIGINT and was observed terminal with exit 2 before source
editing. Its interrupted XML/logs, source snapshot and interruption intent remain intact.
No additional provider request or scientific execution occurred during this proof investigation.

The reader now permits the exact optional successful diagnostic `content_type=missing` and
`content_encoding=identity`. It still requires the full success dictionary, fixed-worker source,
request/destination/scope bindings and saved response proof. Added tests run the actual worker
against a local mock with an omitted MIME header, then exercise read-only recovery after deleting
the fake credential. Extra fields, HTML MIME, gzip, malformed diagnostic shapes and unrelated
result fields remain rejected. All 93 subscription/evidence tests passed in 4.51 seconds.
Formatting, full Ruff and whitespace checks pass. No source-identity guard was relaxed.

Replaying the original diagnostic with the changed production source is correctly rejected by
the host source guard. Its typed review remains a diagnostic, not a retroactively qualified
provider or conformance result. Complete current-source live proof must come from the next
fresh actual conformance run. The old preparation was superseded before execution and remains
preserved. It charged no calls or scientific starts.

The final receipt-compatible host source is
`2f7e283bdb4b0c2a104134353de8aa14f67e05438e5ae5b9867f6d147544c12c`.
Its new offline native qualification passed with digest
`dba8c06369049d4858af9d472e9841b0f0e07a90950e92c50af65dd8a693591b`.
All 140 package files match wheel
`e6ab662f8b7fc3fc5b76a75a2606af43f71bb9324b027cd2a10958c8b6d6427d`.
Current full default and expanded installed checks are running under `proof-recovery/`.
All 3,334 captured source files remain unchanged. Fresh conformance
`c4a9ed14cfac74b2b5d607a6b20667d44bf22923f23e658fde480e8d6fd6b70f` and comparison
`80449770c14ecbfcdd29396c43fd2e4d27b0c680604a4150394a25bcae3e3758` preparations retain
the same numerical inputs, criteria and standing-approval allocation of 71 calls, six public
starts and 3,180 dispatch seconds. The measured ceiling stays 114 and actual measured starts
remain zero. The eighteen prior host calls and four public starts remain charged.

## Actual conformance passed; measured comparison stopped at review

The receipt-compatible source `2f7e283b` passed 1,451 default tests with 65 skips and 237
installed checks. The complete current-source provider proofs were captured during the fresh
live attempt. All six conformance cases passed. The conditional matched comparison then
failed its frozen gate. Its scripted and single-agent routes completed 38 numerical starts
each and selected identical Hargreaves configurations, with RMSE 3.1378289080395643.
Single-agent execution added nine charged host calls, eight provider calls and one repair.
The four-role route stopped at a blocking independent review after 18 numerical starts and
seven charged host calls, including six provider calls. It selected no final configuration.
No trusted override was recorded and no confirmation was attempted.

The review correctly identified missing binding evidence: the catalogue listed starting
parameters, while the checks reflected the calibrated configuration. The bounded summary did
not include the actual evaluation configuration, model identity or committed calibration link.
All four numerical checks passed, but that does not invalidate a provenance finding. The old
failed gate and worker/controller heads remain immutable. Cumulative usage is 47 host calls,
six public reservations and 94 measured starts. No pending reservations or unknown physical
cost remain in this comparison. Local stop was verified and its temporary lease removed.
Records are under `part3-review-contract-20261027/proof-recovery/fresh-live/` in `/private/tmp`.

## Common calibration context and bounded new preparation

Summary schema 1.1 now includes actual evaluation configuration/model/split, restricted purpose,
controller calibration policy and committed study links. Catalogue values identify starting or
fixed parameters. Child paths, raw arrays, evaluator details and checkpoints remain private.
Both agent routes use this common summary. Role contract/reviewer template 1.2 distinguish
pending downstream acceptance and disabled confirmation from prerequisites for review.
Strict check-name validation and genuine blocking findings are unchanged.

The new calibrated-review regression covers actual fitted configuration/study linkage,
copy isolation, protected arrays and absence of child paths. It and the selected contract/privacy
checks pass: 28 tests. The disposable current wheel passes all 238 installed checks in 258.57
seconds, with all 140 package files matching. Wheel SHA-256 is
`ca079739062d4b4a91b73bab639b26cd3ac64ca7c2899d5010c72654fbabd186`.
Current host source is `7092c5f57bfc0e154455c08310a8c2ad787d97373e8d3697184777ea7f74ad45`.
Fresh offline native qualification passes with digest
`3a5b4256eda34b93b572a0f9e0fee77dfa2cba77b9f1d7af144a3a120f41d18b`.
Full default verification remains running under `part3-calibration-context-20261027/`.

A one-call diagnostic is prepared using the captured aggregate Leaf review context and zero
new numerical execution. Automatic approval review rejected launch twice, requiring direct
payload disclosure approval despite the prior authorization record and blanket call approval.
The explicit clarification is pending. Both rejections occurred before process creation,
credential reads or host reservation. No workaround or alternate destination was attempted.

A fresh matched study preparation uses unchanged Leaf digest `2148dc85`, data, seeds, pool,
order and criteria. Conformance digest is
`467bedafca8a47df91096b5e05eed763aa6a2fd842798900a23159a0756b874f`;
comparison digest is `8889fe394eaa888236c70699c59d519413a5d2221404d392da0937ddbe093a2b`.
Its 114 fresh measured starts would raise cumulative usage to at most 208. This needs 94 more
slots above the original 114 ceiling. No numerical-budget authorization, credential lease or
live runtime has been created for it. The unused 20 original slots cannot fund a full matched
study, and replaying only the stopped route would change the comparison design.

Final current-source verification passed: 1,452 tests and 65 skips in 1,181.99 seconds.
JUnit verifies all named original-matrix regressions, including the new calibration-context
case, with zero failures/errors and all 3,334 source files unchanged. The installed run passed
238 checks. Eleven authored operator fixtures pass, including rejection before credential
access when direct payload consent or measured-budget approval is missing. They made no
provider request, credential read or numerical evaluation. The final prepared operator and
verification are bound in `fresh-study/execution-packet.json`. There is no actual authorization
file, lease or runtime for that study. Payload clarification and the extra 94 numerical slots
remain pending. Main checkout remains clean; no commit or push was made.

## Direct approval and calibration-context execution

The user approved both pending requests: the exact scientific aggregate payload disclosure
and 94 more numerical slots, for a cumulative measured ceiling of 208. The one-call captured
Leaf review completed with a proceed recommendation, exact check citations and zero new
numerical execution. Full provider proof verifies. Its standalone evidence capture first
failed because process inspection was sandboxed, then because the archive lacked its artifacts
directory. The helper was corrected and proof captured without another provider request or
production-source change. Verified local stop, no pending invocation and lease removal are
recorded in `review-diagnostic/closeout.json`. Cumulative prior charges are now 48 host calls,
six public reservations and 94 measured starts.

Fresh study packet `94e84e72f6bc587a65ed1f92b65e7bdadda652c3a65f801c6898684d5ca357fd`
preserves the reviewed packet and adds the approved diagnostic's actual charge and conservative
60 seconds. Its cumulative caps are 101 host calls, eight public reservations, 208 measured
starts and 5,340 dispatch seconds. The eleven mock operator fixtures pass with that charge.
The guarded operator is running conformance. It may start the matched comparison only after
all six actual cases pass. Same model/account/destination, numerical criteria and Leaf bytes.

## Preserved conformance failure and noncontradictory initial probe

The calibration-context attempt passed text, roles, timeout, cancellation and owner loss.
The malformed case returned a valid first handoff, so its intended rejection and repair were
not exercised. The frozen gate failed as designed, after 12 charged host calls and two public
starts. Comparison did not start. The operator exited 3 with verified local stop and no pending
reservations. Its lease was removed. Cumulative charges are 60 host calls, eight public starts
and 94 measured starts. The approved measured ceiling is 208, leaving the full 114-start new
comparison allocation unused. Records remain under `part3-calibration-context-20261027/fresh-study/`.

The probe asked the model for an intentionally invalid inner JSON while also supplying the
ordinary role template and valid-handoff schema. The model followed the ordinary instructions.
`MalformedProbeHost` now removes those contradictory instructions only for the fixed initial
probe. It keeps the task, invocation, empty grant set and expected invalid payload explicit.
The repair gets the ordinary template, full role contract and actual parser error. The host
rejects other tasks, roles, run IDs, grants or operations before preparing the diagnostic.
No provider response is injected, corrupted or rewritten. The gate still requires the actual
provider's exact invalid inner payload, strict rejection, provider proof and exactly one valid
repair with no scientific work. The old failed result remains failed. Neither parser nor
acceptance criterion changed.

All 21 focused conformance regressions pass in 66.09 seconds. The positive case checks stored
initial and repair prompts, raw payload preservation and actual parse-error feedback. Existing
valid-first, wrong-payload and missing-provider cases still fail without spending a repair.
Fresh offline native qualification passed with digest
`d3ab997189c68774d59e75d0917e48ba064ece064f5741fc9e53f984fe1750f1`.
All 140 package files match wheel
`91006a62a8c266995c0d245bf3d792845520503e00cf7979e825f9a0b9d70aa2`.
Full default and 238 installed checks are running against frozen source
`e74800bdad196cb9d6258a56a2b929bc1a8c133ff5e679e66695cfcb1450877c`.

The fresh preparation reuses unchanged Leaf inputs and approved numerical capacity. Its
conformance digest is `a43f86f7f4b126142c1e2633e266173bb039084bc6a7dfc848ed1c76a676d0f5`
and comparison digest is `229a5ea6e40f9c7f58750ed3da99e3253174113e2cba8fd8e8d291a61d6877ff`.
Read-only verification also rechecks saved generated-boundary qualification `42e91831` and
fixture registration `04cb63c0` against current source. It executes no containers or model.
Under standing call approval, the operator derives cumulative caps of 113 host calls, ten
public reservations and 5,640 dispatch seconds, including all prior charges. Measured capacity
stays at the expressly approved 208. No fresh live runtime or lease has started for this source.

## Current conformance passed; single-agent proposal failed before fitting

The noncontradictory probe source passed 1,452 default tests with 65 skips in 1,167.41 seconds,
238 installed checks and eleven operator fixtures. Its fresh actual conformance passed all six
cases, including the exact invalid provider payload and one valid repair. The conditional
comparison then stopped: scripted completed 38 starts, while single-agent exhausted its two
proposal repairs after its baseline. Four-role was not attempted. The actual errors were
unresolved proposal eligibility gaps and a wrong first canonical candidate. The model treated
future evaluation/calibration as proposal prerequisites and skipped the Hamon pool candidate
because Hamon was already the baseline implementation. Its raw outputs and rejected attempts
remain intact. No scientific eligibility or repair limit was relaxed.

Read-only reports reconstruct exactly. Local stop was verified, no reservation remains pending,
and the temporary lease was removed. This attempt charged 17 host calls, two public reservations
and 39 measured starts, taking cumulative usage to 77 host calls, ten public reservations and
133 measured starts. The approved 208 ceiling leaves 75 measured starts. Closed evidence was
copied to `outputs/campaign-part3-probe-fix-20261027/`, an ignored, private local archive. All
8,444 files were hashed, and all four copied runtime reports reconstruct exactly. Its manifest
SHA-256 is `3cca99f5011c315a790afbcb2167e48f7988c3d25b377eef532ad3366e4e3933`.
It contains no credential file. No source, result, failed gate or timestamp was rewritten.

## Shared proposal prerequisites and explicit canonical progress

Role-output contract 1.3 describes proposal prerequisites separately from downstream calibration,
evaluation, checks, acceptance and confirmation. Single-agent template 1.3 carries the same
clarification already present in the investigator template. Missing source/interface prerequisites
still block. The common matched summary now includes proposed candidate IDs, the exact next
proposal ID and `baseline_counts_as_proposal: false`. Both routes receive these fields. The
proposal schema and existing parser bind the expected candidate ID. The scientific candidate pool,
order, seed, validation rules and original per-route allowances remain unchanged.

The source tests passed 67 focused checks in 428.56 seconds, including both routes, every canonical
proposal and genuine missing-prerequisite rejection. An earlier restricted run could not verify
subprocess stops and failed before host dispatch. Its focused failure log is preserved; the correct
owned-process environment passes. Full default tests are running against frozen source
`3bc02bf250cfc44cf1a25eda02f078f86c986e9e76e5c5a60e35fa5cab9c72bc`.
The expanded installed run includes all 23 comparison tests, for 261 checks. Its initial collection
error was a missing Leaf River example bundle in the disposable layout. The checked example and
its declared cached source/data files were copied without download or package-code changes.

Fresh offline qualification passed with digest
`0a21145c8feb972c9a5a73afa90566a6657d85525beb857448e25811d4470df8`.
All 140 package files match wheel
`c04d5f27b52931bd6bac12cfd2350502d154100068c0f7e79051a678cdfc174f`.
A one-call actual proposal diagnostic on captured baseline context completed with canonical
`pet-hamon-v1`, no prerequisite gaps and verified full provider proof. It started no numerical
work, stopped cleanly and its lease was removed. Cumulative host charges are now 78, with public
reservations still ten and measured starts still 133. A captured full evaluation/self-review
context with bounded actual history produces 61,567 wire bytes, below the 65,536 limit.

A fresh matched preparation is under `part3-proposal-context-20261027/fresh-study/` in
`/private/tmp`. Its conformance digest is
`aea11ae40bdb70d2d3ac5340137d3c85eef02aaad54fa53cc3a98ef018379a5d`, and comparison digest is
`e00fecc7f8c1a6fa9fd1a8fdb7bbb2990aab4564a87bc1d8e05ad20fa52a2c5c`.
It needs 114 fresh starts while only 75 remain. The proposed cumulative ceiling is 247, requiring
39 additional numerical slots. That increase is not authorized. Payload/account/model approval
remains in force. No new numerical authorization file, lease or live runtime was created.

Final proposal-context verification passed: 1,454 tests with 65 skips in 1,210.32 seconds.
JUnit confirms zero failures/errors, all 3,334 source files unchanged, all eight canonical-order/
prerequisite negative cases, the complete common-context/replay test and the existing named
verification matrix. The corrected disposable example layout passes all 261 installed checks
in 616.04 seconds. It includes every declared audit/model/scientific input, with 88 source/data
files verified byte-for-byte. Both earlier missing-input results remain preserved separately.

All twelve mock operator fixtures pass, including missing payload consent, missing numerical
approval, wrong numerical increase, changed source, withdrawal and exact packet/budget checks.
They read no real credential, make no provider request and start no numerical work. Packet
`51c164c22488348e503c178b52ba6f2b36d76d6df81c6119e1cc27556672e640` is ready for the
39-slot numerical decision. It retains prior 133 measured starts and proposes a ceiling of 247.
No actual new-budget authorization, lease or runtime exists. Payload/account/model approval
remains valid; no further ChatGPT-call permission is requested.

The final verification and pending-study packet are also preserved in the private ignored
archive `outputs/campaign-part3-proposal-context-20261027/`: 509 files, 10,565,932 bytes,
manifest SHA-256 `3520e19968a67df74cca7a12e03b3c7dc6156f14e2e29ea64126cc976baf3078`.
The packet digest matches the executable preparation, and the copied diagnostic provider
proof reconstructs. No credential file or new numerical authorization was copied. Both local
archives are evidence snapshots; they do not grant execution or publication authority.

## Approved 39-slot continuation

The user replied "approved" to the pending 39-slot numerical increase. Packet
`51c164c22488348e503c178b52ba6f2b36d76d6df81c6119e1cc27556672e640` is executing with
all prior charges retained: 78 host calls, ten public reservations and 133 measured starts.
The cumulative measured ceiling is now 247, providing 114 starts for this fresh matched study.
No scientific criterion, candidate order, fitting seed, data exposure or per-route limit changed.
The actual approval file binds the reviewed packet; no further payload/account/model approval
was requested. Current-source actual conformance passed all six cases, and the conditional
matched comparison has started. Current-source and installed checks remain 1,454 passed with
65 skips, 261 passed respectively. No production source changed after verification.

## Final accepted bounded delivery

All six current-source conformance cases passed. The actual three-route comparison then passed:
38 measured starts each, no repairs and no trusted review override. Scripted used zero provider
calls and 91.21 case seconds. Single-agent used seven provider responses plus one charged local
interruption, in 172.80 seconds. Four-role used thirteen provider responses plus one charged
local interruption, in 243.46 seconds. Both native interruption controls passed without scientific
restart. All invalid-unit controls rejected before numerical execution.

All routes selected Hargreaves with capacity 52.2937985509634 and recession 0.9148484857752919,
RMSE 3.1378289080395643. Selected NSE remains -1.2354999304967524 and KGE -0.12377987304518712.
Relative acceptance does not establish absolute predictive skill. The role split added observed
calls/time without objective gain in this development case. No independent confirmation occurred.

The final execution charged 35 host invocations and 114 measured starts. Cumulative usage is
113 host calls, twelve public reservations and 247 measured starts. The numerical ceiling is fully
used. All 114 fresh measured costs are known unit costs, with distinct attempts and three distinct
scientific identities. Prior failed matrices and earlier unknown public/host costs remain retained.
No work is pending. Both supervisors stopped, reports reconstruct exactly, and the temporary
lease was removed without reading it. No server revocation or zero human effort is claimed.

The new closed live archive `outputs/campaign-part3-approved-comparison-20261027/` contains
6,364 files and 166,986,819 bytes. Its manifest SHA-256 is
`65a7d8264993ea419bad3628b71c1cdb3c8a242ca527a240bbc939e6448d8836`. Both copied reports
reconstruct exactly. It contains no credential file. Earlier failed and verification archives
remain unchanged. A genuine private target installation of the verified wheel also succeeded,
with all 140 package files identical. Its generated CLI entry point exposes all six commands and
reports the archived four-role worker completed, without provider or scientific work, dependency
download or global environment change.

The final audit maps the original scope, seven increments, named verification matrix, current
platform/source pins, complete results and deferred/not-attempted scope. Guides, example README,
documentation index and development-plan status are updated. No production source changed after
verification; no commit, push, merge, release or deployment was performed.
