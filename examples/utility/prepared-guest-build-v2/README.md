# Corrected local image-build request

This request was approved and consumed. Plugin discovery worked, but its
endpoint check rejected Buildx's `default` alias. No pull or build ran. See the
[v2 outcome](../verification-guest-build-context-v1/failed-attempt.json).
The original request, runner and bindings remain unchanged. The
[latest proposal](../prepared-guest-build-v4/README.md) adds verified context and
base identity handling and needs approval. The scope below records this original proposal.

Request digest:
`4b292a07a2161f2acb68d08785db6a5c83fd5ef0e17fc06914dbbda6d901eaf5`.
The verified context remains
`0e523c9b2dd0cc9bbc01bea14b185db87f14e982a495f5960b1c082804df2cce`.
The pinned base, 50 verified archives and six Docker commands are unchanged.

V2 also pins the existing Buildx executable. OrbStack's Docker and Buildx entry
points resolve to the same 74,041,344-byte installed binary, SHA-256
`4a728ee98f89005a90198a9be791e8fdaebbcb5e6af9721251efe0113df37759`.
Execution stages a verified copy in the job's private plugin directory with
mode 0500. Every command verifies original and copied bytes. The configuration
stays empty, excluding ambient contexts, builders and credentials. Saved readers
check the copy without its original path. No binary is bundled in this proposal.

The [verification record](../verification-guest-build-plugin-v1/README.md) includes
101 related checks, lint and actual installed Buildx help from a fresh private
configuration against an absent daemon endpoint. No image operations ran.

The proposed job reads daemon/builder metadata, pulls one pinned Linux amd64
base, attempts one local build and inspects the resulting image. Compressed base
layers total 45,269,741 bytes. Transfer overhead and retries are not bounded by
that payload count. Existing archives install offline within the image build.
No push, model, provider, training, scoring or independent-label access is allowed.

One 1,200-second client deadline includes plugin staging and all six commands.
Each command log is capped at 16 MiB. Requested build-step settings remain 2 GiB
memory, the same total memory-plus-swap cap and one CPU, subject to daemon support.
Disk is not quota-enforced. Client termination does not prove daemon cancellation
or owner-loss cleanup. No automatic retry or renewed allowance is allowed.

The original `outputs/guest-image-build-v1` remains preserved. The proposed
`outputs/guest-image-build-v2` remains absent. Private paths are in ignored
`bindings.json`. If separately approved, the exact command is:

```sh
pixi run python -m examples.utility.guest_image_build execute \
  examples/utility/prepared-guest-build-v2 \
  --expected-digest 4b292a07a2161f2acb68d08785db6a5c83fd5ef0e17fc06914dbbda6d901eaf5
```

The [runtime plan](../../../docs/implementation-plans/part-5-frozen-prediction-increment.md)
requires separate assembly authority. V1 forbids an automatic retry or new
allowance. This proposal does not authorize execution. Assembly would produce
an unqualified candidate image only.
