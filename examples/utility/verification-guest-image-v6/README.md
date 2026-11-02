# Current-source image and interpreter evidence

The v6 base image assembled the unchanged 49 locked runtime archives and current
316-source wheel. The environment-only derivative copied that filesystem into a
scratch final stage and set the complete approved environment and provenance
labels. The two builds and one source tag are separate from runtime container
accounting. The derivative performed no install or download.

The [summary](summary.json) records the exact image identities and completion
pins. The current image is a local Linux amd64 candidate under OrbStack emulation
on macOS ARM64. It is not independent physical x86 hardware.

One metadata-only container observed isolated Linux x86-64 CPython 3.12.13 and the
expected installed identity-module bytes. It completed in 6.0415 seconds. Cleanup
recorded the exact original container absent. Its profile remains
`unqualified-candidate`. No fitting, inference, scoring, private label or provider
operation ran in this increment.

Three [guarded readers](cold-results.json) reconstructed the saved base build,
derivative and identity records with live clients, daemon access, network,
processes, imports, writes and clocks disabled after initialization. Derivative
and identity evidence was relocated outside the checkout. The base verifier used
original local evidence because it also verifies the saved 74 MB plugin binary.
That binary is not redistributed in this source archive. Changed identity cleanup
metadata was refused. Original evidence and source pins were not changed.

The `build/`, `environment/` and `identity/` folders are compact metadata/source
snapshots. Python source snapshots use `.py.txt`; replay helpers require their
original `.py` basenames in a reconstructed data scope. The original complete
scopes are `outputs/guest-image-build-v6`, `outputs/guest-image-environment-v6` and
`outputs/guest-identity-v6`. The executed readers and scope preparation are saved
alongside the results.

The [cumulative register](../guest-qualification-accounting-v8.json) now retains
31 explicit runtime container creations and 25 starts across its listed operations.
BuildKit internals are excluded. Earlier uncertain inference and label-access
quantities remain unknown. Historical controls do not qualify the new image.
Current-image resource, inference, lifecycle and private-scoring qualification
remain open, along with task admission and the independent Part 5 comparison.

The full [default checkpoint](../verification-current-base-v6/README.md) finished
with one launcher-PATH failure. Exactly that case passed with project child PATH
and unchanged source. Its original nonzero full-run result remains preserved.
