# Pinned wind extraction source trace

The reviewed rex export preserves in-range direction angles at an existing hub
height. Together with the SAM format specification, this supports the
meteorological-from interpretation as an inference. It does not establish the
history or full semantics of the proposed source objects, qualify the annual
version join, or admit independent confirmation.

Upstream rex commit: `2cb49cfb85c29f8de6d44be3a6dc514bc3b415fb`.
The [acquisition record](acquisition.json) pins eight public metadata/code/document
final response bodies totaling 334,348 bytes. No weather was downloaded. No credential, email,
installation, image, container or scientific evaluation was involved. Earlier
web-tool access failures and a sandbox DNS failure preceded this bounded
acquisition. These eight successful logical fetches made no application-level
retries. The API URL redirected, and preliminary web-tool requests were not
instrumented. Total HTTP exchanges and total transferred bytes remain unknown.
The saved byte count covers only the eight final response bodies, not headers,
redirect responses or failed tools. No full-cost claim follows from this record.

Trace through the saved source:

1. `WindX.get_SAM_gid` requests wind direction by default and delegates to
   `WindResource.get_SAM_df`.
2. The dataframe method selects `winddirection_{height}m`. At an available height,
   the interpolated-resource reader delegates to the base HDF5 dataset reader.
   This avoids the separate circular interpolation branch for missing heights.
3. The base dataset reader unscales the stored number. `rex_unscale` divides by
   scale factor when the additive offset is zero. The check uses factor 100 and
   zero offset, matching the exposed development extraction's declared profile.
   It does not inspect any new HDF5 attributes.
4. SAM preparation rolls timestamps, leaves direction units unchanged and clips
   to 0-360. In-range directions receive no angle rotation or from/to reversal.
5. The CSV writer emits those dataframe columns. The saved SAM specification
   defines degrees east of north, with wind from north at zero and east at 90.

These are contracts in the reviewed exporter, not proof that the original raw
product was generated using that exporter or that no undocumented upstream
transformation occurred. The format inference is stronger than analogy to an
untraced SAM interface, but the production flag remains false. Raw provider
convention, version comparability and task admission remain separate decisions.
The timezone roll is evidence about value preservation only. Do not import it
into the study's UTC alignment or missingness policy.

Run the bounded [check](check.py.txt) from the repository root:

```sh
.pixi/envs/default/bin/python -B -c 'import runpy; runpy.run_path("examples/utility/verification-wind-upstream-source-v1/check.py.txt", run_name="__main__")'
```

The check verifies source hashes before extracting four reviewed helper bodies
with the Python AST. It runs cardinal and noncardinal authored values through
unscaling, units, range and timezone operations. It imports NumPy, but does not
import rex, HDF5, a task adapter or a wind model. It does not execute the complete
exporter. The [saved result](check-result.json) passed. A relocated copy also
passed, and a changed helper with a rehashed acquisition record was refused by
the separately pinned source hash.

The rex source snapshots retain their [BSD license](LICENSE.txt) and upstream
copyright notices. The SAM HTML is a cited documentation snapshot, not covered
by that rex license. Its source URL and byte hash are in the acquisition record.
No confirmation values or private labels are present.

The documentation regression passed all 19 tests. No production source or task
dossier changed, and no complete model suite was rerun for this evidence archive.
