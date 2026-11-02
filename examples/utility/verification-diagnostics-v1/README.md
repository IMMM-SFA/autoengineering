# Saved four-family diagnostic verification

Final package: `../development/diagnostics-four-family-v4`.

The exporter verifies pinned selected states, saved prediction arrays, exposed
comparison observations and engineering scenario records. Recorded prediction
RMSE and bias are reproduced. All task/route rows remain in CSV. No model,
scientific import, network request or confirmation access is allowed in export.
The rendering script reads only the exported tables and their hashes.

Commands from the repository root:

```sh
.pixi/envs/default/bin/python scripts/utility_development_diagnostics.py \
  --output NEW_OUTPUT_DIRECTORY
MPLCONFIGDIR=/private/tmp/utility-diagnostic-mpl .pixi/envs/utility/bin/python \
  scripts/render_utility_development_diagnostics.py NEW_OUTPUT_DIRECTORY --width 8
MPLCONFIGDIR=/private/tmp/utility-diagnostic-mpl .pixi/envs/utility/bin/python \
  scripts/render_utility_development_diagnostics.py NEW_OUTPUT_DIRECTORY
```

The checked exporter uses the existing four-family study and its qualified
inventory. Output must be absent. Rendering updates only the new derived figure
package. Run the narrow render first so the final rendering sidecar hashes both
sizes. Matplotlib uses a temporary writable cache, with no global configuration.

Verification includes guarded export, exact prediction-metric checks, scenario
aggregation and forcing identity checks, explicit check units, image inspection
at 11 and 8 inches, table/image/code hashes, and refusal of a changed table before
rendering. A fresh installed reader reproduced all four CSV files and the summary
byte for byte from 94 copied pins outside the checkout. Its wheel and base cached
dependencies are identified by installed-export-summary.json. Optional scientific
packages were absent. Original checkout opens and sockets were denied by the
existing installed Python audit policy. This is not an OS private scoring boundary.

Initial failures remain: an incorrect manifest helper argument, an unnecessary
SuiteStore constructor in the copied reader, and plotting layout/date warnings.
Initial code and images remain alongside final QA receipts. Development versions
v1-v3 are retained. No model run was repeated to generate these figures.

The exporter relies on the prior qualified full reader and its pinned artifacts.
It does not claim a new full parent/child ledger replay. Current documentation
checks passed 19 tests and lint passed. Bayes verification remains under its
original running handle 59944 at this checkpoint. Independent confirmation,
complete costs, privacy, platform/host and scientific utility gates remain open.
