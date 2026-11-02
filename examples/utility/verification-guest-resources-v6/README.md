# Current v6 image resource controls

All six fixed probes passed against the current v6 candidate image. Memory
reached its 1 GiB cgroup limit and exited 137 with OOMKilled. Processes reached
EAGAIN at cgroup count 16. Workspace returned ENOSPC at 128 MiB. Root, network
and host-canary probes returned EROFS, ENETUNREACH and ENOENT.

The request allowed six creations and six starts, with no retries. All six
original containers were confirmed absent. No model, fitting, score, private
label, provider, image pull or host mount was used. This was local OrbStack
Linux amd64 emulation on macOS ARM64. It does not establish an independent
physical x86 host, owner-loss handling or complete runtime qualification.

[Summary](summary.json), [original evidence](evidence/complete.json) and
[source inventory](../source-inventory-guest-resources-v6.json) retain the
identities and observations. Request digest:
`5a0dc37254fa4eb181ed5b9e2a9a2ff8c14f236d7ae0de34189d381ee443abb7`.
Completion digest:
`98079b65f6ec0d7122145a51fe0e8d4f0b1b88aaebdf9afb8674040b3b2c4648`.

The image catalogue now binds the v6 image's exact environment and wheel labels.
Historical image configurations remain unchanged. The related tests passed
136 cases. The first test run exposed three cases in a shared reader fixture
that still used v5 metadata. Its correction and the initial result are retained.

A fresh process replayed 109 relocated files (405,588 bytes) after installing
read-only guards. Imports preceded the guard and dependencies were inherited.
No process, network, clock, write or outside file access was allowed during
verification. A separate modified copy with false cleanup absence was rejected.
The original evidence was unchanged. This is saved producer-evidence replay,
not independent OS attestation or installed-package qualification.

Cumulative explicit runtime accounting is now 37 creations and 31 starts.
Earlier unknown work and label quantities remain unknown. The earlier image's
inference, lifecycle and private-scoring evidence does not transfer to v6.
The original 26-case proposal and all task admissions remain unchanged.

```sh
pixi run python -m examples.utility.guest_resource_reader \
  examples/utility/verification-guest-resources-v6/evidence \
  --expected-digest 98079b65f6ec0d7122145a51fe0e8d4f0b1b88aaebdf9afb8674040b3b2c4648
```
