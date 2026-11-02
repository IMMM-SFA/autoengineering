# Native Claude loopback development evidence

Status: a synthetic local roundtrip passed. No provider, scientific model, real
credential, utility matrix or independent partition was accessed. Production
admission remains false. This is progress toward the second-host boundary, not
completion of G6 or actual LLM role conformance.

## Measured scope

The final v7 probe ran Claude Code 2.1.310 under policy version 1.4. Its native
apiKeyHelper hook ran the pinned verifier and authored helper through the macOS
shell. One authenticated request reached an authored loopback HTTP peer. The peer
returned fixed Anthropic-format stream events. Claude completed with structured
output and the owned process stopped. Its model name is a fixture label in this
probe, not evidence that any model ran. Token counters and the client's dollar
estimate derive from authored peer events and are not measured provider work.
Billed cost remains unavailable.

Claude's internal JSON-schema mechanism requests the StructuredOutput pseudo-tool
even when user tools are disabled. The final parser accepts its tool_use stop only
with explicit terminal_reason=completed, successful status, a nonempty structured
payload and the existing error/permission/tool/model checks. Plain text still fails.
The actual native result from v6 is a parser regression fixture in tests/fixtures.
The fixed transport settings accept only an integer loopback port, never an
arbitrary URL or credential. Secrets remain forbidden in the shared supervisor's
environment. Its sole new variable, CLAUDE_CODE_TMPDIR, must equal the explicit
HOME. Both ordinary TMPDIR and the Claude override point at the isolated home.

Policy 1.4 adds only the observed public shell launcher, its bash delegate and
selector to the previous runtime grants. The public shell hashes and selector
metadata are in public-shell-inventory.json. It does not grant /bin as a tree.
The final v7 policy probe separately passed all 14 syscall checks, native help and
direct synthetic helper startup on the same host source identity:
8402762a4b9dbbb4292a08e502997a8d54e5ffd6418153825a8a41fbe5eaf07f.
These two probes retain separate observations and output roots.

## Preserved attempts

- Native v1 failed before helper launch because internal temp creation targeted
  /tmp/claude-501, outside the policy.
- v2 showed that TMPDIR alone does not move this macOS internal directory.
- v3 used the documented CLAUDE_CODE_TMPDIR override. It then exposed a denied
  /bin/sh spawn. No peer request occurred.
- v4 allowed that launcher, which exposed its denied /bin/bash delegate. The peer
  rejected three unauthenticated requests. No upstream exists in this probe.
- v5 ran the native helper and sent two authenticated requests. The text-only peer
  response did not satisfy structured output. The parser rejected it.
- v6 returned the StructuredOutput event. Native execution completed, but the
  previous parser rejected its terminal tool_use stop. Raw bytes are retained.
- v7 passed with the strict explicit-completion parser correction. Exactly one
  authored-peer request and one stopped native process are recorded.

Policy v6 retains the intermediate shell-only source scope. Policy v7 uses the
final launcher/delegate grants and parser source. Earlier v1-v5 policy evidence is
in verification-claude-policy-v1. archives.json pins every new archive. Only
regular file bytes were copied. Symlinks/sockets remain exclusion metadata. Original
absolute paths are provenance and are never followed by offline readers.

## Reconstruction and checks

From the repository root:

```sh
pixi run python scripts/verify_claude_loopback_archive.py \
  examples/utility/development/claude-loopback-v7 \
  --index-sha256 e558989c33097a7547cd1f8025a2aa5867ace6365c6db859137c4c6a2813f3eb
```

The reader verifies all indexed bytes, original job and completion hashes,
identity/watchdog stop receipts, the fixed local endpoint and helper code,
retained request and native structured result. Authentication matching remains a
trusted peer attestation, not something inferred from a request body. Inspection
queries no original paths or live processes and cannot grant host admission.
Eight reader regressions passed, including changed bytes and contradictory
request/model/helper/auth/stop/admission records. The initial standalone import
failure was corrected with package-aware imports.

A fresh wheel matched all 181 current core Python files exactly. Outside the
checkout, 100 authored transport/policy/archive tests passed with startup guards
blocking checkout opens and sockets. A separate read of the actual final native
and policy archives also blocked subprocesses. Optional scientific packages and
the Anthropic SDK were absent. Cached base dependencies were reused without
editable activation. This is not a minimal dependency solve or OS isolation.
The fixed helper verifier uses isolated Python and bypasses sitecustomize.

The initial installed v1 setup used an unresolved Pixi interpreter path. Its guard
rejected standard-library imports through the checkout symlink. That failure is
retained. Installed v2 uses the resolved interpreter, a fresh virtual environment,
explicit private reader path and python -P. It reuses the same verified wheel.

All 15634 previously pinned files in the original four-family development study
remain unchanged. None of these process/request counts belongs to that matrix.
The broad agent regression run passed 939 tests in 1175.53 seconds on fixed core
source. Its terminal receipt retains the exact collection scope. Previous full
default/Bayes suites retain their earlier source scope. No frozen matrix was rerun.

## Remaining requirements

A production Anthropic broker, true host records/admission and scheduler/factory/
cost joins remain unfinished. The broker must retain real provider credentials
outside the native client, reserve upstream attempts durably, validate complete
responses before delivery and preserve unknown/failure/recovery accounting.
This diagnostic peer has no upstream and cannot supply that implementation.

Actual role/lifecycle/resource/workspace/privacy qualification remains open,
including preferences/shared memory, process environment, IPv6/UDP and DNS/TLS.
Real authentication, actual model calls and Linux x86-64 are unqualified. A concrete
live conformance package and explicit authority are still required. Independent
task data/custody, a qualified private scorer, full costs/effort, the frozen protocol
and final paired analysis remain separate Part 5 requirements.

## Native lifecycle closeout

Four additional probes each reached one authenticated authored-peer request:
timeout, cancellation, output-limit termination and completed original-job replay.
Every native process group stopped. Original-job recovery reproduced each saved
status. Completed replay retained the same process, parsed result and job digest
and added zero peer requests. lifecycle.json pins their separate raw archives.
Reported errors/outcomes were not replaced with successful handoffs.

A further active-owner-loss probe killed only its owned supervisor after the local
request. The independent watchdog recorded owner_lost and verified the group stop.
The original completion was absent. Recovery refused and added zero jobs. The
native outcome remains unknown_owner_loss with no handoff.

The saved-completion window uses a different probe. Its caller persisted the
original nonce/model/job digest before release, then exited after the supervisor
saved completion and before a caller report. Recovery used that prelaunch binding,
read the original structured result and verified its stop without another job.
owner-loss-archives.json pins both windows. These are native synthetic-peer checks,
not a production admission/profile or LLM role test. Remaining full qualification
includes integration, resource/workspace and privacy/permission checks.

The lifecycle probe's later versions add request-observation receipts, prelaunch
caller binding and explicit fault windows. Earlier source versions remain beside
their outputs. The installed 100-test package and its readers retain the source
scope in installed-summary.json. No installed lifecycle-probe rerun is claimed.
