# Baseline audit and Gate A

The cached baseline is deterministic and its arrays are isolated from evaluator mutation. It
reproduces NSE 0.2321516452, RMSE 3.0261066923 mm/day, bias 0.9666235439 mm/day, and KGE
0.4350260053 over 731 days. The numeric source is [audit.json](baseline/audit.json), with
[hashes](baseline/manifest.json) and [arrays](baseline/baseline.npz).

Both caches contain exactly January 1, 2019 through December 31, 2020, with unique, consecutive
dates and no missing cells. This cache therefore avoids the original script's potential gap
compression when `dropna` removes a day. The pilot rejects changed alignment instead of dropping
rows. Repeated baseline predictions are identical. The maximum bucket accounting residual is
2.84e-14 mm. Reconstructing the cached cfs conversion differs by at most 3.56e-15 mm/day.

The local fetcher names gage 02472000, station USW00003940, and drainage area 1947.7 km2.
Those metadata are code declarations, not freshly verified provider metadata. Raw USGS qualifiers
and NOAA quality attributes are absent from the CSVs. Missing precipitation defaults to zero in
the uncached fetcher. Weather is from one station rather than basin precipitation. These limitations
remain unresolved. No fresh data were downloaded and cached bytes were preserved.

The routing family named `calibrated` contains fixed defaults. Neither its name nor the candidate
brief establishes a recorded fit or an independent period. Both years have informed repository
development. Only the baseline's historical score was reproduced here. Historical bundled
multi-component improvements were not rerun or reinterpreted as routing-only improvements.

Gate A passes for an orchestration fixture and routing accounting. It does not pass for catchment
conservation: recharge duplicates some water already assigned by the bucket, the runoff transform
leaves part of excess unaccounted for, and baseflow has no explicit storage balance. A complete
water balance cannot be reconstructed from these definitions. The pilot consequently makes no
scientific adoption claim about hydrology and does not relax conservation to admit a model.

The smallest next scientific task is an existing explicit reservoir/bucket model with all storage
and flux terms and suitable observations. Choosing and qualifying it remains a Part 2 prerequisite
for scientific acceptance. Leaf River remains useful for testing orchestration, which the plan
expressly allows at Gate A. The preflight audit captured the then-current source hashes; later
prototype changes have their own run identities rather than rewriting this baseline evidence.
