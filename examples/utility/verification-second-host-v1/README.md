# Claude transport foundation verification

The implementation is `src/autoengineering/agents/hosts/claude.py`, primitive
version 1.2. It is not an admitted scheduler Host. Existing host records, capability
records, scheduler dispatch and qualified Codex admission are unchanged. The next
increment must supply the actual boundary/profile and truthful host integration.

The transport pins the CLI version/executable and non-secret helper code. Its
fixed bare command requests disabled tools, skill commands, dynamic MCP/settings
and session persistence. A caller-owned OS wrapper must preserve that complete command. The
helper hash verifier is embedded in the persisted command. No API key enters a
process environment, command or public job. Real authentication and the actual OS
boundary were not exercised here.

JSON mode requires one structured result, with no prose fallback. Subtype alone
cannot establish success. Invalid/error/denied/incomplete responses retain bounded
raw bytes and available metadata. Missing/multiple/wrong model metadata cannot
complete a handoff. The supervisor owns process limits, stop proof and saved
completion recovery. The caller must reserve the invocation and durably bind the
original job before command release. Tests cover owner loss before release and
after completion was saved.

Per-model token categories supply whole-call normalized counters. All categories
must be present for usage_complete. Missing model counters never fall back to the
potentially incomplete top-level usage. Crash zeroes become unknown normalized
work. Top-level counters remain separate diagnostics. SDK dollars are explicitly
estimated_cost_usd, with billed_cost_usd unknown. They are not settled charges or
a hard actual-billing cap. Primary source URLs and access limits are recorded in
primary-sources.json. No schema is inferred from a requested model name.

Focused new/existing transport, record, scheduler and process checks passed 112
tests. Documentation checks passed 19 tests and lint passed. The earlier full
base/Bayes suite results apply to the pre-module source snapshot, not these later
bytes. The installed final fixture result is recorded separately. All actual
execution in these tests uses authored local executables and synthetic key
canaries. Installed CLI probes were version/help only, including explicit empty
option syntax. No actual Claude inference, API authentication, account query or
real credential read was requested.

Initial adverse results remain. Empty argument options were rejected by the
shared supervisor. Explicit equals syntax fixed this without relaxing supervisor
validation. Source/log copies before the cost-estimate and model-usage corrections
are retained. Earlier installed wheels remain in separate temporary roots.

The local wheel contains every current core Python source byte. A fresh temporary
venv uses resolved cached base dependency paths without editable activation. It
has no Anthropic SDK. Its Python startup policy denies original-checkout opens
and sockets in the parent and ordinary Python children. The fixed helper verifier
uses isolated Python and executes only its pinned helper. This audit policy is
not an OS privacy boundary and does not qualify arbitrary untrusted programs.

To repeat focused checks from the repository root:

```sh
PATH="$PWD/.pixi/envs/default/bin:$PATH" .pixi/envs/default/bin/python -m pytest \
  tests/test_agent_claude.py tests/test_agent_codex.py tests/test_agent_contracts.py \
  tests/test_agent_scheduler.py tests/test_agent_process.py -q -p no:cacheprovider
```

Installed-check scripts require new absent temporary output roots. Do not overwrite
previous runs. No live run command is provided by this foundation. Complete the
second-host implementation increment and prepare the exact conformance package
before requesting live authority. All independent data/privacy/platform/cost and
scientific utility gates remain open.

Adding a host module changes the aggregate host source identity. Existing records
retain their original serialization, but an earlier live configuration still binds
its original source snapshot. Use that snapshot or obtain fresh qualification.
Do not rewrite old pins, relabel observations or resume an old run with new source
and a fresh allowance. source-identity-change.json records this increment's hashes.
