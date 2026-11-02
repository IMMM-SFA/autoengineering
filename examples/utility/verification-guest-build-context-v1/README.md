# Default-context resolution

The approved v2 job reached two client commands. Both exited successfully, but
builder validation rejected the printed endpoint name `default` because v2
required a literal Unix URI. No pull or build ran. The
[original outcome](failed-attempt.json) and copied original proofs remain here.
The consumed job was not retried or relabeled as successful.

Read-only inspection then showed that the default context resolves to the exact
pinned local Unix endpoint. Request v3 now performs that check before accepting
the alias. A changed context name, remote endpoint or other alias refuses before
image acquisition. The Docker driver and amd64 capability checks remain intact.
Legacy v1/v2 replay retains its original command lists and endpoint rules.

All three metadata preflight commands passed against the actual local endpoint.
[Saved observations](actual-preflight.json) retain output hashes and the checked
endpoint digest. The context projection omits the private absolute socket path.
Raw daemon-version and builder outputs are retained. These diagnostics performed
no image operations and did not reopen either consumed job.

The [new request](../prepared-guest-build-v3/README.md) remains unexecuted.
The final related regression passed 105 tests with no failures, errors or skips.
Repository lint passed. Tests include wrong-context and remote-endpoint refusal,
actual alias formatting, immutable legacy command lists and endpoint rules,
plugin drift and offline replay. These regression runs use authored Docker
responses; the actual three-command diagnostics are recorded separately.
The administrative helper and tests postdate the full v5 default checkpoint.
Core source and frozen guest inputs are unchanged. Runtime/privacy and independent
scientific qualification remain open.
