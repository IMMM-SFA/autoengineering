# Prepared API lease and fixed upstream evidence

Status: verified development increment. Production host admission and actual
provider conformance remain open. All credentials in these checks are authored
fixtures. No real key, provider call or independent scientific partition was used.

`anthropic_lease.py` reads only an explicitly named private raw-key file into a
fresh private lease directory. It reserves the destination before reading, refuses
reuse, binds a declared local expiry and keeps the source unchanged. It rejects
Git/client read scopes, unsafe files, changed bytes and invalid key/workspace
syntax. Its public receipt contains neither key nor key hash. Preparing a lease
does not verify server validity, actual key expiry or refresh credentials.

`ScopedAnthropicUpstream` supplies a fixed isolated Python command to the existing
owned-process supervisor. Its worker pins the sibling transport helpers, API
version 2026-10-21 and api.anthropic.com:443/v1/messages. It validates the rebuilt
request before opening the lease. Native client headers and metadata never reach
this interface. It requires certificate/hostname verification and TLS 1.2 or later,
with no proxy discovery, redirect, retry, credential refresh or auth fallback.

Send intent precedes the possible request. Only complete bounded valid JSON is
persisted. Conflicting framing, invalid encoding, incomplete bodies and literal
or JSON-escaped credential reflections fail without saving response bytes.
Error response bodies and headers are discarded. Public status records use static
reasons. Usage remains unknown at this transport layer. The exchange separately
validates the handoff and records reported usage. Local process termination never
claims that provider work stopped.

The shared private reader now opens the leaf with O_NONBLOCK before checking its
descriptor type. A FIFO cannot hang while waiting for a writer. Descriptor-based
directory traversal, O_NOFOLLOW, ownership, private modes, single links, size and
unchanged-file checks remain in force.

## Observed checks

- Final transport regressions: 299 passed in 21.26 seconds. The command covers
  new API lease/worker/upstream/TLS checks and existing exchange, endpoint,
  Claude, command supervisor and subscription transport contracts.
- Exact isolated production commands refused missing and FIFO leases before
  send intent. Their local stops verified. Reuse/recovery added no launch.
- A separate test shim routed the isolated worker to an authored loopback TLS
  server with an ephemeral fixture CA. One request completed. Removing the
  synthetic lease did not affect original-byte recovery or add a second request.
  Production command verification rejects this shim. It is not an admitted
  production request or OS privacy qualification.
- Untrusted certificates and wrong hostnames sent no HTTP authentication.
- Installed wheel: all 187 core Python files matched source bytes. Its SHA-256
  is recorded in wheel.json. Fifty-two installed cases passed with original
  checkout opens, all sockets and subprocesses denied. Six separate installed
  TLS/process cases passed with loopback TCP and fixed fixture processes allowed.
  Explicit guard checks confirmed denials. The Python audit hook covers the test
  parent and is not inherited by isolated children. These checks do not qualify
  a production OS boundary.
- Ruff and git diff whitespace checks passed. Cached base dependencies were
  reused without editable activation. The Anthropic SDK and optional scientific
  packages were absent. This was not a fresh minimal dependency solve.

Initial logs are preserved. The first two worker test failures expected the wrong
reason for duplicate/nonfinite JSON. The implementation already refused it. A
later owned-worker test failed because its privacy assertion tried to read a
process directory as a file. The corrected assertion scans all regular nested
evidence files. The final run passed after these test corrections.

Source identity: 5996c60747b6a39355a994d2cd7cf7b830c7088151f2640f05fd9770cf1a00ae.
final-source preserves the eight changed source/test files. The prior 2016-pass,
106-skip full default run belongs to the preceding b595972d source snapshot.
It does not cover these added modules or the private-reader change. Focused
regressions cover the changed contracts. Earlier qualification pins stay unchanged.

## Remaining work

The API profile is provisional pending the operator's authentication preference.
No API key discovery or real credential read is authorized by this increment.
Full credential/runtime/privacy/resource qualification, truthful host records,
scheduler/factory/cost integration and an explicit live conformance package remain
unfinished. HostSelection still admits only the existing fake/Codex profiles.
Subscription authentication requires a separate implementation and qualification.
Independent data/custody, private scoring, Linux x86-64 and the full Part 5
protocol, comparison and analysis gates remain open.
