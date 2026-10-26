# Part 2 completion audit

The macOS implementation passes all seven increment gates. This audit maps the implementation
plan's acceptance requirements to observable checks and local evidence. Final qualification and
test results are recorded in the accompanying
[progress record](part-2-workflow-contracts-progress.md). Linux process/locking qualification is
outstanding under the plan's explicit platform exception. Windows is outside scope.

## Increment gates

| Gate | Evidence and scope |
| --- | --- |
| 2.1 Strict contracts | `test_campaign_contracts.py` checks canonical YAML/JSON round trips, duplicate keys, unknown fields, unsupported versions, boolean limits, finite values, dates, duplicate IDs/references, deep immutability, source identity, ordered optimizer space, legacy YAML and optional imports. `fixture.yaml`, `request.json`, `response.json` and both measured-data profiles are resolved examples. |
| 2.2 Adapter/science | `test_adapter_contracts.py` covers exact metadata, same-shape shifted dates, coordinate order, units, missing inputs, dtype, input mutation, cleanup at every lifecycle failure, optional fitting-only training receipt, state reset/continuity and direct kernel parity. `test_campaign_acceptance.py` covers unavailable/error checks, fabricated residual/zero-flow evidence, ineligible baselines, exact ties, full precision and secondary tolerances. Qualification recomputes balance and metrics from saved arrays and compares both PET defaults with supervised kernel oracles. |
| 2.3 Durable events | `test_campaign_store.py` injects five commit boundaries, reconstructs missing/stale projections, preserves torn temporaries, refuses gaps, modified canonical tail events, changed results, symlinks and invalid references. Every event stores its own checksum and its predecessor hash. `test_campaign_service.py` checks persisted duplicate responses before revision, conflicts, stale revisions, bounded transport/reject counts and branching repair limits. |
| 2.4 Attempts/processes | `test_campaign_execution.py` covers full reservations, no extra start, unresolved allowance, idempotent resolution, invocation/time ceilings, durable process receipts, timeouts, descendants, cancellation while locked, failed stops and wrong-generation nonces. `test_campaign_recovery.py` kills an actual supervisor and verifies that work remains blocked until an owned group stops. Cancellation retains uncertain cost. |
| 2.5 Study bridge | `test_campaign_studies.py` compares interrupted/uninterrupted fitting selections and public resolver recovery. `test_campaign_recovery.py` covers a saved worker result before campaign commit, saved fitting result before child acknowledgment, and unknown physical work despite zero child recovery cost. The bridge uses public optimizer construction/run APIs, archives child manifests and never patches pending files or appends observations itself. Existing recovery tests retain their expected semantics. |
| 2.6 Broker/CLI | `test_campaign_controller.py`, `test_campaign_cli.py` and `test_campaign_diagnostics.py` cover positive and negative decisions, identical direct/CLI decisions, pause/resume counts, no eligible recommendation, no candidate, insufficient observations before launch, budget exhaustion, read-only reports, invalid UTF-8, cancellation replay, one-shot confirmation, failed confirmation without reselection and two-call diagnostic stage boundaries. `test_campaign_recovery.py` checks duplicate dispatch during active execution with a single charged attempt. |
| 2.7 Qualification/handoff | The frozen qualifier executes the same measured-data task through direct and bounded CLI paths, the two fixed routing references, and two independent kernel calls. Its verifier reconstructs all metrics, balances, causality prefixes and pair decisions from artifacts. `docs/campaigns.md` documents actual APIs, commands, trust, recovery and exits. `docs/part-3-campaign-handoff.md` defines the future tool/artifact permissions and host provenance boundary. |

## Identity and evidence review

The campaign identity binds the resolved schema, baseline/model definitions, inputs/observations,
acceptance and model/glue sources, parameter ordering, seeds and environment lock. The supplied
profiles declare the complete package plus their known local model helpers and package initializers.
This is an explicit closure, not discovery of arbitrary imports.

The source audit found a copied-bundle gap after the first numeric qualification. Two failing
regressions demonstrated that changed declared adapter/engine bytes could be accepted even while
the original modules would execute. The fix verifies actual engine bytes before create/resume/start,
checks supplied adapter source locations and checks loaded module locations before preparation.
Both regressions now refuse the task before creating a work directory. Qualification was repeated
under a new identity. The original run remains intact and bound to its older source version.

A child identity binds its exact candidate, adapter, fixed parameters, fitting/forcing references,
ordered search space, policy/options, budget, seed and campaign. Each later family links its study
predecessor. Changed scientific input cannot resume an old child through the public broker.
Legacy optimizer recovery also rejects incompatible source/input/seed/space/policy identities.

Physical counts are not ledger costs added to reservations. Reservations describe capacity,
attempts describe physical or uncertain work, and costs remain measured or unknown. A recovered
unknown child action can remain a zero-cost infrastructure failure in its ledger while its outer
attempt consumes capacity. Acknowledging uncertainty does not manufacture a measured zero.

## Scientific claims and limits

The two PET families use the same meteorological interface, daily forcing, initial-condition rule,
parameter space and acceptance rules. Every configuration starts soil at half its own capacity and
reservoir storage at zero. Fitting and comparison are one causal simulation. Store snapshots label
the end of each daily update. Daily temperature extrema are features assigned to their source date
label, not evidence of the intraday time at which an extreme occurred.

The measured-data qualifier preserves warm-up January-March 2019, fitting April-September,
development comparison October-December and exposed 2020 data. The latter is not used as a new
holdout. It checks two defaults, 32 fitting runs, two selected comparison runs and two future-forcing
perturbations. The fixed Hargreaves, calibrated Hamon and calibrated Hargreaves comparisons retain
their distinct comparator identities. No diagnostic score enters fitting or selection.

The selected model passes the declared relative acceptance rules, but comparison NSE and KGE remain
negative. The result supports workflow qualification and relative comparisons within this exposed
development case. It does not establish predictive adequacy, scientific generalization or an
independent confirmation. Routing parity concerns routing accounting, not a full catchment balance.
The reports explicitly state `confirmation_not_attempted`.

The only optimizer extension is an optional public `pending_result_resolver`. Without a verified
outer result, default pending recovery remains unchanged. No frozen benchmark matrix, gate,
observation, Part 1 manifest or Part 1 source was rewritten. The package still makes no LLM calls.
Strict tokens, other providers, production agent roles, arbitrary code admission, ML training,
general DAG redesign, a host plugin, web UI and distributed execution remain deferred.

## Final closure evidence

The final default suite reports `609 passed, 65 skipped`. Ruff and `git diff --check` pass.
The final qualification source IDs match the current worktree and its archived bundles. It
records 80 confirmed executions in the final round and 240 cumulatively, within 320.
The [machine-readable summary](part-2-workflow-contracts-qualification.json) records the source,
lock, package and platform identities, full precision comparison metrics, decisions and counts.
All 39 links in each hydrology report and all three routing report links resolve inside their
campaign to immutable records. Incompatible resume of the first source version was also checked
and left every file byte unchanged.

The optional bayes environment is absent and its suite was not run. The 65 default skips concern
optional Bayesian/BMI/pvlib/open-chain dependencies. Linux remains explicitly outstanding. These
limits do not imply passing gates on an untested platform or missing optional environment.
