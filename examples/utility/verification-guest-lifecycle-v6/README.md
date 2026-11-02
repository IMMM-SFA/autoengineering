# Current v6 cancellation and acknowledgment-loss controls

Five actual local lifecycle controls passed using the existing v6 frozen authored
fit. They created five containers and sent two START requests. Every original
container was confirmed absent, including a separate actual GET after cleanup.
No new fit, score, provider call or independent observation was used.

| Control | Created | Started | Observed boundary |
| --- | ---: | ---: | --- |
| Cancel after create | 1 | 0 | Original created event |
| Cancel before start | 1 | 0 | Original start intent; START prevented |
| Cancel running guest | 1 | 1 | Actually running, before input transfer |
| Lost CREATE acknowledgment | 1 | 0 | Real success saved, then withheld |
| Lost START acknowledgment | 1 | 1 | Real success saved, then withheld |

The two starts remain charged. Model work and elapsed inference time remain
unknown because no model result was observed. The running cancellation recovered
as `infrastructure_failure` with no model result or numeric penalty. Redispatch
was refused without a daemon request. Parent composite reservations remain
charged and unfinished. Acknowledgment loss was injected by a producer wrapper
that preserved the real response. It does not establish a real network outage.

The unchanged production executor, watchdog and ownership-checked cleanup paths
performed the work. No scientific criteria or runtime code changed in this
increment. A new reusable fixture copy preserves the previously saved v6 fit and
selection. It contains known exposed synthetic meteorological drivers. Its
authored owner template makes no OS claim. Actual execution required the v6
identity/resource proof and exact installed wheel provenance.

[Summary](summary.json) and the three public archives retain the evidence:
[unstarted](unstarted-public-proof.tar.gz), [running](running-public-proof.tar.gz)
and [response loss](response-loss-public-proof.tar.gz). They contain 104, 163 and
103 files. The matching manifests record every file's hash and size. Input-transfer
tars contain declared code, fit metadata and exposed drivers. Fitting/comparison
and private-label arrays are absent. Source and driver roots are not needed for
saved replay.

All three archives replayed after relocation in fresh processes. Model imports
were blocked from startup. Imports and metadata initialization preceded guards
that denied processes, sockets, array loading, clocks, writes and outside content
reads. Dependencies and example helpers were inherited. This verifies saved
producer evidence, not independent OS attestation or installed-reader coverage.

The first archive pass omitted the running reader's required helper snapshot.
The corrected pass copied only source matching the digest pinned before runtime
execution and preserved the already completed unstarted archive. No control,
fit, guest or model was restarted. Both archival scripts and the refusal remain.

The related tests passed 27 cases. Full default tests were not rerun because no
core, test or example runtime source changed. Current-image owner/watchdog process
loss, cancellation during model computation, private scoring, independent task
admission and the full Part 5 study remain open. The host was local OrbStack Linux
amd64 emulation on macOS ARM64. Runtime qualification remains false.

Cumulative explicit runtime accounting now records 43 creations and 34 starts.
There are 12 charged inference starts and two native references. Five started
attempts have no observed model result. Earlier unknown model/label quantities
remain unknown. The original 26-case proposal and its criteria remain unchanged.

Saved readers accept the corresponding extracted archive and the completion
digest in [summary.json](summary.json), for example:

```sh
pixi run python -m examples.utility.guest_running_cancellation_reader PATH_TO_PROOF \
  --expected-digest 58b25cd13e33f1063b2a3bc0fb95dcbcc5b751dd1152a87e353ac0432d5e6b98
```

Documentation passed 19 tests. Ruff and whitespace checks passed. The v6 wheel
still aligns with its 316 declared code sources. All public proof file hashes
were rechecked. A separate altered copy of a withheld START response was rejected.
The original proofs were unchanged. See [final checks](final-checks.json).
