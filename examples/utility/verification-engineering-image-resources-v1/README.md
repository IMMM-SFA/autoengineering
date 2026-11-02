# Coupled-image resource and output controls

Eight fresh diagnostics passed on the exact coupled image
`sha256:62f6c7b58e34f4ec5d5517af49c8b9e1e7d1d7235f550384ac52c1281fb262ad`.
The image was already available locally. No build, pull, installation, scientific
packet, source read or model evaluation was used.

Memory pressure ended with exit 137 and daemon `OOMKilled` at the 1 GiB limit.
Forking reached `EAGAIN` with 16 cgroup processes. Scratch writes reached `ENOSPC`
at 134,217,728 bytes. Root writes returned `EROFS`, the isolated network returned
`ENETUNREACH`, and the unmounted fresh host canary returned `ENOENT`. Effective
CPU quota, UID/GID, capabilities and seccomp settings were also observed. CPU
saturation and scientific-model RSS were not measured.

Two synthetic controls executed the image's hash-pinned fixed worker output
wrapper. A 4,096-byte child output stayed within the limit. The shared stdout/
stderr overrun reached 16,384 bytes and terminated with `SIGXFSZ`. No child bytes
were forwarded as a result, and no score was produced.

The request reserved eight creations and starts, with a 60-second active window
and 10-second cleanup window for each. No attempt was repeated. Each original
container was separately confirmed absent. The commands were fixed diagnostics,
not the scientific scoring entrypoint. A private policy namespace binds the
exact image and two public output modes. Production catalogues, scoring paths,
owner code and existing qualification records were not edited.

A standalone stdlib reader replays copied configuration, context, terminal,
output and cleanup records outside the checkout. It rejects false cleanup even
with recomputed test pins. This is producer-evidence reconstruction, not
independent OS attestation. The owner and core remain at the preceding verified
source checkpoint. The full default test suite was not rerun for these new
diagnostic records.

The [v21 register](../guest-qualification-accounting-v21.json) records 67 container
creations and 52 starts. Its known model-start lower bound remains 105, including
96 coupled evaluations. Older unknown work stays unknown.

These observations establish the listed image/diagnostic limits on local Linux
amd64 emulation under macOS ARM64. They do not establish an independent physical
x86 host or complete the scientific owner's resource/interruption matrix. Loss
during computation, arbitrary daemon delay, task admission and the independent
utility study remain open. Runtime/private admission remain false.
