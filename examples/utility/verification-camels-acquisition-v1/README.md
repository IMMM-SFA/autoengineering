# Full CAMELS acquisition and trusted source inspection

The [review](../../../docs/reviews/part-5-camels-actual-source.md) describes the
verified archive, actual placeholder-hour conflict and remaining admission limits.
This directory contains public metadata only. The source archive and all
observation values remain outside it.

- `request.json`, `acquire.py.txt` and `failure.json` preserve the first bounded
  download and its terminal time-limit refusal.
- `continuation-request.json`, `prefix-proof.json`, `continue-download.py.txt` and
  `receipt.json` bind the retained prefix to the verified full archive.
- `zenodo-record.json` is the actual provider metadata used for acquisition.
- `inspection-policy.json`, `inspection-request.json` and `inspection-failure.json`
  preserve the original README-based hour-zero declaration and refusal.
- `diagnostic.json` records only the fixed refusal category and timestamp metadata.
- `inspection-v2/` retains the literal-hour-12 declaration and passing existing
  archive/parser checks, with physical timing and task admission still false.
- `timing-search-notes.json` preserves the limits of additional method searches.
- `trusted-preparation-exposure.json` records which content the trusted programs
  received and which metadata they exported. It is not a custody admission.
- `verify.py.txt` reconstructs metadata consistency with private/original reads,
  imports, network, execution and writes denied. It does not rehash the private
  3.41 GB archive or load observation rows.

The producers consumed their output scopes. Do not rerun them to repair or replay
the records. Both failures remain. Replay uses only the metadata verifier.
No scientific model, candidate selection or confirmation score ran here.
