# Larger BMI models and longer search budgets

Registered on 2026-09-05 before benchmark evaluation. Base commit: `1a01a6e`.
The user authorized more complex BMI examples, fixed budgets including 48 and
96, and a 200-call cap for the target experiment. This protocol preserves all
previous results and their original targets. Local Pixi examples environment,
sequential studies, one Torch CPU thread. No artificial sleeps or remote jobs.

## Models and data

The three existing models are unchanged. Two additional chains reuse their
measured forcing, observations and exact splits; no test labels enter calibration.

- `hymod`: PET -> Pareto-distributed soil capacity -> parallel slow reservoir and
  three fast reservoirs in series. Seven search parameters: PET family, maximum
  point capacity cmax (50-1000 mm, log), capacity-shape beta (0.1-3), quickflow
  fraction alpha (0.05-0.95), daily fast release (0.1-0.9), daily slow release
  (0.001-0.15, log), PET multiplier (0.5-1.5). Mean maximum soil storage is
  cmax/(beta+1). Initialize it half full and routing reservoirs empty. Continuous
  daily state includes the original warmup. PET demand is limited by available
  soil water. Routing receives and releases inflow during the same daily step.
  Each day's precipitation equals ET + discharge + total storage change.
- `solar_diode`: effective irradiance -> Ross temperature -> De Soto parameter
  translation and Brent single-diode maximum-power solution -> PVWatts inverter. Seven
  continuous parameters: heat loss (15-60), irradiance scale (0.85-1.15), series
  resistance multiplier (0.5-2, log), shunt resistance multiplier (0.5-2, log),
  saturation current multiplier (0.3-3, log), diode thermal-voltage multiplier
  (0.8-1.2), plant loss factor (0.6-1.05). The last factor can represent gain when
  above one. Scale module watts to 2369 kW nominal DC, with the original 1910 kW
  inverter. Use a pinned representative CEC First Solar FS267 module snapshot.
  It is not the measured site's identified module. Reference bandgap settings
  retain CEC's extraction convention (EgRef 1.121, dEgdT -0.0002677), including
  for this thin-film entry. Module/cell temperature equality is an approximation.
  This is an equivalent plant calibration, not identifiable physical module
  parameter estimation. Sample-index time remains appropriate for steady state.

The new models are more complex in their states and parameter spaces, not new
independent datasets or additional modeling domains. Existing limitations remain:
Leaf River weather representativeness and legacy quality flags, a short solar
winter window and uncertain array allocation, and copper's unresolved unit scale.
Model detail does not itself establish better prediction or higher runtime.

HYMOD conceptual source: https://github.com/jdherman/hymod and the linked PDM
reference (Moore 2007). This implementation uses the stated daily discrete routing,
without snow or subdaily integration; it is not a bitwise port of that C++ model.
PV implementation uses the installed pvlib 0.15.0 functions. Method documentation:
https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.pvsystem.calcparams_desoto.html
and https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.pvsystem.singlediode.html.
The installed CEC source URL, SHA256 and numeric snapshot are in module.json.

## Fixed budgets and target construction

Run all five models with random, scrambled Sobol and whole-system BO, seeds 0-2,
to 96 calls. Freeze observed recommendations at 12, 24, 48 and 96. Compute all
held-out scores only after the full trajectory finishes. This reuses trajectory
prefixes; checkpoints are not independent trials. Verify the existing models'
first 24 actions/outcomes against the earlier 24-call matrix. Timing differs due
to the new checkpoint bookkeeping, so compare timing only within this experiment.

BO uses four initial Sobol points for existing models and eight for the new
seven-parameter models. Acquisition uses two restarts and 32 raw samples as before.
No optimizer settings, seeds or model spaces are revised from benchmark outcomes.
Retain and report backend fallbacks, failures and nonfinite outcomes.

For the three existing models, retain the exact original frozen validation targets.
For each new model, set the target to 1.05 times the lowest successful validation
RMSE across its complete 96-call fixed matrix. This target is informed by development
results, but is frozen before target-study seeds 3-7 are evaluated. Save source
ledger hashes. These targets are not global optima or scientific quality standards.

Run a separate target experiment for all five models and all three methods using
seeds 3-7. Stop after the first observed validation RMSE <= target or 200 attempts.
Count initialization and failed attempts; distinguish backend termination from cap
exhaustion. Never report a capped run as converged. Verify original target trajectories
through their former observed horizon (up to 60) using configurations and outcomes.

## Evidence, interpretation and exit

Maximum primary calls: 45 x 96 = 4320 fixed and 75 x 200 = 15000 target calls.
Fixed-budget test scoring, verification and component swaps are separate diagnostic
calls and excluded from optimizer budgets. No suite resume/budget mutation is used.
Preimport dependencies before timing. Study time includes controller and optimizer,
excludes input loading, backend construction and held-out scoring. Record cumulative
model/study time, individual runs, success fractions, successful-only median calls
with denominator, and capped computational cost. Do not rank unequal success rates
by successful-only medians or by mean capped cost alone. Report validation and test
outcomes separately. Hypothetical expensive-model savings require fewer calls to a
common target and must remain conditional on unchanged trajectories and overhead.

Check water conservation, routing impulse response and causality, solar scalar BMI
against vectorized pvlib and independent Lambert-W solutions, bounds, zero-light behavior, and held-out isolation.
Exercise real graph component swaps. Audit recorded objectives and recommendations,
source hashes, checkpoint membership, prefix equality, earliest crossings, and caps.
Run relevant tests, lint, project constraints and independent scientific review.
Save negative results and unresolved issues. Do not merge, push or alter old gates.

Before benchmark runs, a numerical microbenchmark selected pvlib max_power_point
with Brent root finding instead of computing all seven single-diode IV outputs.
The model equations and parameter space are unchanged. Independent Lambert-W
checks validate this solver choice. No validation scores informed this choice.

The slowest HYMOD reservoir has a roughly 1000-day recession time. The inherited
90-day warmup is not sufficient to establish equilibrium for every configuration.
Results are conditional on the declared initial stores, not a fully spun-up system.
The solar model uses De Soto equations with a CEC parameter snapshot; it does not
apply CEC's additional Adjust correction or claim exact CEC-model reproduction.
