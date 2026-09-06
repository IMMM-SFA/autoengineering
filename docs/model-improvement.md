# Choosing a model improvement

We need criteria for choosing an appropriate model change. This guide proposes a decision process
based on data availability, computational complexity, and potential system improvement. It is a
design proposal, not an implemented selector or a validated universal scoring rule.

Start with a stated failure or cost problem. More flexible models are worth considering when the
data support them and a bounded experiment can show a useful gain over simpler alternatives.
Retaining the current model is a valid outcome.

## Compare the available changes

The rows are options, not a required progression. The examples name method families, not package
recommendations or claims that one family will perform better.

| Change | Data needed | Compute to account for | Reason to test it |
| --- | --- | --- | --- |
| Tune existing parameters | Observations or reference outputs that constrain the parameters and objective. | Complete model evaluations and optimizer overhead. | The structure appears adequate, but plausible parameter values remain untested. |
| Swap a parameterization | Inputs required by the alternative and evidence for the affected process. | Adapter development, calibration, and system evaluation. | A known structural assumption plausibly explains the error. |
| Use a simple statistical model | Aligned predictors and responses covering the intended application. | Fitting, resampling, and inference for a regression, correction, or other simple baseline. | A simple relationship or systematic residual pattern could explain a useful part of the error. |
| Use basic machine learning | Representative labeled data, valid predictors, and separate evaluation groups or periods. | Feature preparation, tuning, repeated fits, memory, and inference. | A bounded pilot can test nonlinear relationships missed by the simpler baselines. |
| Use a full surrogate deep learning model | Sufficient representative simulation runs or observations, with coverage of intended regimes. | Training-data generation, accelerator time if needed, tuning, validation, storage, and retraining. | Repeated expensive evaluations or complex outputs may justify the training investment. |

A statistical or learned model may replace one component, correct a residual, or emulate the whole
system. Record which role it serves. Training on simulator output supports a claim about simulator
fidelity. A claim about the physical system requires appropriate observational evaluation.

## Eligibility comes before ranking

For each option, record the following in a candidate assessment linked from the research brief:

| Criterion | Evidence to record | Decision when evidence is missing |
| --- | --- | --- |
| Data availability | Source, access, coverage, missingness, measurement error, effective independent samples, and availability at inference time. | Mark blocked or conditional on acquiring the missing data. |
| Comparison validity | Fixed baseline, target, training and validation split, held-out test, and treatment of temporal, spatial, or grouped dependence. | Design the comparison before tuning or training. |
| Interface and scientific validity | Ports, units, time support, state, required inputs, conservation checks, and domain restrictions. | Repair the adapter or reject the candidate before performance comparisons. |
| Computational feasibility | Data generation, training, tuning, evaluation, deployment, memory, and expected number of uses. | Reject an unaffordable candidate or reduce the pilot without changing its question. |
| Potential improvement | Diagnosed failure, relevant sources, pilot evidence, plausible terminal gain, and uncertainty. | Label the benefit unknown and bound the cost of learning more. |

Do not equate row count with independent information or choose a deep model using a universal
sample-count threshold. Assess coverage and learning curves for the actual task. Reserve evaluation
data before selecting features, models, or hyperparameters. Repeatedly consulting a held-out test
turns it into selection data.

## Weigh benefit against cost

First remove candidates that cannot meet the data, interface, or resource requirements. Compare the
remaining candidates on expected terminal gain, uncertainty, and total cost. An option dominated by
another option on both gain and cost needs a separate scientific reason to remain in the pilot.

For a single declared objective, a possible assessment is:

```text
expected net value = probability of a useful gain * value of that gain
                     - data acquisition and preparation cost
                     - implementation, training, and search cost
                     - expected execution and maintenance cost
```

Use this expression only when benefits and costs can be stated in compatible units. Otherwise show
a comparison table and a Pareto frontier. Do not hide incompatible quantities inside an arbitrary
weighted score. If a study uses weights, declare them before comparing candidates and check whether
reasonable alternatives change the ranking. Record uncertainty ranges and the evidence behind the
probability and gain estimates. Unsupported estimates should remain unknown.

For a surrogate intended to save compute, check the proposed break-even condition:

```text
data generation + training + validation + expected retraining cost
    < expected future uses * (original execution cost - surrogate execution cost)
```

Evaluate both sides in the same cost unit and include optimizer overhead where relevant. Passing
this cost comparison still requires acceptable fidelity, constraints, and behavior across the
intended domain. A faster inaccurate surrogate is not an accepted improvement.

## Run a bounded pilot

1. Freeze the baseline, data splits, system objective, constraints, budget, and minimum useful gain.
2. Compare the proposed method with a simple alternative using the same evaluation data and a
   declared compute budget. Report actual cost as well as model evaluations.
3. Check component fit, terminal system performance, scientific invariants, and relevant regimes.
   For stochastic methods, include repeat seeds and uncertainty in the comparison.
4. Retain the method only if it meets the declared gain and constraint criteria. Report increases in
   complexity, runtime, or data dependence alongside improvements.
5. Stop when the budget is spent, the method lacks needed data, or the pilot does not justify more
   work. Preserve negative results and explain whether to retain the baseline or collect evidence.

For example, a component with little local observational support might justify a bounded
parameterization comparison before a learned replacement. An expensive simulator used many times
might justify a surrogate pilot if training coverage and the break-even calculation support it.
These are conditional design examples, not findings from the checked benchmarks.

## Connection to the workflow

Deep research supplies the rationale, alternatives, and data requirements. An executable candidate
enters the replacement loop. A parameterized evaluator enters BO. Training, data splitting,
resource estimation, and acceptance checks beyond the existing interfaces must currently be
implemented by the caller.

The current `rank_opportunities` heuristic does not perform this assessment. BO acquisition scores
do not choose among these modeling families. Implementing and validating that selection process is
part of the [roadmap](roadmap.md).
