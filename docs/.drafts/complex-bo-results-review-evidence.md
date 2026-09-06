# Larger-model BO evidence notes

Source: `/private/tmp/autoengineering-local-examples`, clean revision `a262556`.
Review output is isolated in `/private/tmp/autoengineering-complex-bo-review`.

Inspected:

- `examples/complex_models/README.md` and `PROTOCOL.md`.
- `examples/complex_models/results/RESULTS.md`, `verification.json`,
  `data-quality.json`, `fixed-audit.json`, and target/fixed result artifacts.
- `scripts/summarize_complex_models.py`: verified its checks and redirected
  `RESULTS` to a temporary directory of input symlinks before calling `main()`.
  Neither original report nor original trajectories were opened for writing.
- `scripts/audit_complex_models.py`: inspected objective/recommendation checks,
  vector reference scope, HYMOD balance check, and alternate solar solver.
- Fixed BO ledgers and `hydro-bo-0/backend-state.json`.

Fresh report reconstruction used the locked Pixi examples environment and exited
0. It verified 120 studies and reproduced `RESULTS.md` and `trajectories.csv`
byte identically. Output:
`/private/var/folders/fh/9cg4m7ms61135w3wnpgg71lr0000gn/T/complex-bo-review-1_8nadn9/`.

Generator checks include manifest input hashes (using the allowed frozen source
archives for workflow/README changes), matrices, ledgers versus trajectories,
earliest target crossings, caps, 72 historical prefixes, frozen target derivation,
audit ledger/result/source hashes, and data-QA hashes. The retained numerical
audits cover 8,942 attempts and 300 recommendation records. Numerical model
evaluation, optimizer execution, timing, and the historical 51-test result were
not rerun in this review.

Independent action-label counts across three fixed seeds:

| Model | Sobol labels including initialization | Adaptive BO labels |
| --- | ---: | ---: |
| hydro | 260 | 28 |
| solar | 143 | 145 |
| copper | 152 | 136 |
| hymod | 24 | 264 |
| solar_diode | 24 | 264 |

Subtract 12 initial actions for each legacy model and 24 for each new model to
recover fallback counts. Hydro seed 0's final backend snapshot reports
`warning_exhaustion_after_3_retries: ValueError: candidate_duplicate`.
This snapshot does not establish the cause of every historical fallback.

Independent review was read from `/private/tmp/bo-complex-independent-review-20260905.md`.
It checked raw medians and action labels and agreed with the interpretation.
No numerical correction was identified. No new benchmark was run by either reviewer.
