# Current v6 frozen inference and native parity

The production `GuestRoutingExecutor` completed one frozen learned-routing
inference in the installed v6 image. All four physical checks passed and the
original container was confirmed absent, including a separate read-only GET.
The lifecycle took 1.7852 seconds. The model reported 0.0194 seconds. These are
individual observations, not speed or predictive-skill claims.

A separately reserved native reference used the same frozen fit, seed, drivers
and axis. All seven outputs passed the unchanged symmetric tolerance
`abs(native - guest) <= 1e-10 + 1e-12 * max(abs(native), abs(guest))`.
The largest difference was `2.1316282072803006e-14`. Prediction JSON differed
numerically while model, partition and selection metadata agreed. No new fitting
or scoring occurred during either inference.

The old exposed fixture commits to earlier core bytes. The preparer now checks
its core and model-source commitments against the wheel before output creation
or driver access. The old fixture refused without a new fit or guest start.
It remains preserved. Tests cover missing, changed and resized core/model code.

A separate current-source development fixture used one supervised fit and one
baseline evaluation over authored synthetic inputs. The fit completed 27 routing
rollouts and 2,160 routing days within a 120-rollout cap. Its fit hash is
`fe8ce1bef4cdda09f2a29b99fcabaa6d9e28898a5e40d70ce158580f2d33a67b`.
The baseline report retains its unknown physical science-start quantity. The
fixture builder uses test helpers and an authored owner template. That template
makes no OS claim. The actual inference required separate v6 identity/resource
proof and replaced the template's guest metadata. This is a development control.

Two launch-path refusals and one post-fit diagnostic metadata error are retained.
The metadata error occurred after fitting and freezing. Saved metadata recovered
without refitting, a repeated evaluation or a repeated guest start. The executed
creator, failed archive helper and separate metadata recovery scripts are saved.

[Summary](summary.json), [request](request.json), [completion](complete.json),
[fit accounting](fixture-accounting.json), [absence check](post-run-absence.json)
and [public proof](public-proof.tar.gz) preserve the evidence. The public archive
has 98 files (see its [manifest](public-proof-manifest.json)). Its only NPZ is the
model output. Source/driver directories and fitting/comparison labels are absent.
A fresh process recovered the relocated proof with model imports blocked from
startup. After metadata initialization, guards denied execution, array loading,
network, clocks, writes and outside file reads. Dependencies were inherited.

The [native/guest saved proof](parity/complete.json) also recomputed after
relocation with process, network, write, outside-read, import and clock guards.
Imports and numerical dependency initialization preceded that guard. Neither
reader independently attests the operating system or reimplements the physics.

Inference request digest:
`32c684a294150b67f21f23821227b38513a8a454b94cd201225b209d5f09c706`.
Inference completion digest:
`b35b3b180caa3396857f37f1929be3b79fd7678cde71184f9acae5c65585bddc`.
Native parity completion digest:
`d6feb256c08824c15adc2ba12b8d761e80a22f44c3185cfa17dd616391cd7aa4`.

```sh
pixi run python -m examples.utility.guest_parity_reader \
  examples/utility/verification-guest-inference-v6/parity \
  --expected-digest d6feb256c08824c15adc2ba12b8d761e80a22f44c3185cfa17dd616391cd7aa4
```

The host was local OrbStack Linux amd64 emulation on macOS ARM64, with a native
macOS ARM64 reference. It was not an independent physical x86 host. The composite
grant reserved two scientific starts but attempted only inference. Scoring and
parent confirmation remain incomplete. Current-image lifecycle/private controls,
independent task admission, the full matrix and Part 5 completion remain open.
Cumulative explicit runtime accounting is 38 creations, 32 starts and two native
references. Older unknown work and label quantities remain unknown.

The related regression passed 210 tests in 198.80 seconds. Documentation passed
19 tests. Ruff, changed-file formatting and whitespace checks passed. The frozen
v6 wheel still aligns with all 316 declared code sources. All 308 original fixture
file hashes remain unchanged. The full default checkpoint predates this example
helper/test change and was not rerun. No core source changed in this increment.
