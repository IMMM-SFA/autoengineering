# Wind NetCDF environment experiment

The existing wind environment still emits the recorded NumPy array-size warning.
An isolated local netCDF4 patch removes that import warning and passes authored
I/O and cross-reader checks. Its broader upstream regression did not pass, so
the candidate was not promoted. No scientific wind model or reserved weather ran.

The warning must be tested after importing NumPy, whose installed filters can
otherwise hide it. The original environment has Python 3.12.14, NumPy 2.5.2,
netCDF4 1.7.4 and PyWake 2.6.20. Rebuilding the unchanged netCDF4 source against
that same NumPy reproduced the warning. This contradicts the proposed remedy of
rebuilding alone.

Source inspection found a legacy opaque `numpy.ndarray` declaration in
`include/netCDF4.pxi` alongside the declaration already imported from NumPy.
Generated C imports the former with a size warning and the latter with NumPy's
size policy. The local patch uses the existing NumPy declaration. That exposes
a scalar-attribute comparison whose static type changes: the patch also replaces
`value_arr.shape == ()` with the equivalent `value_arr.ndim == 0` test.
This evidence supports a declaration-specific explanation of the warning. It
does not establish general binary compatibility.

[Cython documents these external-type size checks](https://docs.cython.org/src/userguide/extension_types.html).
The build follows [Unidata's source-build interface](https://unidata.github.io/netcdf4-python/)
using the existing local NetCDF/HDF5 libraries. It changes no global warning
filter and retains the original warning criterion. The compiled candidate uses
local macOS 26 libraries and is not a portable release artifact.

| Attempt | Outcome |
| --- | --- |
| Same-version source rebuild | Built; authored I/O passed; binary warning remained |
| First declaration patch | Compile failed on the scalar shape comparison |
| Corrected declaration/scalar patch | Built; import warning absent; authored and cross-reader checks passed |
| Six-file upstream regression, warnings as errors | 8 passed, 5 failed |

Authored checks cover 48 synthetic hours, masks/fill, compression, packed values,
CF time conversion, xarray's NetCDF backend, compound values, variable-length
arrays/strings and scalar/vector attributes. Both original and patched readers
read the other writer's files. These checks contain no task observations.

The upstream failures include one denied `ncdump` launch, two NumPy 2.5
shape-assignment deprecations and two subsequent temporary-file permission errors.
The original failures and traces remain. Warnings were not ignored to obtain a
passing suite, and this was not the full upstream suite. The original extension
hash remained unchanged. No package was installed into the existing wind
environment.

Seven logical public HTTP requests read 4,925,020 bytes, including a discarded
1,000,001-byte oversized metadata response. HTTP exchange/transfer cost is
unknown. A fixed-version metadata correction retained the failed request charge.
Three build attempts were charged. Build dependencies and both built wheels went
only to isolated targets. The original metadata intent named a 30-second timeout,
but its fetch code used 60 seconds. No request timed out; a 30-second enforced
bound is not claimed.

The [archive](../../examples/utility/verification-wind-netcdf-build-v1/README.md)
preserves source hashes, MIT license, patches, all build/probe results and the
failed regression. The normal wind environment retains its warning. Actual wind
task admission, protected execution, full environment qualification and independent
confirmation remain open. No upstream message, release or project dependency
change was made.
