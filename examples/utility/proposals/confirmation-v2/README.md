# Four-task confirmation preparation

This package makes the existing final-test proposal machine readable. It does not
admit tasks, freeze a protocol or authorize execution. No observations, model runs,
fitting, scoring or LLM calls were used to construct it. A separate person
acting as custodian is not required. Trusted preparation and scoring still need a
qualified boundary from advisory workers.

| Task | Proposed reserved test | Useful-gain rule |
| --- | --- | --- |
| Hydrology | CAMELS 01491000, Daymet, discharge 2005-2014 | RMSE reduction of 5% of fixed development-baseline RMSE, in mm/day |
| Solar | PVDAQ 2107, first-inverter AC channel, 2022 | RMSE reduction of 5% of fixed development-baseline RMSE, in kW |
| Engineering | 24 authored load/ground cases, excluding three nominal-resistance cases | Mean source-power reduction of 5% of fixed development-baseline mean power, in W |
| Wind | WIND Toolkit nearest (-70.5, 41.5), 80 m, 2012-2014 | Mean energy gain of 1% of fixed development-baseline energy, in GWh |

The fractions and secondary policies come from the preserved
[final-test proposal](../../../../docs/reviews/part-5-confirmation-proposal.md).
They are proposed study judgments, not task-owner numeric declarations or values
chosen from final performance. Absolute references and gains remain null. All
four dossiers remain `blocked_draft`, with unknown exposure and null frozen
thresholds. Their preceding bytes are preserved in `previous-dossiers`.

`proposal.json` binds the original proposal, public metadata and updated dossiers
by file hashes. Its digest is
`59099fffedbc3aed4cc04b03cf1a5fb3d92678e48fdf231be74a47e5030e3c9e`.
It also records all 24 engineering forcing combinations without solving them,
secondary policies, the unfrozen 560-cell/480-adaptive-cell planning matrix and
proposed multiplicity rules. Numeric budgets and dependence methods stay unset.
`producer.py.txt` preserves the exact preparation code.

The `confirmation_choices` helper can bind an explicit positive development
baseline reference to its proposed absolute gain. It verifies the reference bytes,
metric, units, phase, route and provenance identities. Zero, invalid, mismatched
or underflowed references refuse. A reference declaration alone does not qualify
its receipt or admit the task. No real reference was fabricated in this package.
New proposal output directories must be absent, so earlier versions are preserved.

The site-2107 metadata was fetched again with a single anonymous GET, no redirect,
a 10-second timeout and a 128 KiB cap. Its 64,652 bytes match the preceding snapshot
exactly. No measurement CSV was requested. `metadata-review.json` records specific
blockers: the AC channel has no explicit source ID, module records have no inverter
join, string topology is blank, and mixed sampling plus interval code `L` remain
unqualified. No mapping was inferred from array order or inherited from site 9068.
The official [PVDAQ documentation](https://github.com/openEDI/documentation/blob/main/pvdaq.md)
describes system-dependent sampling. The [wind registry](https://registry.opendata.aws/nrel-pds-wtk/)
confirms anonymous CONUS HDF5 access. Those facts do not resolve channel timing,
source-version comparability, exposure or protected-runtime admission.

Next resolve source-specific metadata and rights, prepare separated development
and reserved artifacts without advisory label access, profile admitted development
inputs, qualify task/protected-scorer bindings, then bind absolute references,
numeric caps and the final matrix. Historical exposure stays preserved. A changed
proposal or source identity requires a successor. G1-G8 and Part 5 remain incomplete.

Verification passed 38 focused tests in 0.95 seconds with zero failures, errors or
skips. Ruff and whitespace checks passed. The source inventory records the helper,
tests and four changed dossiers. All 224 core and 315 declared runtime Python
sources remain unchanged. The full default suite was not rerun.
