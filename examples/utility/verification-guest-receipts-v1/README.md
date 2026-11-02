# Candidate guest receipt reader verification

The archive binds the v2 job and environment, original suite claim, launch policy,
container start, stopped state, cleanup, bounded result capture, physical checks
and output/vector hashes. The caller supplies explicit source, lock, executor and
runtime pins. Verification contacts no daemon and starts no model or process.

All container and API capture records here are authored projections. They are not
observed OCI evidence. Their raw-capture digests preserve producer claims; the
reader cannot independently attest image identity or OS enforcement. The returned
boundary remains unqualified-candidate. No service, launcher or runtime is
registered by these records.

The first reader tests passed 35 cases. The compatibility regression passed 133
tests in 124.32 seconds. After requiring the saved environment manifest as well as
its pin, the final guest/archive checks passed 72 tests in 13.98 seconds. These
cover foreign/corrupt evidence, incomplete capture, timeout/cancellation/OOM/dead
and failed exits, scientific/model failures, prediction conflicts, terminal state,
relocation and cold reconstruction. Unknown lifecycle time stays null.

The fixed policy projection binds the isolated command, single-thread environment,
user, no host mounts/devices, no network, capabilities, root/workspace permissions,
resources and no stdin/host logging. It is a candidate contract, not an enforced
configuration. An actual owner must qualify the image/API, validate original raw
observations, enforce the selection/access barrier and export the linked receipts.

The saved authored archive and reader inputs are a replay fixture. Preserve the
original fixture and use a fresh directory for extraction. The original guest job
is required; local supervisor archives still cannot complete a guest attempt.
Full default, installed, actual guest/OS and independent scientific qualification
remain open for this new reader.

See [summary](summary.json), [reader inputs](reader-inputs.json),
[verified projection](verified-projection.json) and
[the implementation audit](../../../docs/reviews/part-5-completion-audit.md).
