# Derivative image environment and provenance

The new image passes the existing strict image-metadata check. It copies the
verified original filesystem into a scratch final stage, sets exactly seven
environment entries, and adds the required purpose, environment and wheel labels.
Core source, receipt policies and the frozen runtime wheel are unchanged.
Docker documents [copying between stages and local images](https://docs.docker.com/build/building/multi-stage/).

Image `sha256:516cb2702eb45d99264dc90622fea8de4de987f68b4266ba8c86da4c312390de`
built in 29.9822 seconds on the local ARM64 OrbStack host. Inspected size is
440,613,645 bytes, not measured physical disk use. The fixed recipe has no RUN,
package installation or host-file copy. No pull or push command was issued.
Nine clients, one unique local source tag and one build share a 1,200-second
deadline. Disk quota, resource-flag enforcement, daemon cancellation and total
registry transport remain unqualified or unmeasured.

V1 completed four read-only clients, then the API transport refused its tag-check
deadline before sending the GET. No tag or build was attempted. It remains
consumed. V2 bounds that read-only check to ten seconds within the original build
deadline. [Completion](complete.json), [build log](06.log), [final inspect](07.log)
and both executed source snapshots preserve the evidence. The later reader also
checks the source digest resolved in the saved build log. Machine bindings and
executable client copies remain in ignored local work.

One subsequent metadata container observed Linux x86-64 CPython 3.12.13,
UID/GID 1000, package 0.2.0 and the expected installed identity source. It completed
in 5.8893 seconds and its original container was confirmed absent. See
[identity completion](identity/complete.json) and [profile](profile.json).
All 315 declared wheel sources, including 224 core files, still match current
declared host sources. New host helpers are outside that frozen wheel's source set.

Fresh guarded processes replayed the image completion from 41 relocated files
(178,952 bytes) and identity from 12 files (117,131 bytes). After imports, guards
denied outside file-content reads, writes, imports, processes, sockets and clocks.
Dependencies were inherited. See [image scope](cold-image.json) and
[identity scope](cold-identity.json). This is source-based metadata replay, not
installed-package qualification or independent OS attestation.

```sh
pixi run python -m examples.utility.guest_image_environment verify \
  outputs/guest-image-environment-v2 \
  --expected-digest 008aa6f0d4c850548cbc5c8ecd173ce1a031679d7d3151b9a961d8ff3331afe0
pixi run python -m examples.utility.guest_identity verify outputs/guest-identity-v2 \
  --expected-digest 332206006452b9f4291cd6608093729249500d43bde08bcfaba78ec0961a7e30
```

No model, fitting, scientific label, score or provider work ran. The original
image's resource evidence does not qualify this derivative. Its resource,
inference and lifecycle controls, private scoring and independent scientific
admission remain open. Both build requests and the identity request are consumed.

The final related regression passed 285 tests with no failures, errors or skips
in 39.82 seconds. Ruff and `git diff --check` passed. These tests use authored
fixtures and owned local subprocesses, not an admitted confirmation matrix.
The intermediate bound-check name collision and preceding 281-case result are
preserved separately. See [final output](final.log), [JUnit](final.xml),
[command](final-command.json) and [collision reproduction](bounds-name-collision.log).
The full default checkpoint was not rerun for this host/example increment.
