# Installed wind cost-reader verification

The [review](../../../docs/reviews/part-5-wind-cost-report.md) describes the current
wire contract and limits. This archive reconstructs previously saved native wind
work. It runs no models, opens no weather and makes no source or dependency fetch.

- `public/` contains the original public suite and pinned cost inputs.
- `autoengineering-0.2.0-py3-none-any.whl` is the core-only reader wheel.
- [Build producer](build-install.py.txt) and [build result](build-install-result.json)
  preserve the offline source-mirror build and separate target installation.
- [Installed reader](read-installed.py.txt) reconstructs JSON/Markdown and CLI
  report/verify with example/model imports and external execution blocked.
- `installed-reader/` contains saved outputs. `summary.json` and `tests.xml`
  record source pins, checks and remaining work.

Source and work `ArtifactRef` hashes are caller-held pins. A null pin preserves
unknown work. The reader never searches for a replacement proof. These records
establish producer-metadata consistency, not source independence or OS protection.
The netCDF4 compatibility warning belongs to the preceding native run and is not
resolved by this report-only checkpoint.

Build and reader producers require new output scopes. Do not rebuild or reinstall
them to replay an existing result. The wheel inherited the interpreter's base
dependencies and installed no optional framework. Installed qualification is
limited to the recorded local base environment and cost reader, not other
platforms, native scoring or a complete release.
