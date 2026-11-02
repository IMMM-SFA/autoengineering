# Image build with verified base identity

This request was approved and completed in 45.4099 seconds. See the
[actual result](../verification-guest-build-actual-v1/README.md). The candidate is
Linux amd64, with all seven client commands successful. It remains unqualified
for private runtime/scoring. The scope below records the original proposal.

V3 pulled the pinned Linux amd64 base,
then stopped before building because its ID check expected the config digest.
The local containerd image store returned the pinned manifest digest instead.
All earlier work and the acquired base remain preserved.

Request digest:
`c5fe7f7072d84cb436c5fa866cc39fe7b70506692ec4774c68f68424469ce0ec`.

The included 1,752-byte raw registry manifest hashes to
`623674a14ef93d052bb9b0de4dbf5f28eb578a35263838941cc8aa43213c1487`.
It names the original expected config digest
`sha256:37ccb536022bb36c4570856b55ebfa85bf07827e3c2fa3eba37f0dac62eebc05`.
Both bindings are checked before execution and by the saved-result reader.
Manifest-based IDs additionally require matching descriptor digest, size,
media type and repository digest. Legacy requests keep their original rules.
See the [identity verification](../verification-guest-build-base-v1/README.md).

All five actual saved responses before the build pass the corrected checks.
This does not relabel the consumed v3 request. V4 adds no client commands: it
keeps v3's seven commands, base, 50 archives, plugin and verified build context.
It still permits one pinned base pull and one local build. The existing base may
be cached; transport overhead and usage remain unmeasured.

One 1,200-second client deadline covers plugin staging and all commands. Logs are
capped at 16 MiB each. Build-step limits remain 2 GiB total memory with swap capped
to the same total and one CPU, subject to daemon support. Disk is not quota-enforced.
Client termination does not prove daemon cancellation or owner-loss cleanup.
No automatic retries or renewed allowances are allowed.

`outputs/guest-image-build-v4` now holds the saved completion and private proofs.
Private paths stay in ignored bindings.
No model, provider, training, scoring or independent-label access is allowed.
An assembled image would remain an unqualified candidate. If separately approved:

```sh
pixi run python -m examples.utility.guest_image_build execute \
  examples/utility/prepared-guest-build-v4 \
  --expected-digest c5fe7f7072d84cb436c5fa866cc39fe7b70506692ec4774c68f68424469ce0ec
```

The [runtime plan](../../../docs/implementation-plans/part-5-frozen-prediction-increment.md)
requires separate assembly authority. V4 received that approval. The user also
approved future corrected build versions within the established scope and limits.
The completed v4 job remains consumed and cannot be rerun.
