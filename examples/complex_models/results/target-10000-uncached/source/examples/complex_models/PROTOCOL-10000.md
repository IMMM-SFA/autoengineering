# Extension to 10000 target calls

Registered before the extended target runs. The user authorized raising the
200-call cap to 10000 and regenerating RESULTS.md on 2026-09-05.

Keep the five existing model definitions, parameter bounds, objective functions,
methods, seeds 3-7, initialization, stopping targets and test splits unchanged.
The fixed 96-call matrix and its 12/24/48/96 checkpoints remain historical evidence.
Run a new target matrix at results/target-10000. Never mutate the old studies or
resume them with a changed budget. Stop at the first observed target crossing,
backend termination or 10000 attempted calls. Failed attempts consume budget.
The maximum is 75 * 10000 = 750000 primary calls; early stopping should reduce it.

Compare each new trajectory's actions, statuses and outcomes with all of its old
200-cap trajectory. Preserve exact historical source files under history/a262556
and existing source snapshots. Report mismatches as failures. Targets remain
hash-verified against their original source ledgers. Test scoring and numeric
audits are diagnostic calls outside optimizer budgets. Do not relax targets or
alter the optimizer policy after seeing extended outcomes.

The new pvlib/OEDI, PyWake/TOPFARM and HOPP chains have separate component-swap
comparisons under examples/open_chains. They use measured power RMSE, modeled
energy, and scenario revenue respectively. Run their real integrations and full
comparisons, and include their evidence in the regenerated report. They are not
additional RMSE domains in the existing frozen benchmark. Finite candidate lists
terminate at exhaustion rather than repeating configurations to fill a cap.

BO still fits all successful observations. Its dense diagnostics and repeated
ledger validation can make large runs expensive. Keep costs and termination
states visible. No remote compute or artificial delays. Primary target runs are
sequential with one Torch CPU thread. Run full comparisons and tests separately
from the target matrix to avoid contaminating its timing measurements.
