# Campaign contracts

The experimental campaign broker and CLI run the synthetic scalar example through baseline,
admission, fixed replacement, scientific review, selection freeze and reporting:

```sh
pixi run autoengineering campaign validate examples/campaign_contracts/fixture.yaml
pixi run autoengineering campaign run examples/campaign_contracts/fixture.yaml \
  --workdir outputs/campaign-fixture --max-new-evaluations 1
pixi run autoengineering campaign resume outputs/campaign-fixture --max-new-evaluations 1
pixi run autoengineering campaign report outputs/campaign-fixture
```

The direct equivalent uses `CampaignController.create(specification, source_root, workdir)` and
`advance()`. `open(workdir, max_new_evaluations=N)` verifies dependencies before compatible resume.
The [campaign guide](../../docs/campaigns.md) explains the JSON tools, trust boundary and exits.

`fixture.yaml`, `request.json`, and `response.json` demonstrate resolved author and tool contracts.
The forcing, fitting, and comparison files are separate. Trusted registry factories supply the
implementations. Worker requests contain artifact IDs and permitted values rather than imports,
commands, or evaluator file paths.

## Hydrology development profile

The stateful hydrology wrapper uses the existing Hamon/Hargreaves PET and soil bucket equations
with a linear reservoir. It exposes ET, discharge, soil and reservoir storage, and initial
conditions. A new configuration starts soil at half its own capacity and reservoir storage at
zero. Continued forcing preserves both stores across chunks. Synthetic tests check direct-call
parity, state continuity, causal behavior, exact interfaces and independent daily conservation.

`profile/campaign.yaml` resolves the measured-data development case. The builder performs no
scientific evaluations. The workflow plans two defaults, 32 Sobol fitting calls, two selected
comparison calls and two declared causality calls: 38 physical executions. The last stage changes
only future precipitation and checks that earlier discharge stays unchanged. Diagnostic metrics
never participate in fitting or selection.

Forcing contains no discharge observations. Separate NPZ files hold fitting and comparison labels.
Historical labels remain unchanged: January-March 2019 warm-up, April-September fitting,
October-December development comparison, and exposed 2020 observations. The latter period is
excluded from primary qualification and cannot support a new holdout claim. Original HTTP
responses and source quality flags are absent from the legacy cache.

## Routing reference

`routing-profile/campaign.yaml` uses saved Part 1 driver arrays and the supplied triangular/gamma
routing functions. The two fixed configurations reproduce the earlier reference comparison.
This example tests routing accounting and orchestration, not a complete catchment water balance.
It creates a new campaign. It does not resume or modify any Part 1 journal.

## Profile preparation and status

During implementation, rebuild the resolved source identities without running a scientific model:

```sh
pixi run python -m examples.campaign_contracts.build_fixture
pixi run python -m examples.campaign_contracts.build_profile
pixi run python -m examples.campaign_contracts.build_routing
```

The source closure includes package sources, supplied equations and glue, cache metadata and the
environment lock. Regeneration updates those declared source identities. Freeze the final profiles
before the first real qualification comparison. The final macOS ARM64 qualification is retained
under `outputs/campaign-qualification-v3`.
It passed 80 executions in that round and 240 across all three preserved rounds. Verify it without
new model starts:

```sh
pixi run python -m examples.campaign_contracts.qualify --verify --output outputs/campaign-qualification-v3
```

See the [verification record](../../docs/reviews/part-2-workflow-contracts-progress.md) for measured
results, source identity, limits and the Part 3 handoff. Linux remains unverified. These examples
do not establish general model improvement or independent hydrologic confirmation.

`profile/audit.json` is a preparation receipt. Its zero model count refers to the builder, which
performs no model execution. Actual qualification counts are recorded in the verification evidence.
