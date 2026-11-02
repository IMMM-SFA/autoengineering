# CAMELS source version and daily-time boundary

The [versioned source record](../../examples/utility/hydrology_camels.py) now binds
declared legacy-archive provenance and explicit no-shift/no-fill behavior.
It does not resolve physical daily intervals or admit hydrology confirmation.
No forcing, discharge series or archive was acquired for this increment.

The pinned [NCAR issue](https://github.com/NCAR/CAMELS/issues/1) remains open.
Its single saved response acknowledges the reported documentation differences
without explaining the Daymet hour field. An hour value alone therefore cannot
establish whether a daily accumulation ends or begins at that time.

The [Daymet v4 guide](https://daacweb-prod.ornl.gov/DAYMET/guides/Daymet_Daily_V4.html)
describes 365 dates per year, retaining February 29 and dropping December 31 in
leap years. This is evidence about that product. It cannot authenticate the
calendar or processing of a legacy CAMELS member. The
[CAMELS-SPAT methods](https://hess.copernicus.org/articles/29/5791/2025/)
describe another collection with v4 R1 and local-standard-time handling. Those
conventions also cannot be transferred automatically to the proposed old archive.

The pinned NeuralHydrology loader constructs its index from published year,
month and day fields and uses legacy forcing/discharge filename patterns.
This supports the nominal date-label join as a loader convention, not an exact
physical interval or causal availability contract. The original CAMELS paper's
abstract was also read and contains aggregate benchmark descriptions. That
literature exposure is recorded separately from observations. Prior personal use
of the proposed confirmation years remains unknown.

`CamelsArchiveDaymetSource` uses source schema version 2. It adds archive and
archive-metadata hashes and HUC02, fixes the declared collection and expected
member paths, and binds the parser's date/calendar policies into source identity.
It rejects a modern-product declaration, performance-selected lag policy,
implicit filling, a claimed UTC interval or verified archive membership.
These restrictions define the supported metadata contract. They do not establish
that supplied bytes came from the declared archive. Trusted acquisition must
verify the actual archive and members before scientific admission.

The parser still checks each supplied member hash, preserves published dates,
checks the declared hour and requires the frozen complete axis. Its version-1
format stays compatible. A version-2 descriptor changes source identity, so a
plan bound to version 1 cannot inherit it. An authored leap-year case with a
missing December 31 refuses before yielding any rows. It is neither shifted nor
interpolated. No offset was chosen from candidate or confirmation performance.

The [source archive](../../examples/utility/verification-camels-source-version-v1/README.md)
pins six bounded public documentation/code responses totaling 82,510 bytes,
including the loader commit and license. Total requests/transfer remain unknown
because preceding web requests and headers were not fully metered. The original
paper PDF fetch timed out and was not used to resolve timing.

The focused parser/preparation/site/documentation regression passed 89 tests.
These checks use authored data and exercise the existing hydrology lifecycle.
No standalone scientific study, training or observed-data run was performed.
Rights, real coverage/masks, archive provenance, physical interval interpretation,
prior exposure and protected execution remain unadmitted. The four task dossier
and proposal hashes are unchanged.
