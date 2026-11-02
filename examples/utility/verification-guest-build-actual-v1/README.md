# Actual candidate image build

The approved v4 request completed all seven client commands successfully in
45.4099 seconds. It installed 49 pinned archives offline, installed the frozen
wheel and passed the image's NumPy/SciPy/pandas/package import smoke. The package
transaction reported zero download bytes. The final Linux amd64 image is
1,019,479,486 bytes. This ran on the local ARM64 OrbStack host, not independent
x86-64 hardware.

Image ID:
`sha256:fc19692dff41a699600f76a79a97ed6cdcdf927f28e09984a79f33dcee46c399`.

Completion digest:
`28d422cf3dc61628de0e2db9410a644ab683e31b3e77906c5e5a679a23e0e966`.

[Summary](summary.json), [completion](complete.json), [request](request.json),
[build output](build.log) and [final inspection](image-inspect.json) retain the
public result. The image payload, executable plugin copy, bindings and full
original proof remain local in ignored work. No image was published or tagged
over another image. Earlier failed work remains preserved.

The current saved-result reader verified the original completion. A fresh
subprocess then verified 31 relocated proof files without processes, sockets,
clocks, new imports, writes or reads outside the saved data after initialization.
See [reader source](cold-build-reader.py.txt) and [output](cold-reader.log).
The reader imports pinned code before installing guards and inherits base
dependencies. This is not an installed-package qualification. The private
relocated proof includes the pinned plugin executable required by the reader;
that binary is not bundled here.

The [authorization record](authorization.json) preserves the user's approval for
future corrected image-build versions within this scope and its established
limits. It does not admit inference, scoring or independent labels.

This produces a candidate image, not a qualified private runtime. Resource
enforcement, owner-loss/daemon cancellation, diagnostics, fixed-model inference,
protected scoring and independent scientific admission remain open. Disk quotas
and build-step resource enforcement were not qualified. No inference, fitting,
provider or independent confirmation ran.
