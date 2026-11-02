# Actual unstarted cancellation controls

Both actual local controls passed using the resource-checked derivative image
and the existing frozen authored fit. Each created one container, started none
and confirmed its exact original container absent. No model, fitting, scoring,
provider or independent-data work ran. The parent composite reservations remain
charged and unfinished.

`cancel_after_create` persisted cancellation at the original `created` event.
The production creation-cleanup path verified ownership, observed an unstarted
container and deleted it once. `cancel_before_start` armed the production
watchdog, attached and persisted the original `start_intent`. Cancellation then
prevented the START request. The watchdog observed cancellation and deleted the
unstarted original container. Both cleanup readers verify the saved original
plans, ownership, mutation intents and absence evidence. A separate actual GET
returned 404 for each exact container after cleanup.

The request digest is
`88205202e69e4d28264d731d7c1b0bd76cad34c2e8077432b7669ce548db18a6`.
The completion digest is
`a75833654e13b948e2a7c279528d045ebedad20fd3a451d3ed5f05787ab3bcba`.
`runner.py.txt` preserves the exact producer. Each prepared smoke request allowed
at most one start, but this outer cancellation request and its API guard reduced
the actual allowance to zero. The wrapper delegated real responses unchanged,
recorded attempts before sending them, refused repeated owner mutations and
refused any container START before sending it. The watchdog ran separately with
its own production cleanup journal.

`public-proof.tar.gz` contains the 93 files hashed by `proof-manifest.json`.
SHA-256 and size are in `summary.json`. The proof includes original input-transfer
tars containing declared source, fit metadata and known exposed meteorological
drivers. It contains no fitting labels or private labels. No separate suite,
source or driver root is needed for saved replay. The working roots remain in
the ignored `outputs/guest-cancellation-controls-v1` directory.

The saved reader supports a relocated, owner-private proof tree:

```sh
pixi run python -m examples.utility.guest_cancellation_reader PATH_TO_PROOF \
  --expected-digest a75833654e13b948e2a7c279528d045ebedad20fd3a451d3ed5f05787ab3bcba
```

The archive was extracted after checking every member's name, regular-file type,
size and hash. All directories were created with mode 700. Saved replay passed
in a fresh process after initialization with external content reads, writes,
imports, clocks, array loading, sockets and processes blocked. It reads and
verifies the saved transfer tar bytes. Dependencies and helper code were inherited
from the checkout before the guard. This does not qualify package installation,
attest the operating system or independently reproduce daemon observations.
The first cold invocation could not import the example helper from the script
folder. Its log is retained. The corrected invocation initialized from the
checkout and passed for both a copied tree and the extracted public archive.

Running cancellation, owner/watchdog loss, adverse output, lost responses,
private inference/scoring and independent task admission remain open. These two
controls are separately counted in the successor evidence map. They do not
rewrite the original 26-case proposal or reset earlier consumed attempts.

The related lifecycle regression passed 136 tests. Its reader revision predates
the later after-create transfer check. The final reader/control checks passed
all 10 tests, including transfer corruption, and the archive guard passed again.
The summary records these scopes separately. Documentation checks passed 19
tests, Ruff and whitespace checks passed, and the frozen 224-core/315-source
runtime closure remains unchanged. The full default suite was not rerun.
