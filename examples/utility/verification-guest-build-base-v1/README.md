# Base identity verification

The approved v3 job passed three metadata checks, pulled the pinned base and
inspected it. All five client commands exited zero. Identity validation stopped
before the build because Docker returned the manifest digest as `Id`, whereas
the original rule expected the config digest. The original job remains consumed.
[Recorded observations](actual-base-verification.json) distinguish that failure
from the corrected rule. No build or package installation ran.

The [raw public manifest](base-manifest.raw) is exactly 1,752 bytes. Its SHA-256
matches the original pinned manifest, and its config descriptor matches the
original expected config ID. No source identity was replaced.
[Moby's containerd inspection implementation](https://github.com/moby/moby/blob/master/daemon/containerd/image_inspect.go)
reports the target descriptor digest as the image ID, consistent with the
observed response. This source was inspected on 2026-10-31.

Request v4 carries that raw proof. It accepts the manifest ID only with matching
descriptor digest, size, media type and repository digest. The legacy config-ID
form remains supported. Existing request versions keep their original rules.
Saved readers require the manifest proof without fetching it or reading original
scopes. Modified bytes, wrong config, missing descriptor/repository evidence and
missing saved proof refuse. Tests include the actual base-inspection format.

The new checks pass all five saved pre-build responses. This is offline
reconstruction of actual observations, not a new image job or reclassification
of v3. The public copy omits v3's context log because it contains the private
socket path; the full log remains in ignored original work.

Core code and frozen guest inputs remain unchanged. The administrative helper,
tests and two small metadata fixtures postdate the full v5 default checkpoint.
The related regression passed 114 tests, with zero failures, errors or skips.
Repository lint passed. The raw manifest and actual inspection format are small
test fixtures with [provenance](../../../tests/fixtures/guest-base-provenance.md).
The [v4 proposal](../prepared-guest-build-v4/README.md) is unexecuted. Runtime,
private scoring and independent scientific qualification remain open.
