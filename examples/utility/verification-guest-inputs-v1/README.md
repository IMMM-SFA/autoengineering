# Candidate frozen guest inputs

The package carries the exact v2 job, worker intent, original claim, pinned guest
environment, dependency lock, selected state/runtime, six fit/provenance metadata
artifacts, inventoried core/model Python sources and one normalized driver artifact.
It does not copy fitting or comparison arrays, labels or undeclared tree contents.
Artifact references inside frozen metadata do not grant access to their payloads.

Preparation requires both the original suite and owner writer locks, the original
owner lease, frozen selection and original charged composite access. Public source,
selection, environment and wheel-code checks precede driver access. The permanent
input intent precedes the first driver read. Interruption cannot retry that read.
A complete manifest is published last. Recovery verifies the saved package only.

Members have fixed uid/gid 1000, regular-file mode 0600 and directory mode 0700.
The canonical uncompressed tar has no links, extensions or trailing content.
Limits are 1024 files, 4 MiB per file, 32 MiB payload and 40 MiB transfer bytes.
These are candidate input limits, not measured guest OS resource qualification.
The reader checks every member hash, exact frozen membership and original job,
launch, claim, intent and wheel identities. Refreshing a tar/manifest hash cannot
admit a fitting payload or an undeclared member.

The first focused test passed 15 cases in 10.03 seconds. The expanded archive/path
and custody checks passed 33 cases in 16.04 seconds. Later tests add wheel/source
mismatch refusal before driver access and a fresh cold process. Cold verification
denies model imports, array interpretation, process launches, sockets, new clocks
and unrelated or writable reads. All datasets and OCI records are authored test
fixtures. The common fixture runs an ordinary development baseline, never a guest.

Exact broader/final results and source pins are recorded separately. Preparation
performs no image assembly, acquisition, installation or daemon operation. Actual
transfer/dispatch, watchdog cleanup and OS/privacy qualification remain open.
No default executor or confirmation service activates this candidate path.

The broader guest/environment/v1 inference/composite/cost regression passed 284
cases in 159.43 seconds. That run predates the owner start-binding addition and
has separate initial source pins. After that addition, the final package/owner/
observation/archive check passed 203 cases in 51.71 seconds. Legacy owner archive
replay also passed. Nineteen documentation cases passed in 0.60 seconds. Full Ruff,
explicit 100-column checks on changed Python files and whitespace checks passed.

The final authored capsule has 239 input files, 3,489,429 payload bytes and a
3,696,640-byte canonical tar. Its saved owner journal contains the package binding.
The outer authored-owner-inputs.tar.gz has 18 saved owner files. replay-public.py.txt
relocates them and verifies the package, original start binding and projections
with processes, sockets and clock sampling denied. No original input scopes are
required. Source snapshots preserve both tested revisions.

When preparation has begun, the owner start intent requires a completed package
and pins its digest. Journal replay verifies the same binding. An incomplete
package blocks the start commit. Legacy evidence-only records omit the optional
field and preserve original bytes. A future actual dispatcher must require the
package binding. These records alone grant no execution authority or admission.
