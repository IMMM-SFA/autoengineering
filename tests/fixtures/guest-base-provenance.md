# Guest base metadata fixtures

`guest-base-manifest.raw` contains the public OCI manifest returned by
`docker buildx imagetools inspect --raw` for
`docker.io/library/python@sha256:623674a14ef93d052bb9b0de4dbf5f28eb578a35263838941cc8aa43213c1487`.
Its 1,752 bytes hash to that digest. The source is Docker Hub's official Python
repository, inspected on 2026-10-31. The config digest is
`sha256:37ccb536022bb36c4570856b55ebfa85bf07827e3c2fa3eba37f0dac62eebc05`.

`guest-base-inspect.json` is the approved v3 job's actual base inspection from
the local Docker 29.8.2 daemon. It reproduces the manifest-based image ID format.
These files contain image metadata, no layers or executable payloads. They do
not grant licenses to image contents or qualify a runtime/privacy boundary.
