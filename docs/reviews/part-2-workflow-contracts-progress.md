# Part 2 implementation and verification

Part 2 is implemented in `.worktrees/agentic-architecture` and verified on macOS ARM64. The
[completion audit](part-2-workflow-contracts-audit.md) maps each increment to tests and evidence.
Linux qualification remains outstanding as the plan permits. Windows is outside scope.

This verification preceded the separately requested implementation commit. No push, installed
host plugin, live LLM call or frozen benchmark replacement was performed.
Part 1 sources, arrays, manifests, ledgers and existing lock files were preserved.

## Delivered interfaces

- Strict immutable campaign/domain records, canonical YAML/JSON, semantic identities, declared
  source closure, bounded artifact access and actual executing-source verification.
- Trusted Python lifecycle, supplied scalar/hydrology/routing adapters, exact scalar/daily metadata,
  isolated inputs and independent physical acceptance checks.
- Single-writer checksum/hash-linked event commits, pure replay, projections, request idempotency,
  bounded rejects/repairs, physical reservations, process supervision, cancellation and reconciliation.
- Existing optimizer bridge with immutable child links, per-action supervision, fitting-only
  selection and a public optional `pending_result_resolver`. Default legacy recovery is unchanged.
- Direct `CampaignController`, scripted supplied candidates, seven `campaign` CLI commands,
  evidence reports, selection freeze and explicit disabled/one-shot synthetic confirmation.
- Resolved fixtures, measured-data profiles, bounded qualifier and independent artifact verifier.
  Current usage is in [campaigns.md](../campaigns.md). The
  [Part 3 handoff](../part-3-campaign-handoff.md) defines future tool/artifact permissions.

## Final verification

Python 3.12.13, macOS ARM64, with the existing repository default Pixi environment. The linked
worktree has no separate installed environment, so commands used its own `src` and the existing
environment's executables. No dependency installation or lock update was needed.

```sh
/Users/cam/projects/autoengineering/.pixi/envs/default/bin/ruff check --no-cache src tests examples
PATH=/Users/cam/projects/autoengineering/.pixi/envs/default/bin:$PATH PYTHONPATH=src \
  /Users/cam/projects/autoengineering/.pixi/envs/default/bin/python \
  -m pytest tests -q -p no:cacheprovider
```

Ruff passed. The final default suite passed with `609 passed, 65 skipped` in 130.53 seconds.
Skips concern unavailable optional Bayesian, BMI, pvlib and open-chain environments. The separate
bayes environment is absent, so its suite was not run. No frozen benchmark matrix was launched.
Process-control tests ran with approved sandbox escalation because the sandbox denies `ps`.

Fault tests cover commit boundaries, saved-result/response loss, corrupt records, unknown physical
work, concurrent duplicate commands, cancellation while locked, descendants, supervisor death,
failed stops, wrong-generation process identities, and failed confirmation without reselection.
Reports are read without model calls or private observation access. Their stored Markdown links
resolve to immutable outputs and complete evaluation/check records.

## Measured-data qualification

The final evidence is retained under `outputs/campaign-qualification-v3`. Its
[machine-readable summary](part-2-workflow-contracts-qualification.json) records identities, package
versions, counts, metrics and limits. `frozen.json` and each campaign's private source bundle retain
the exact source/lock snapshot and invocation. The recorded Git revision is the base commit, not a
claim that these uncommitted changes were committed there. Archived file hashes identify the code.

Final round: 80 confirmed executions, no unresolved attempts:

| Work | Executions |
| --- | ---: |
| Direct hydrology | 38 |
| CLI hydrology with bounded resume | 38 |
| Fixed routing reference | 2 |
| Supervised direct-kernel parity oracles | 2 |

Each hydrology campaign used two defaults, 32 Sobol fitting calls, two selected comparison calls
and two future-precipitation perturbations. Fitting used seed 17 and 16 evaluations for each PET
family. Defaults were separate. The two entry points produced identical scientific decisions and
configuration/metric records. Independent reconstruction matched every metric, balance check and
causality prefix. Routing predictions and the gamma decision matched the saved Part 1 reference.

The qualifier limits physical starts through invocation allowances without changing scientific
campaign or child budgets. Its final round reserved 80 starts after 160 prior starts, for a
cumulative ceiling and actual count of 240, below 320. All three rounds remain on disk. The first
was followed by a copied-source provenance repair. The second was followed by a report-link repair.
Acceptance tolerances, splits, model equations, search spaces and seeds were not changed.

Verification without additional model execution:

```sh
pixi run python -m examples.campaign_contracts.qualify \
  --verify --output outputs/campaign-qualification-v3
```

A fresh qualification requires a new output directory and checks prior charged/uncertain starts
against the cumulative ceiling before launching anything. Recreating this entire 80-call round
would consume the remaining 80 executions in the same evidence root. The qualifier refuses any
reservation that would exceed the cumulative ceiling. Reading or verifying existing artifacts
requires no new model starts.

## Scientific interpretation

On the exposed October-December 2019 development comparison:

| Configuration | RMSE (mm/day) | KGE | Bias (mm/day) | NSE |
| --- | ---: | ---: | ---: | ---: |
| Fixed Hamon | 5.2915 | -1.1631 | 2.2142 | -5.3572 |
| Calibrated Hamon | 3.4512 | -0.3776 | 2.1626 | -1.7043 |
| Fixed Hargreaves | 4.7009 | -0.8261 | 1.4900 | -4.0174 |
| Calibrated Hargreaves | 3.1378 | -0.1238 | 1.6292 | -1.2355 |

The fixed Hargreaves, calibrated Hamon and calibrated Hargreaves pair comparisons each pass the
predeclared relative rules. The calibrated Hargreaves configuration is selected. All daily
conservation checks pass, with maximum absolute residual `2.1316282072803006e-13` mm including
the perturbations. These facts do not establish predictive adequacy: development NSE and KGE
remain negative. The cache was already exposed and lacks original HTTP responses/quality flags.
The result is workflow qualification, not scientific generalization or independent confirmation.
Every measured campaign reports `confirmation_not_attempted`.

Strict token ceilings, other providers, production agent roles, arbitrary generated-code admission,
automatic ML training, general DAG/harness redesign, host plugins, cloud execution and a web app
remain deferred. All new APIs and all BO backends remain experimental.
