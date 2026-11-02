# Annual wind custody boundary

The new [source helper](../../examples/utility/wind_annual_source.py) connects
supplied normalized annual drivers to the suite's existing confirmation access
accounting. It returns the exact in-memory type accepted by the
[annual kernel](part-5-wind-annual-kernel.md). It does not acquire weather, invoke
the kernel or register a scorer.

Trusted preparation requires empty, separate owner-private public, private and
suite directories. It must precede every suite selection event. The immutable
wind task partition must match the complete annual plan. A durable suite claim
precedes private payload writes. An interrupted preparation cannot restart at a
fresh path. Final binding publication follows all payloads and public metadata.
No existing binding, claim or payload is overwritten.

The public binding contains source/point manifest identities, exact payload byte
hashes and sizes, task/suite identities, and source/kernel code identities. It
contains no weather vectors or absolute private paths. Each private payload has one fixed
name and exactly two little-endian float64 hourly vectors. There are no arbitrary
archive members, executable entries or pickle objects. The private codec carries
no inferred raw-provider or geographic provenance. Those still require source
admission against the acquisition and selected-grid metadata.

The bound scorer identity combines callback code and the sealed source binding.
Opening requires the complete frozen suite manifest, the selected model, the
original active allocation and its committed confirmation-access event. The
helper checks the original preparation claim, unchanged public metadata and code,
and the original directory scope. It requires exact reservations named
`private_wind_reads` and `private_wind_bytes`. Both use `count` units: the latter
counts bytes. For the proposed 2012-2014 normalized inputs, one cell needs three
reads and 420,864 bytes. These are private replay costs, not acquisition costs.

A durable per-grant access intent precedes private reads. Each annual read has a
start and verified-completion record. Payload hashes, shapes, numeric domains,
time support and normalized point manifests are checked. A full-source completion
records verified reads and bytes. A corrupt or interrupted later read retains the
earlier completions, unfinished intent and complete reservation. No second source
open is permitted for that grant. Errors do not return private exception details.

The [tests](../../tests/test_utility_wind_annual_source.py) exercise the real suite
freeze/reservation/access state machine using authored driver arrays. They cover
pre-barrier refusal, missing access, changed code/metadata, insufficient read
reservations, private file permissions and symlinks, partial reads, preparation
interruption and saved score replay without reopening weather. The scorer in
these custody tests returns an explicitly authored scalar. It is not a wind
energy result. No model was executed or source acquired for this increment.

The final focused suite passed 105 tests with no failures, errors or skips.
Repository lint passed. The
[verification archive](../../examples/utility/verification-wind-annual-source-v1/summary.json)
pins source and JUnit evidence. Production core and the four blocked dossiers
were preserved. The full default suite was not rerun for this example increment.

The application still needs a scorer callback that joins this source access to
the kernel through a qualified runtime, publishes original work/score pins and
recovers without rereading weather or repeating a model. Cost/report integration
must retain incomplete work. The helper provides no OS isolation, dataset rights,
exposure attestation, geographic admission or scientific acceptance. Its binding
keeps `task_admitted` and `private_boundary_qualified` false.
