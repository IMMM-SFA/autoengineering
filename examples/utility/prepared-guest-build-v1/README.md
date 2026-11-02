# Proposed local candidate-image preparation

This request was approved and attempted. The daemon version read succeeded, but
the second client command failed because the fresh Docker configuration could
not discover Buildx. No pull, installation or image build ran. The failed work
directory remains consumed and must not be retried. See the
[saved outcome](../verification-guest-build-plugin-v1/failed-attempt.json).
The original request, runner and bindings remain unchanged. The
[latest proposal](../prepared-guest-build-v4/README.md) needs new approval.

Request digest:
`066de0ca30b2efafdfa3cb7e5d9cebe992c07e0f1e6854e6f71352518d6fa566`.
It binds the verified context
`0e523c9b2dd0cc9bbc01bea14b185db87f14e982a495f5960b1c082804df2cce`,
the installed Docker CLI hash and an existing local OrbStack Unix endpoint.
Machine-specific absolute paths are in ignored private `bindings.json`. The
request and runner source are retained here for review.

## Proposed action and limits

The six client commands will read daemon/builder metadata, pull one immutable
Linux amd64 Python base image, verify that base image, attempt one local build,
and inspect the resulting original image ID. The base has 45,269,741 compressed
layer bytes. Actual Docker transfer overhead, retries and cache reuse are not
measured, so that number is an expected payload rather than a hard wire quota.
The 50 package/installer archives are already verified locally.

The job uses a fresh empty Docker configuration and a minimal environment. It
accepts only the default Docker driver at the pinned local Unix endpoint and an
advertised Linux amd64 platform. No remote builder, image push, secrets, SSH
forwarding, host model data or independent labels are permitted. The resulting
image has no user tag, avoiding replacement of an existing tag.

One original 1,200-second deadline covers all commands. A surviving owner stops
its owned client process group on timeout or output overflow. Each command log is
bounded to 16 MiB. Requested build-step settings are 2 GiB memory plus swap and
one CPU. Their enforcement requires daemon support and is not qualified here.
The original 8 GiB disk proposal is not enforced as a quota. Daemon cancellation
and owner-loss cleanup remain unknown when a client stops. No automatic retry,
new work directory or renewed allowance is allowed for this request.

If the build succeeds, the helper checks Linux amd64, original image ID, fixed
bootstrap, user, working directory and thread environment. It records only a
candidate image. Runtime/privacy, independent-hardware/platform and scientific
qualification remain open. A completed saved receipt verifies without the daemon,
source checkout, original context or new clocks. Partial jobs remain consumed.

## Separate authority

The [runtime implementation plan](../../../docs/implementation-plans/part-5-frozen-prediction-increment.md)
requires separate authority for installation, image assembly and execution.
Archive-only approval does not grant this action. After that separate approval,
the exact prepared command is:

```sh
pixi run python -m examples.utility.guest_image_build execute \
  examples/utility/prepared-guest-build-v1 \
  --expected-digest 066de0ca30b2efafdfa3cb7e5d9cebe992c07e0f1e6854e6f71352518d6fa566
```

The request does not run the 26-case runtime qualification proposal, inference,
scoring, fitting, providers or independent confirmation.

[Verification evidence](../verification-guest-image-build-v1/README.md) covers
fixture orchestration and the real owned Python client supervisor, not a Docker
build. [Docker's build reference](https://docs.docker.com/reference/cli/docker/buildx/build/)
describes the per-step, daemon-dependent resource flags and RUN network setting.
