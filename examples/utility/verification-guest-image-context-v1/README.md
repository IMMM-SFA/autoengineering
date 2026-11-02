# Offline guest image context materialization

The new source-checkout administrative tool copies already-present, hash-bound
inputs into a fresh private build directory. It does not fetch archives or image
layers, extract an installer, install packages or start a build. The image recipe
and runtime policy remain unchanged.

The materializer verifies every input before creating output, then verifies each
again while copying through bounded streams. It copies only declared payloads and
recipes. Unrelated cache files never enter the context. A separate proof directory
contains only the referenced recipe/environment closure. All output directories
and files are private. The completion manifest is written last. Partial output
cannot be resumed or overwritten.

Cold verification checks the exact file/directory closure, recipe and payload
bindings, content hashes and fixed nonexecuting status. It refuses extra files,
empty directories, symlinks and nonregular entries. Repinning metadata cannot
turn it into build authority. Declared copied files are capped at 8 GiB and each
at 512 MiB, with 1 MiB streaming reads. Tool source and the small manifest are
additional metadata. These are byte-copy bounds, not measured disk use or a
filesystem interruption guarantee.

## Verification

The first run had 55 passes and three failures from intermediate directory modes.
Its observed result is recorded in `initial-result.json`; full stdout was not saved.
After creating every directory explicitly as private, 58 tests passed in 2.53
seconds. The final image/context/environment check passed 61 cases in 2.68 seconds,
including bounded-copy, permission and guarded cold-reader checks.

Positive materialization uses authored bytes and fixture installer metadata. It
is not validation of downloaded packages or the real installer archive. The
relocated fixture reader runs with original cache/source/plan directories deleted,
processes, sockets and clocks denied, and an audit guard denying writes and file
reads outside the relocated closure.

`missing-production-inputs.py.txt` checks the unchanged production recipe against
an empty cache. It refuses missing archives before creating output, with acquisition,
processes and clocks denied. Its initial script-path import error is preserved in
`missing-production-inputs-before.log`; the corrected harness passes. No real
production context was materialized because its archives remain unacquired.

The preceding image plan and wheel retain their original 224-core/315-source scope.
This new host helper is not in that wheel. Installed-helper, actual production
copy, acquisition/build, daemon, diagnostic-profile and runtime/privacy checks remain
open. No independent data, fitting, provider or scientific matrix ran. Part 5 remains
incomplete.
