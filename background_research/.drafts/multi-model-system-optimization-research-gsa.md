# Attribution in multi-model chains: GSA, Shapley effects, and model discrepancy

*Researcher brief T2 for `autoengineering`. Sibling briefs cover Bayesian and multi-objective optimisation; this memo covers the attribution slice — how to decide **which component in a chain is responsible for the sim-obs gap** and therefore which to swap next.*

## Evidence table

| # | Source | URL | Key claim | Type | Confidence |
|---|--------|-----|-----------|------|------------|
| 1 | Sobol' (2001), *Global sensitivity indices for nonlinear mathematical models…*, MATCOM | https://doi.org/10.1016/S0378-4754(00)00270-6 | Establishes the variance-based (Sobol') decomposition and Monte Carlo estimators for first-order and total-effect sensitivity indices. | primary | high |
| 2 | Saltelli, Annoni, Azzini, Campolongo, Ratto, Tarantola (2010), *Variance based sensitivity analysis of model output: design and estimator for the total sensitivity index*, CPC | https://doi.org/10.1016/j.cpc.2009.09.018 | Gives the modern "Saltelli" pick-and-freeze design used by SALib/UQLab for computing $S_i$ and $S_{T_i}$. | primary | high |
| 3 | Homma & Saltelli (1996), *Importance measures in global sensitivity analysis of nonlinear models*, RESS | http://www.andreasaltelli.eu/file/repository/Homma_Saltelli_RESS.pdf | Introduces the total-effect index; PDF-only. | primary (PDF-only) | high |
| 4 | Owen (2014), *Sobol' indices and Shapley value*, SIAM/ASA JUQ | https://doi.org/10.1137/130936233 | Proposes Shapley effects for GSA: uniquely apportions variance among inputs, always summing to $\mathrm{Var}(Y)$. | primary | high |
| 5 | Song, Nelson, Staum (2016), *Shapley effects for global sensitivity analysis: theory and computation*, SIAM/ASA JUQ | https://doi.org/10.1137/15M1048070 | Shows first-order and total Sobol' indices sandwich the Shapley effect and gives permutation-based estimators; the operational reference. | primary | high |
| 6 | Iooss & Prieur (2019), *Shapley effects for sensitivity analysis with correlated inputs…*, IJUQ | https://doi.org/10.1615/Int.J.UncertaintyQuantification.2019028372 | Compares Shapley effects to Sobol' under dependence, gives numerical estimators and hydrology/nuclear applications. Preprint: https://inria.hal.science/hal-01556303v7/document | primary | high |
| 7 | Broto, Bachoc, Depecker (2018), *Shapley effects for sensitivity analysis with dependent inputs: bootstrap and kriging-based algorithms*, arXiv | https://arxiv.org/abs/1801.03300 | Practical estimators when inputs are dependent and the model is expensive (kriging surrogate + bootstrap CIs). | primary | high |
| 8 | Kennedy & O'Hagan (2001), *Bayesian calibration of computer models*, JRSS-B | https://doi.org/10.1111/1467-9868.00294 | Canonical decomposition $z(x) = \eta(x,\theta) + \delta(x) + \varepsilon$ separating parameter calibration from model discrepancy $\delta$. Paywalled — cite DOI only. | primary (paywalled) | high |
| 9 | Higdon, Gattiker, Williams, Rightley (2008), *Computer model calibration using high-dimensional output*, JASA | https://doi.org/10.1198/016214507000000888 | Extends K–O'H to functional/high-dimensional outputs via GP + basis representations; standard for gridded/time-series simulators. | primary | high |
| 10 | Higdon, Kennedy, Cavendish, Cafeo, Ryne (2004), *Combining field data and computer simulations for calibration and prediction*, SIAM J. Sci. Comput. | https://doi.org/10.1137/S1064827503426693 | Earlier K–O'H extension; MCMC for GP emulator + discrepancy. | primary | high |
| 11 | Brynjarsdóttir & O'Hagan (2014), *Learning about physical parameters: the importance of model discrepancy*, Inverse Problems 30, 114007 | https://doi.org/10.1088/0266-5611/30/11/114007 | Shows ignoring $\delta(x)$ yields biased, over-confident parameter estimates; discusses informed priors on discrepancy. | primary | high |
| 12 | Herman & Usher (2017), *SALib: an open-source Python library for sensitivity analysis*, JOSS | https://doi.org/10.21105/joss.00097 (docs: https://salib.readthedocs.io/) | Reference Python implementation of Sobol', Morris, FAST, DGSM, PAWN, HDMR, delta. | primary | high |
| 13 | Marelli & Sudret, *UQLab* (ETH Zürich) | https://www.uqlab.com/ | MATLAB/Python framework with Sobol', Shapley, PCE, Kriging surrogates for GSA of expensive simulators. | primary | high |
| 14 | Friedli et al. (2019/2022), *Network uncertainty quantification for analysis of multi-component systems*, ASME JVVUQ | https://doi.org/10.1115/1.4055688 (arXiv preprint: https://arxiv.org/abs/1908.11476) | Decomposes system-level UQ into per-component subproblems and propagates through the DAG — closest analogue in UQ to `autoengineering`'s use case. | primary | high |
| 15 | Cho, Zhang, Zhou (2025), *Attributing forecast gaps to component models in complex model suites*, arXiv | https://arxiv.org/abs/2606.21539 | Formalises the "gap attribution" problem for chained financial/ML models — evidence the general chain-attribution problem is still recognised as open. | primary | medium (very recent) |
| 16 | Peña et al. (2024), *Quantifying cascading uncertainty in compound flood modeling with linked process-based and ML models*, HESS | https://hess.copernicus.org/articles/28/2531/2024/ | Cascading-uncertainty analysis across a linked hydrology/hydrodynamics/ML chain; typical of the empirical state of the art in earth-system chains. | primary | medium |
| 17 | Wagener, Reinecke, Pianosi (2022) / Pianosi et al. (2016), sensitivity-of-hydrologic-models review | https://doi.org/10.1002/wat2.1569 (see also Pianosi et al. 2016, https://doi.org/10.1016/j.envsoft.2016.02.008) | Reviews of GSA practice in hydrology; document why practitioners mix screening (Morris), variance-based (Sobol'), and moment-independent (PAWN, delta) methods. | secondary | medium |

## Findings (~900 words)

**1. The Sobol'/variance-based backbone.** The dominant "global" answer to *which input matters* is Sobol's ANOVA-style variance decomposition [1]. For scalar output $Y = f(X_1,\ldots,X_d)$ with independent inputs, one writes $\mathrm{Var}(Y) = \sum_i V_i + \sum_{i<j} V_{ij} + \cdots$ and defines the first-order index $S_i = V_i/\mathrm{Var}(Y)$ and total-effect index $S_{T_i} = 1 - V_{\sim i}/\mathrm{Var}(Y)$ (Homma & Saltelli 1996 [3]). The workhorse pick-and-freeze estimator with $N(d+2)$ model evaluations comes from Saltelli et al. 2010 [2]. This is what SALib [12], UQLab [13], and `scipy.stats.sobol_indices` compute, and Pianosi et al.'s hydrology review [17] documents its ubiquity in the earth-science modelling literature.

**2. Where Sobol' breaks — and Shapley effects.** Sobol' indices assume input independence. When inputs are correlated (e.g., precipitation and temperature errors upstream of a runoff model, or PET-model parameters correlated with soil-moisture-store parameters), the ANOVA decomposition is not unique and $\sum_i S_i \neq 1$; interaction/correlation effects can be double-counted or hidden. Owen (2014) [4] proposed borrowing the Shapley value from cooperative game theory: treat each input as a "player" whose marginal contribution to $\mathrm{Var}(Y)$ is averaged over all input orderings. The resulting **Shapley effect** $\phi_i$ is always non-negative and sums exactly to $\mathrm{Var}(Y)$, even under dependence. Song, Nelson & Staum (2016) [5] gave the first computationally tractable permutation estimator and showed that under independence the Shapley effect is sandwiched between $S_i$ and $S_{T_i}$. Iooss & Prieur (2019) [6] and Broto et al. (2018) [7] provide the practitioner-facing estimators — including kriging-surrogate variants for expensive models — and the correlated-input comparisons that make Shapley effects the current state of the art for attribution under dependence.

**3. The Kennedy–O'Hagan model-discrepancy framework.** GSA answers *which input drives output variance*, but a systems-engineer swapping components asks a subtly different question: *given that our simulation $\eta$ systematically disagrees with observations $z$, which component's structural inadequacy is responsible?* Kennedy & O'Hagan (2001) [8] gave the canonical Bayesian answer: $z(x) = \eta(x,\theta) + \delta(x) + \varepsilon$, where $\eta$ is the simulator (emulated by a GP), $\theta$ are calibration parameters, $\delta$ is a **model-discrepancy** function estimated jointly with $\theta$, and $\varepsilon$ is observation noise. Higdon et al. (2004, 2008) [9,10] extended this to functional/high-dimensional outputs via basis-function GP priors — directly relevant when components exchange time series or gridded fields, as in `autoengineering`'s port types. Brynjarsdóttir & O'Hagan (2014) [11] is the essential cautionary paper: **ignoring $\delta$ makes $\theta$ estimates biased and over-confident**, so any workflow that calibrates one component at a time without a discrepancy term will systematically mis-attribute structural error to parameter values.

**4. Software.** SALib [12] is the default Python library — Sobol', Morris, FAST, DGSM, PAWN, HDMR, delta-moment-independent. It has a decoupled sample/evaluate/analyse workflow that composes naturally with an external model chain. UQLab / UQ[py]Lab [13] adds polynomial chaos and Kriging surrogates and has explicit Shapley-effect modules. In R the `sensitivity` package is the standard equivalent (not verified here beyond CRAN existence — no URL cited).

**5. The chain-attribution gap.** The literature has two mature *point* answers — GSA/Shapley effects (which input matters?) and Kennedy–O'Hagan (what is model discrepancy?) — but **neither directly answers "which component in a DAG of models is responsible for the observed sim-obs gap, given that its own inputs are themselves noisy outputs of upstream components?"** The closest existing work:

- **Network / multi-component UQ.** Friedli et al. [14] ("Network Uncertainty Quantification") explicitly decompose system-level UQ into per-component subproblems and propagate uncertainty through a DAG, with the goal that each component can use its own UQ method. This is the closest structural analogue to `autoengineering`'s graph. It is a *forward-propagation* framework, though — it does not yet incorporate observation-based discrepancy attribution per node.
- **Modular / sequential-modular sensitivity.** Older chemical-engineering work on flowsheet sensitivity (Vasudevan/Wozny et al., 1987) [see: https://doi.org/10.1016/0098-1354(87)85022-6] and modular integrated-assessment coupling (Jaeger et al. 2005, https://doi.org/10.1007/s10666-005-2361-5) propose modular sensitivity chains, but neither uses Sobol'/Shapley language and neither closes the loop with observations.
- **Cascading-uncertainty case studies.** Peña et al. (2024) [16] and the compound-flood UQ perspective (https://pmc.ncbi.nlm.nih.gov/articles/PMC9547283/) analyse how uncertainty compounds through hydrology→hydrodynamics→ML chains, but the attribution is qualitative or scenario-based rather than a formal decomposition of a residual into per-node contributions.
- **Explicit "gap attribution" formulations.** Cho et al. (2025) [15] pose the "attribute forecast gaps to component models" problem in finance/ML terms — that a 2025 paper still frames this as an open problem is itself evidence of the gap.

**Inference (not directly stated in one source):** a defensible practical recipe for `autoengineering` is (i) compute Shapley effects [5,6,7] on each component's *own* parameters using SALib/UQLab plus a Kriging surrogate; (ii) fit a Kennedy–O'Hagan discrepancy $\delta_c$ per component whose output is observable [8,11]; (iii) rank components by a composite of Shapley-total contribution to end-of-chain error variance and posterior $\|\delta_c\|$. No paper found in this scan gives that exact recipe, which is consistent with the plan's expectation that chain-level attribution is a genuine research gap.

## Sources

1. Sobol' (2001), MATCOM — https://doi.org/10.1016/S0378-4754(00)00270-6
2. Saltelli et al. (2010), CPC — https://doi.org/10.1016/j.cpc.2009.09.018
3. Homma & Saltelli (1996), RESS — http://www.andreasaltelli.eu/file/repository/Homma_Saltelli_RESS.pdf (PDF-only)
4. Owen (2014), SIAM/ASA JUQ — https://doi.org/10.1137/130936233
5. Song, Nelson & Staum (2016), SIAM/ASA JUQ — https://doi.org/10.1137/15M1048070
6. Iooss & Prieur (2019), IJUQ — https://doi.org/10.1615/Int.J.UncertaintyQuantification.2019028372 ; preprint https://inria.hal.science/hal-01556303v7/document
7. Broto, Bachoc, Depecker (2018), arXiv — https://arxiv.org/abs/1801.03300
8. Kennedy & O'Hagan (2001), JRSS-B — https://doi.org/10.1111/1467-9868.00294 (paywalled)
9. Higdon et al. (2008), JASA — https://doi.org/10.1198/016214507000000888
10. Higdon et al. (2004), SISC — https://doi.org/10.1137/S1064827503426693
11. Brynjarsdóttir & O'Hagan (2014), Inverse Problems — https://doi.org/10.1088/0266-5611/30/11/114007
12. Herman & Usher (2017), SALib, JOSS — https://doi.org/10.21105/joss.00097 ; docs https://salib.readthedocs.io/
13. Marelli & Sudret, UQLab — https://www.uqlab.com/
14. Friedli et al. (2022), ASME JVVUQ — https://doi.org/10.1115/1.4055688 ; arXiv https://arxiv.org/abs/1908.11476
15. Cho, Zhang, Zhou (2025), arXiv — https://arxiv.org/abs/2606.21539
16. Peña et al. (2024), HESS — https://hess.copernicus.org/articles/28/2531/2024/
17. Pianosi et al. (2016) / Wagener & Pianosi review — https://doi.org/10.1016/j.envsoft.2016.02.008 ; https://doi.org/10.1002/wat2.1569

## Coverage status

Checked directly (abstract or landing page read):
- Sobol' variance-based GSA foundations [1,2,3] — done.
- Shapley effects family (Owen; Song–Nelson–Staum; Iooss–Prieur; Broto et al.) [4,5,6,7] — done.
- Kennedy–O'Hagan and extensions [8,9,10,11] — done; K&O'H 2001 paywalled, not parsed per plan instruction.
- SALib and UQLab software [12,13] — done.
- Network / modular / cascading-UQ literature [14,15,16] — done, sufficient to characterise the gap.

Uncertain / not fully resolved:
- Exact status of R `sensitivity` package version — not verified with a URL, therefore not cited.
- Bayarri et al. (2007) validation framework was surfaced via arXiv 0711.3271 but not cited to keep the count focused.
- Wagener/Clark citations were surfaced generically in HESS reviews; specific Wagener & Pianosi WIREs paper cited by DOI but not read in full.

Not attempted (per plan):
- Direct PDF parsing of paywalled K&O'H 2001.
- Any fetch of `deep_research_refs.csv` — this brief is only the attribution slice.

Tasks: all four plan questions marked **done**; the "chain-level attribution is underdeveloped" note is included explicitly per the deliverable spec.
