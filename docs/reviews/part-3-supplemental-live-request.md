# Part 3 supplemental live request

Historical request: approved by the user, then stopped on the launcher failure described in
[the recovery request](part-3-launcher-recovery-live-request.md). The original packet and gate
records remain unchanged.
The account in `~/.codex/auth.json`, model `gpt-6.1-sol`, destination and payload scope
are already approved. No new credential lease or runtime has started.

Six calls remain charged from the compatibility failures. A fresh conformance run permits
thirteen calls across the original six cases. The conditional comparison permits forty.
Their cumulative maximum is 59, three above the approved 56. Conformance's cumulative
ceiling would rise from 16 to 19. Every failed gate and its original records remain unchanged.

| Allowance | Prior work | Proposed new work | Cumulative ceiling |
| --- | ---: | ---: | ---: |
| Host-call slots | 6 | 13 conformance + 40 conditional comparison | 59 |
| Public scientific starts | 0 | 2 | 2, unchanged |
| Measured scientific starts | 0 | 114 | 114, unchanged |
| Dispatch seconds | 360, conservatively charged | 360 conformance + 1,800 comparison | 2,520, unchanged |

The immutable inner conformance specification retains its original criteria and limits.
An owned outer supervisor restricts new conformance to the remaining 360 seconds. The
comparison starts only after the actual live conformance gate passes. There is no refresh,
model/account fallback, automatic retry, lease extension or access to new held-out data.

The fixed destination is `https://chatgpt.com/backend-api/codex/responses`. The temporary OAuth
bearer and recorded account ID enter only its authentication headers. Bodies contain the
approved role/task/output contracts, candidate configurations, aggregate scientific summaries
and permitted handoffs. Raw forcing/observation arrays and refresh tokens stay local.

The compatibility fixes handle the observed missing MIME header and inert provider metadata.
Complete stream, text, model, usage, tool, credential and process checks remain enforced.
The captured actual Sol response and sandboxed native replay pass offline. These replays do
not relabel the failed live gate. Current verification passed 1,438 full-suite tests with 65
skips and zero failures/errors, plus 171 focused tests in both source and wheel layouts.
All original native qualification groups and the unchanged generated-fixture evidence verify.

Execution inputs are under `/private/tmp/part3-sol-final-live-20261027/`. The launcher requires
a supplemental approval bound to the packet and a passing offline-verification receipt before
opening the selected credential source. Runtime roots are absent and the lease placeholder
is empty. The one-shot lease retains the existing 900-second maximum.

| Pin | SHA-256 |
| --- | --- |
| Execution packet | `da30a4d0a16b23fbbff1d763b1cf9282e82fafb9a0d2a9fcaba81861bf8249cb` |
| Native qualification | `5533596bbe49697d692c3b00814c7839afbd234ad483b80fc460676f321ea265` |
| Conformance preparation | `1b8b7a99a0e2ee3c127cdded9161d0d10c7af4d8086d262ee21405cde8120277` |
| Comparison preparation | `9e45d74b18aa750a04fb996956fc567c940a689dab76c81ddb710333c000c434` |

The original [plan, section 11](../implementation-plans/part-3-multi-agent-system.md#11-bounded-development-comparison)
requires: "Use a new output root and a newly authorized budget." Existing approval does not
increase the cumulative ceiling. Only those three additional slots need approval.
