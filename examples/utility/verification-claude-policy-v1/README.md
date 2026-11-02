# Claude policy development evidence

Status: limited local boundary probe. No production admission, provider call,
scientific call, real authentication or independent confirmation is claimed.

The final v5 probe ran the actual macOS kernel policy using an authored C program,
Claude Code 2.1.310 help and the transport's pinned helper verifier. All 14 fixed
observations passed their unsandboxed controls and sandbox expectations. The
synthetic helper returned only the authored fixture. This directly executes the
verifier/helper, not Claude's native helper hook. Source stayed fixed during the
probe and the 128 focused host/process/policy regressions, which passed.

The policy grants read access to the explicit worker workspace, isolated home,
Python runtime, public system runtime trees and exact helper/credential files.
Writes are limited to the isolated home. Executable paths and localhost endpoint
ports are explicit. The observed network checks cover IPv4 TCP and Unix sockets.
This profile does not yet qualify IPv6, UDP, external egress, DNS/TLS, preferences,
shared memory, process environment privacy, resource/workspace bounds, the full
lifecycle matrix, actual role conformance or Linux. It cannot admit a scheduler host.

## Preserved attempts

- v1: numeric 127.0.0.1 endpoint syntax was rejected by sandbox-exec. The Darwin
  grammar requires localhost or a wildcard. The policy now supports localhost.
- v2: all syscall checks passed, but native help failed while formatting numbers.
  Controlled diagnostics separated locale from public ICU data access. Those
  diagnostic process results are not a second full canary qualification.
- v3: explicit public `/usr/share/icu` read access let actual CLI help complete.
  The helper had not yet been exercised.
- v4: an initial Python syntax error occurred before output creation. The corrected
  probe passed syscall/help and direct synthetic helper startup. Its source identity
  precedes the missing-public-path validation fix.
- v5: final policy source with that validation fix passed the complete limited probe.

All five roots are archived under `../development/claude-policy-vN`. `archives.json`
pins their indexes. Only regular files were copied. Intentional symlinks and the
Unix socket node are described under `excluded_nodes`, without following/copying
them. Original absolute paths in jobs and policies remain provenance. No archived
program is executed during inspection. Source versions, failed logs and diagnostics
are retained in this directory.

## Offline reconstruction

From the repository root:

```sh
pixi run python scripts/verify_claude_policy_archive.py inspect \
  examples/utility/development/claude-policy-v5 \
  --index-sha256 a27811a715282977682469fe43c88a09bb60d618c82cbf76e11de7ebe6cb32ab
```

The reader verifies the caller-pinned index, every regular file's size/hash, saved
job/input/output/completion bindings, process identity and watchdog stop receipts.
It checks the fixed 14 control outcomes, exact help command and synthetic helper
output against raw bytes and report claims. It queries no original paths or live
processes. This is saved-evidence verification, not fresh stop qualification.

All 12 archive tests passed, including relocation, changed bytes, contradictory
control/report/stop/helper/help records and removal of the sandbox command. A
relocated copy also passed these tests using the earlier installed wheel and
cached base dependencies. That wheel's unchanged artifact/record utilities were
used, not a new installation of the policy module. A separate guarded read of the
actual v5 archive blocked checkout opens, sockets, subprocesses and optional
model/provider imports. `installed-reader.json` records the result. The 19 current
documentation tests and repository lint passed. Pixi's lint launcher initially
failed to acquire a sandboxed cache lock; the same Ruff command passed through the
resolved environment executable. No installation or global configuration changed.

Source hashes and predecessor inventories preserve the evidence boundary. Earlier
full default/Bayes results retain their original source scope. No frozen science
matrix or live conformance was rerun.
