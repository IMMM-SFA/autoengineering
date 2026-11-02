# Isolated wind NetCDF environment experiment

The [review](../../../docs/reviews/part-5-wind-netcdf-environment.md) records the
bounded experiment and its adverse results. No scientific model, private source
or reserved weather was used. The existing project environment was not replaced.

- `fetch*.py.txt` and their records retain seven logical requests, the oversized
  metadata refusal and exact public input hashes.
- `build*.py.txt` and logs retain three build attempts and isolated installations.
- `numpy-array-declaration*.patch` describe the local upstream-source edits.
- `probe*.py.txt` and `check-probes*.py.txt` retain the unchanged warning criterion.
- `patched-v2/probe-result.json` records passing authored and cross-reader checks
  with the candidate warning absent and the original warning retained.
- `upstream-tests.xml`, `upstream-tests.log` and the test producer retain the
  broader result: 8 passed and 5 failed. The candidate was not promoted.
- `netcdf4-1.7.4.tar.gz` and `upstream-source/LICENSE` preserve upstream source and
  licensing. Built wheels retain their upstream license metadata.

The producers have consumed output scopes and must not be rerun to replay these
records. The metadata verifier hashes archived bytes and reconstructs recorded
counts. It does not load either binary, compile, run I/O or prove runtime safety.
