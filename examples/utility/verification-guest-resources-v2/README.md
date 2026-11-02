# Derivative-image resource controls

All six fixed resource probes passed against
`sha256:516cb2702eb45d99264dc90622fea8de4de987f68b4266ba8c86da4c312390de`.
Each used one creation/start and confirmed its original container absent.
Memory produced OOMKilled and exit 137. Processes reached EAGAIN at cgroup count
16. Workspace returned ENOSPC at 128 MiB. Root, network and host-canary checks
returned EROFS, ENETUNREACH and ENOENT. No scientific model, fitting, label,
score, provider, image pull or host mount was used.

The fixed catalogue retains the original image and adds this derivative. Its
exact seven environment entries and inherited provenance labels are checked
before creation. Requests explicitly include the expected inherited labels.
Unknown images and unexpected environment/labels refuse. Original-image receipts
retain their original configuration and still replay.

[Completion](complete.json), [observations](runtime-observations.json), output logs
and executed source snapshots retain the evidence. Request:
`ebd628517a85b6173f127819782d62d36ca9d4d3dc17c28e6ab68a013bfa504e`.
Completion: `e899a83865a1ae3619af3fcfbbf68b204525566f168350ffa258582556a6df8b`.
A fresh guarded process verified 108 relocated files, 405,034 bytes. Imports
preceded the guard and dependencies were inherited. See [scope](cold-reader.json)
and [output](cold-reader.log). This is source-based replay, not independent OS
attestation or full installed-package qualification.

Both resource profiles together retain 13 creations and 12 starts, including
the original refused creation and its separate administrative cleanup. The
original 26-case proposal is unchanged and has not run as a whole. These normal
completions do not qualify owner loss, cancellation, deadlines or private scoring.

```sh
pixi run python -m examples.utility.guest_resource_reader outputs/guest-resources-v3 \
  --expected-digest e899a83865a1ae3619af3fcfbbf68b204525566f168350ffa258582556a6df8b
```

The related final regression passed 417 tests without failures, errors or skips.
See the [shared verification](../verification-guest-inference-smoke-v1/README.md).
