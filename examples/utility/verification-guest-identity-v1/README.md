# Actual Python identity discovery

The fixed metadata-only probe completed in 9.8228 seconds with one observed
container start. Its client exited zero. The original container ID was captured,
and cleanup observed it absent. No model, fit, label, provider or scoring work ran.
The image was cached and the request prohibited pulls and host mounts.

The guest observed Linux x86-64, isolated CPython 3.12.13, UID/GID 1000 and package
0.2.0. Its installed identity-module bytes matched the frozen wheel manifest.
The Python build digest is
`b045b35133aee229f091997de805d765ccda1c386ba6b0802f6534008f759cca`.
The image remains
`sha256:fc19692dff41a699600f76a79a97ed6cdcdf927f28e09984a79f33dcee46c399`.

[Completion](complete.json), [output](output.log), [cleanup](cleanup.json) and
[profile](profile.json) retain the observations. The profile's boundary remains
`unqualified-candidate`. Its limits describe the intended policy, not measured
resource enforcement. This probe is separate from the preserved 26-case proposal
and does not count as any of its controls.

The reader verifies the saved request, source, launch intent, result, original
cleanup allowance, output identity and profile without live calls. A fresh process
also verified 12 relocated files after initialization with outside reads, writes,
imports, processes, sockets and clocks denied. See
[guarded reader](cold-identity-reader.py.txt), [output](cold-reader.log) and
[scope](cold-reader.json). Source imports precede the guard and dependencies are
inherited. This is not installed-package qualification or independent OS
attestation. Cleanup is reconstructed from the saved producer observation.

The first broader test attempt failed in fixture setup under restricted process
permissions. A PATH-only reproduction still failed. The same unchanged fixture
passed with the owned-subprocess permissions used by the full v5 suite, and the
111-case related check passed under those permissions. All initial logs remain.
The final related guest/identity/documentation regression passed 140 tests with
no failures, errors or skips. Repository lint passed. This includes saved replay,
file-size/symlink bounds, identity mismatch, source/client drift, uncertain cleanup
and late completion. No production gate was relaxed to obtain a pass.

Report-only verification from the checkout is:

```sh
pixi run python -m examples.utility.guest_identity verify outputs/guest-identity-v1 \
  --expected-digest 653357f8bf204e3366d15d68f86c4c2f230db11409cf5f24c2f8526d7727c8d8
```

The next work is the actual diagnostic and fixed-inference control matrix.
No private runtime registration or independent scientific admission is supplied.
