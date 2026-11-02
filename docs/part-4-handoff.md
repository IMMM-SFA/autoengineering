# Part 4 development handoff to Part 5

Status: complete for bounded macOS ARM64 delivery. The
[completion audit](reviews/part-4-completion-audit.md) controls delivery status.
Do not interpret successful integration as independent scientific validation.

## Candidate catalogue and exposure

The solar baseline is the preserved measured-POA pvlib/OEDI chain with Faiman
plus Prilliman transience. Supplied alternatives are steady Faiman and SAPM module
temperature. The bounded campaign evaluates steady Faiman and numeric u0/u1/loss
calibration. The source implements SAPM, but that campaign's one-candidate limit
does not constitute a SAPM comparison. All use the declared CEC electrical and
Sandia inverter models with frozen equipment assumptions.

June 1-7, 2018 solar data were used for interoperability development. Fitting
labels precede June 5 and comparison labels start on June 5. Earlier 2018/2019
open-chain periods were inspected during historical development. Keep their
prior exposure. No data in these records become an untouched confirmation set.
The selected uncalibrated steady-Faiman comparison RMSE was 139.81 kW versus
142.99 kW for baseline. Calibration selected on fitting data produced 158.72 kW
on comparison and was not retained. Independent confirmation was not attempted.

The circuit is a supplied OpenMDAO resistor/diode/node engineering model with
source-current design. The BMI example is the preserved scalar daily reservoir
with three supplied inputs. These are interface/solver checks, not empirical
physical-model validation studies or predictive benchmarks.

## Conventional baselines and cost meanings

The retained Ax/Optuna/Sobol comparison uses analytic continuous, mixed and
conditional cases, three seeds, shared initial points and explicit failures.
Optuna is selected for public integration compatibility. Ax failures and stalled
cases remain evidence. Do not infer general optimizer ranking from the strongest
objective result.

The circuit compares native SLSQP, with derivatives retained, against Optuna.
Native coupled solves, solver iterations, component calls and derivative callbacks
are separate costs from top-level trials. Budgets are unmatched. Solar campaign
cost counts every physical dispatch, including supplied defaults, fitting calls
and comparison reevaluation. Failed, interrupted and uncertain work remain visible.
A framework trial entry does not authorize or prove a scientific model start.

## Limits and next scientific questions

Runtime evidence is bounded macOS ARM64. Linux remains unverified. BMI support
is scalar float64 daily exchange with explicit time semantics. CSDMS heat's
spatial grid and seconds profile is unsupported. PyMT, DAKOTA and Ray remain
need-gated. OpenMDAO wraps a whole coupled Problem, not a flattened feedback DAG.
The initial adapter profile is scalar and requires explicit units.

Resource monitoring observes sampled process-tree RSS, not an instantaneous
kernel quota. Detached escape between observations is unsupported. No paid
agents, new hosts or remote compute were required for these integrations.

Part 5 must predeclare a genuinely independent scientific question, candidate
pool, data access and untouched confirmation evidence. It must distinguish
interoperability burden reduction from optimizer quality, prediction skill and
multi-agent utility. Repeating a development score on already inspected data
cannot establish those claims.
