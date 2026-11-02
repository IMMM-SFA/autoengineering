# Local image build with explicit context resolution

This request was approved and consumed. Metadata checks passed and the pinned
base was pulled. Validation then rejected its manifest-based image ID before
the build command. The base and original proofs remain preserved. See the
[v3 outcome](../verification-guest-build-base-v1/actual-base-verification.json).
The [v4 proposal](../prepared-guest-build-v4/README.md) verifies the manifest/config
relationship and needs new approval. The scope below records the original proposal.

Request digest:
`d9bd15a3f74b84126ca6b1d00e487b841350895be1225653952ee6946ca0b759`.

V3 adds one read-only context-inspection command before builder inspection.
The alias is accepted only after `context inspect default` reports the exact
pinned Unix endpoint. Other aliases and remote or changed endpoints refuse.
Legacy requests retain their original endpoint checks. The plugin remains
explicitly pinned and staged in the fresh private configuration.

All three metadata preflight commands passed in separate read-only diagnostics
against the pinned local endpoint. See the
[verification record](../verification-guest-build-context-v1/README.md).
Those diagnostics did not open a new build job or perform image operations.

The context remains
`0e523c9b2dd0cc9bbc01bea14b185db87f14e982a495f5960b1c082804df2cce`.
The base, 50 archives and plugin bytes are unchanged from
[v2](../prepared-guest-build-v2/README.md). The seven commands read daemon metadata,
resolve the context, inspect the builder, pull one pinned Linux amd64 base,
inspect that base, attempt one local build and inspect the resulting image.

The same 1,200-second client deadline covers plugin staging and all commands.
Logs remain capped at 16 MiB each. The base has 45,269,741 compressed layer bytes,
which is not a wire quota. Requested build-step limits remain 2 GiB total memory
with swap capped to that same total and one CPU, subject to daemon support.
Disk has no enforced quota. Client termination does not prove daemon cancellation
or owner-loss cleanup. No automatic retry or renewed allowance is permitted.

`outputs/guest-image-build-v3` remains absent. Earlier work is preserved.
No model, provider, fitting, scoring or independent-label access is authorized.
An assembled image would remain an unqualified candidate. If separately approved:

```sh
pixi run python -m examples.utility.guest_image_build execute \
  examples/utility/prepared-guest-build-v3 \
  --expected-digest d9bd15a3f74b84126ca6b1d00e487b841350895be1225653952ee6946ca0b759
```

The [runtime plan](../../../docs/implementation-plans/part-5-frozen-prediction-increment.md)
requires separate assembly authority. The earlier requests forbid automatic
retries or new allowances. This proposal needs new approval.
