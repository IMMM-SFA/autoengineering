# Fixed guest Python discovery

This metadata-only request completed. It reserved one container creation/start,
60 active seconds and one ten-second cleanup window. Its fixed Python program
had a ten-second alarm. No host mounts, model inputs, labels, image pulls or
scientific work were permitted. Requested isolation used UID/GID 1000, a read-only
root, no network, one CPU, 1 GiB memory, 16 PIDs and a 128 MiB work tmpfs.

Request digest:
`f2df304d9bee6b956c0e9641c2323a9c1446e9610621cd03669ec36dbe535107`.

Completion digest:
`653357f8bf204e3366d15d68f86c4c2f230db11409cf5f24c2f8526d7727c8d8`.

The program observed the expected installed source, Linux x86-64, isolated
CPython 3.12.13 and package 0.2.0. One container start was recorded and the
original container was confirmed absent. See the
[executed evidence](../verification-guest-identity-v1/README.md).

The original request, controller and private bindings are preserved. The job is
consumed and cannot restart. The exported profile remains an unqualified
candidate. Resource enforcement, private inference/scoring and owner-loss behavior
are not admitted by this metadata observation.
