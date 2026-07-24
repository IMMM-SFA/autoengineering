# Theoretical Foundations for Optimizing Systems of Compute Models

*A research memo for `autoengineering`, mapping four literatures — MDAO / coupled-simulator BO, global sensitivity and model discrepancy, decision theory and value of information, and satisficing / info-gap — onto the four-step workflow (define → validate → analyze → execute).*

## Executive summary

The `autoengineering` package asks a question that sits at the intersection of four mature but rarely-combined literatures:

> Given a directed graph of coupled compute models (each a simplified representation of reality), and validation data at one or more nodes, **which component should we improve or swap next?**

None of the reviewed fields answer that question directly. But together they supply the theoretical primitives needed to make the workflow defensible. In short:

- **Multidisciplinary Design Optimization (MDAO)** gives the *architectural* language — MDF, IDF, AAO, and distributed patterns (CO, BLISS, ATC) — for coupled compute-model systems ([Martins & Lambe 2013](https://doi.org/10.2514/1.J051895); [Martins & Ning 2021](https://doi.org/10.1017/9781108980647)), and its recent Bayesian-optimization extensions ([Tao et al. 2021](https://doi.org/10.1115/1.4050738) multi-model BO; [Kyzyurova et al. 2018](https://doi.org/10.1137/17M1157702), [Ming & Guillas 2021](https://doi.org/10.1137/20M1323771) linked and deep-GP emulators) give the *surrogate machinery* for BO over networks of expensive simulators.
- **Global sensitivity analysis and model discrepancy** give the *attribution* language: Sobol' and Shapley effects apportion output variance to inputs even under dependence ([Owen 2014](https://doi.org/10.1137/130936233); [Song, Nelson & Staum 2016](https://doi.org/10.1137/15M1048070)), and Kennedy–O'Hagan Bayesian calibration cleanly separates parameter calibration from *structural* model error δ(x) ([Kennedy & O'Hagan 2001](https://doi.org/10.1111/1467-9868.00294); [Brynjarsdóttir & O'Hagan 2014](https://doi.org/10.1088/0266-5611/30/11/114007)). The literature is thin on **chain-level** discrepancy attribution, which is precisely the gap `autoengineering` sits in (see [Friedli et al. 2022](https://doi.org/10.1115/1.4055688) for the closest forward-propagation analogue).
- **Decision theory and value of information (VoI)** give the *choice rule*: [Howard's (1966)](https://doi.org/10.1109/TSSC.1966.300074) VoI framework and its knowledge-gradient ([Frazier, Powell & Dayanik 2008](https://doi.org/10.1137/070693424)) / entropy-search descendants convert "which component to improve" into a preposterior expected-utility calculation. The closest formalization to an auto-engineering loop is a POMDP over "which component is the current bottleneck" ([Andriotis, Papakonstantinou & Chatzi 2021](https://doi.org/10.1016/j.strusafe.2020.102072)).
- **Satisficing and info-gap theory** give the *stopping rule* and an alternative framing: when a downstream threshold ("NSE ≥ 0.5", "flood probability ≤ 1%") is the actual object of interest and probability priors on model error are not credible, robust satisficing dominates expected-utility maximization ([Simon 1956](https://doi.org/10.1037/h0042769); [Ben-Haim 2019](https://doi.org/10.1007/978-3-030-05252-2_5); [Schwartz, Ben-Haim & Dacso 2011](https://doi.org/10.1111/j.1468-5914.2010.00450.x); [Ben-Haim 2008](https://doi.org/10.1115/esda2008-59029)). This is the frame that most closely matches how engineering standards are written.

The rest of this memo (a) surveys each literature in turn, (b) maps its primitives onto `autoengineering`'s four submodules, and (c) flags three genuine research gaps that a follow-on paper could plausibly fill.

---

## 1. MDAO and coupled-simulator Bayesian optimization

**Formalism.** The MDO community's canonical taxonomy of architectures for coupled compute-model systems is due to [Martins & Lambe (2013)](https://doi.org/10.2514/1.J051895) and codified in Martins & Ning's open-access textbook *[Engineering Design Optimization](https://mdobook.github.io/)* ([Cambridge 2021](https://doi.org/10.1017/9781108980647)):

- **Monolithic:** MDF (Multidisciplinary Feasible — inner MDA resolves couplings at each optimizer step), IDF (Individual Discipline Feasible — coupling variables promoted to optimizer variables + consistency constraints), AAO/SAND (states + couplings + design vars all owned by the optimizer).
- **Distributed:** Collaborative Optimization (CO; see [Roth & Kroo 2008](https://doi.org/10.1115/DETC2008-50038)), BLISS/BLISS-2000, Analytical Target Cascading (ATC), plus ASO, QSD, MDOIS variants — each with different feasibility/consistency semantics ([Martins & Lambe 2013](https://doi.org/10.2514/1.J051895)).

`autoengineering` currently assumes a feed-forward chain (implicit MDF with no feedback loops). This is a real limitation once we consider systems with feedback couplings (e.g., surface-water/groundwater, atmosphere-ocean).

**Surrogate machinery for BO over networks.** Three closely related lines matter here:

- **Multi-model Bayesian optimization** ([Tao, Van Beek, Apley & Chen 2021](https://doi.org/10.1115/1.4050738), *J. Mech. Design*; precursor [IDETC 2020](https://doi.org/10.1115/DETC2020-22651)): builds a per-subsystem surrogate and lets acquisition decide *which subsystem* to query rather than only where in the global design space. Directly analogous to `autoengineering`'s "which component to swap" question, with heterogeneous evaluation costs treated first-class.
- **Linked Gaussian-process emulators.** [Kyzyurova, Berger & Wolpert (2018)](https://doi.org/10.1137/17M1157702) derive closed-form predictive mean and variance for the composition f₂(f₁(x)) when f₁ and f₂ are each emulated independently (reference R implementation: [LinkedGASP](https://ksenia-kyzyurova.r-universe.dev/LinkedGASP)). [Ming & Guillas (2021)](https://doi.org/10.1137/20M1323771) ([arXiv:1912.09468](https://arxiv.org/abs/1912.09468)) generalize the linked-GP construction to Matérn kernels and add an iterative adaptive-design loop for systems of models.
- **Deep-GP / networked-GP emulation** ([Ming, Williamson & Guillas 2023](https://doi.org/10.1080/00401706.2022.2124311), [arXiv:2107.01590](https://arxiv.org/abs/2107.01590); [Ming & Williamson 2023](https://arxiv.org/abs/2306.01212)): turns training a deep GP into training a linked GP via stochastic imputation, and generalizes to arbitrary DAGs of models. Reference implementation: [dgpsi](https://github.com/mingdeyu/DGP).

**Multi-fidelity BO** ([Kandasamy et al. 2017](https://proceedings.mlr.press/v70/kandasamy17a/); [Poloczek, Wang & Frazier 2017](https://proceedings.neurips.cc/paper/2017/hash/df1f1d20ee86704251795841e6a9405a-Abstract.html); [Li et al. 2023 review, arXiv:2311.13050](https://arxiv.org/abs/2311.13050); see also [Wu et al. 2019](https://proceedings.mlr.press/v115/wu20a.html)) is orthogonal — it optimizes *inside* one component with a tunable fidelity knob, whereas linked-GP / multi-model BO chooses *across* components. Both are relevant to `autoengineering` but answer different sub-questions.

**Ecosystem.** [OpenMDAO](https://openmdao.org/) (NASA/UMich; framework overview: [Gray et al. 2019](https://doi.org/10.1007/s00158-019-02211-z); MAUD residual formulation with analytic derivatives: [Hwang & Martins 2018, *ACM TOMS*](https://doi.org/10.1145/3182393)), [SUAVE](https://suave.stanford.edu/) (Stanford, multi-fidelity aircraft design; [Lukaczyk et al. 2015](https://doi.org/10.2514/6.2015-3087)), [Dakota](https://dakota.sandia.gov/) (Sandia, general-purpose UQ + optimization), [SEGOMOE](https://sbarchopt.readthedocs.io/en/stable/algo/segomoe/) / [SMT](https://smt.readthedocs.io/) (ONERA + ISAE-SUPAERO, mixed-variable BO with Mixture-of-Experts surrogates; [Bartoli et al. 2017](https://doi.org/10.2514/6.2017-4433)).

**Mapping to `autoengineering`.** The `System` DAG in `autoengineering.system` is a strict subset of an XDSM diagram ([Martins & Lambe 2013](https://doi.org/10.2514/1.J051895) convention). Adopting XDSM/MDF/IDF terminology and eventually supporting feedback couplings is the natural next architectural step. The linked-GP variance decomposition ([Kyzyurova et al. 2018](https://doi.org/10.1137/17M1157702)) is the closest published mechanism for answering "which component contributes most to end-of-chain output uncertainty."

---

## 2. Attribution: global sensitivity, Shapley effects, and model discrepancy

**Sobol'/variance-based decomposition** ([Sobol' 2001](https://doi.org/10.1016/S0378-4754(00)00270-6); Homma & Saltelli 1996; [Saltelli et al. 2010](https://doi.org/10.1016/j.cpc.2009.09.018)) is the workhorse: for scalar output Y = f(X₁,…,X_d) with independent inputs, decompose Var(Y) into first-order and total-effect indices S_i and S_{T_i}. Implemented in [SALib](https://salib.readthedocs.io/) ([Herman & Usher 2017](https://doi.org/10.21105/joss.00097)) and [UQLab](https://www.uqlab.com/) (Marelli & Sudret). This is what practitioners use when they ask "which input matters most" ([Pianosi et al. 2016](https://doi.org/10.1016/j.envsoft.2016.02.008); [Wagener & Pianosi 2019](https://doi.org/10.1002/wat2.1569)).

**When Sobol' breaks:** under input dependence the decomposition is not unique and Σ S_i ≠ 1. **Shapley effects** ([Owen 2014](https://doi.org/10.1137/130936233); [Song, Nelson & Staum 2016](https://doi.org/10.1137/15M1048070); [Iooss & Prieur 2019](https://doi.org/10.1615/Int.J.UncertaintyQuantification.2019028372); [Broto, Bachoc & Depecker 2018](https://arxiv.org/abs/1801.03300)) apply the cooperative-game-theoretic Shapley value to variance attribution: each input is a "player" and its Shapley effect φ_i is the average marginal contribution to Var(Y) across all orderings. Shapley effects are always non-negative and sum exactly to Var(Y) even under dependence. Under independence, φ_i is sandwiched between S_i and S_{T_i} ([Song, Nelson & Staum 2016](https://doi.org/10.1137/15M1048070)).

**Model discrepancy** ([Kennedy & O'Hagan 2001](https://doi.org/10.1111/1467-9868.00294), *JRSS-B*): the canonical Bayesian framework for computer-model calibration writes

$$z(x) = \eta(x, \theta) + \delta(x) + \varepsilon$$

separating the simulator η (typically emulated by a GP), calibration parameters θ, a **model-discrepancy** function δ (also emulated by a GP), and observation noise ε. [Higdon et al. (2008, *JASA*)](https://doi.org/10.1198/016214507000000888) extends KOH to functional / gridded outputs via basis-function GP priors (see also the earlier [Higdon et al. 2004, *SIAM J. Sci. Comput.*](https://doi.org/10.1137/S1064827503426693)) — directly relevant when `autoengineering` components exchange time series (its `timeseries` port type). **[Brynjarsdóttir & O'Hagan (2014)](https://doi.org/10.1088/0266-5611/30/11/114007)** is the cautionary paper: ignoring δ makes θ estimates biased and over-confident, so any workflow that "just fits parameters" without a discrepancy term will mis-attribute structural error to parameter values.

**The chain-attribution gap.** GSA answers "which input matters" and Kennedy–O'Hagan answers "what is model discrepancy for one simulator," but the literature is thin on **which component in a DAG of coupled models is responsible for a system-level sim-obs gap, given that each component's inputs are themselves noisy outputs of upstream components.** Closest existing work:

- **Network / multi-component UQ** ([Friedli et al. 2022, ASME JVVUQ](https://doi.org/10.1115/1.4055688); [arXiv:1908.11476](https://arxiv.org/abs/1908.11476)): forward-propagates per-component UQ through the DAG, without observation-based attribution.
- **Modular sensitivity in flowsheets** ([Vasudevan & Wozny 1987](https://doi.org/10.1016/0098-1354(87)85022-6); [Jaeger et al. 2005](https://doi.org/10.1007/s10666-005-2361-5) on integrated-assessment coupling): modular sensitivity chains without Sobol'/Shapley language and without closing the loop with observations.
- **Cascading-uncertainty case studies** ([Muñoz, Moftakhari & Moradkhani 2024, HESS](https://doi.org/10.5194/hess-28-2531-2024) on compound flooding): quantify how uncertainty compounds through linked process-based + ML chains, but not as a formal per-node attribution decomposition.

**Practical recipe (inferred, not directly published):** (i) Shapley effects on each component's own parameters using a Kriging surrogate ([Song, Nelson & Staum 2016](https://doi.org/10.1137/15M1048070); [Broto et al. 2018](https://arxiv.org/abs/1801.03300)); (ii) fit a [Kennedy–O'Hagan (2001)](https://doi.org/10.1111/1467-9868.00294) δ_c per observable component; (iii) rank components by a composite of Shapley-total contribution to end-of-chain error variance and posterior ‖δ_c‖. This is a plausible synthesis of the two literatures but has not, to my knowledge, been published as a single procedure.

**Mapping to `autoengineering`.** The current `rank_opportunities` in `autoengineering.analyze` uses a heuristic distance-from-threshold score. A defensible replacement would combine Shapley-effect attribution on component parameters with a Kennedy–O'Hagan discrepancy estimate on each observable node — exactly the recipe above.

---

## 3. Decision theory and value of information

**Bayesian decision-theoretic frame.** [Raiffa & Schlaifer (1961)](https://www.wiley.com/en-gb/Applied+Statistical+Decision+Theory-p-9780471383499) and [Berger (1985)](https://link.springer.com/book/10.1007/978-1-4757-4286-2) give the canonical setup: given prior p(θ), action set A, utility u(a, θ), pick a* = argmax_a E[u(a, θ)]. When data d is available at cost c, the **preposterior expected utility** is E_d[max_a E_{p(θ|d)}[u(a, θ)]], and the **value of sample information (VoI)** is this minus max_a E[u(a, θ)]; [Howard (1966)](https://doi.org/10.1109/TSSC.1966.300074) formalized this and the notion of value of clairvoyance.

**Bayesian experimental design as decision theory.** [Chaloner & Verdinelli (1995, *Statistical Science*)](https://doi.org/10.1214/ss/1177009939) show that A-, D-, c-optimality are all special cases of expected-utility maximization. [Ryan et al. (2016)](https://doi.org/10.1111/insr.12107) catalog the computational machinery (nested MC, ABC, sequential MC) needed when u is high-dimensional or the likelihood only accessible via a simulator — exactly the regime of coupled compute-model chains. [Rainforth et al. (2024, *Statistical Science*)](https://doi.org/10.1214/23-STS915) update this with variational EIG bounds and gradient-based BOED; [Foster et al. (2021 ICML, Deep Adaptive Design)](https://arxiv.org/abs/2103.02438) amortize the design policy into a network for real-time sequential experimentation.

**Information-theoretic acquisition functions.** Within BO, the modern taxonomy splits by utility choice:

- **Knowledge-gradient (KG)** ([Frazier, Powell & Dayanik 2008, *SIAM J. Control Optim.*](https://doi.org/10.1137/070693424)): utility = max of the posterior mean over the *decision* space. KG is directly a one-step VoI on the terminal decision. This is the acquisition most naturally aligned with "which component should I improve next?" — decision space = candidate replacement components; posterior mean = expected system performance after each hypothetical swap.
- **Entropy Search** ([Hennig & Schuler 2012](https://www.jmlr.org/papers/v13/hennig12a.html)) / **Predictive ES** ([Hernández-Lobato et al. 2014](https://arxiv.org/abs/1406.2541)) / **Max-value ES** ([Wang & Jegelka 2017](https://arxiv.org/abs/1703.01968)): utility framed as entropy reduction over argmax or max-value.

For `autoengineering`, KG is the closest fit because the decision is a discrete "swap component X for candidate Y." MES/PES become attractive when the decision is continuous.

**VoI in engineering practice.** The structural-reliability community has the most developed applied VoI literature: [Straub (2014, *Structural Safety*)](https://doi.org/10.1016/j.strusafe.2013.08.006) uses FORM/SORM to compute monitoring-vs-no-monitoring VoI; [Konakli, Sudret & Faber (2016)](https://doi.org/10.1061/AJRUA6.0000850) use polynomial chaos surrogates to make preposterior expectations tractable in lifecycle maintenance; **[Andriotis, Papakonstantinou & Chatzi (2021, *Structural Safety*)](https://doi.org/10.1016/j.strusafe.2020.102072)** prove that a POMDP policy inherently realizes non-negative VoI at every observation step. Their POMDP is set up for structural health monitoring; the mapping below to model-swap decisions is *our* proposed adaptation, not a claim from the paper:

- state = latent discrepancy contribution of each component,
- observation = validation metrics on terminal / intermediate nodes,
- action = which component to swap (or "stop"), with cost,
- reward = negative terminal-node discrepancy − swap cost.

A myopic (one-step) approximation is KG over the swap set ([Frazier, Powell & Dayanik 2008](https://doi.org/10.1137/070693424)). If replacement candidates are themselves uncertain (e.g., an unfit sub-model), the acquisition becomes a nested BOED problem à la [Rainforth et al. 2024](https://doi.org/10.1214/23-STS915) / [Foster et al. 2021](https://arxiv.org/abs/2103.02438).

**Stopping rules.** [Ishibashi et al. (2023 AISTATS)](https://proceedings.mlr.press/v206/ishibashi23a.html) provide an optimality-guaranteed BO stopping rule based on the expected simple-regret gap; [Xie et al. (2025, arXiv:2507.12453)](https://arxiv.org/abs/2507.12453) adds an explicit cost term and expected-cost-adjusted-simple-regret guarantees (accepted at ICML 2026). Both are reservation-price stopping rules directly portable to `autoengineering`.

**Mapping to `autoengineering`.** `autoengineering.execute.swap_component` currently returns a new `System` with one component replaced; a defensible auto-engineering loop wraps this in a KG-over-swap-set acquisition, evaluates each candidate swap via propagated posterior expectation on the terminal metric, and terminates via a marginal-VoI ≤ marginal-cost stopping rule.

---

## 4. Satisficing, bounded rationality, and info-gap

**Simon's satisficing** ([Simon 1955 *QJE*](https://doi.org/10.2307/1884852); [Simon 1956 *Psych. Review*](https://doi.org/10.1037/h0042769)): real decision-makers have bounded information and compute; the rational strategy is to search until an aspiration-level threshold is reached and stop. "Organisms adapt well enough to 'satisfice'; they do not, in general, 'optimize'" ([Simon 1956](https://doi.org/10.1037/h0042769); see also the [SEP entry on Bounded Rationality](https://plato.stanford.edu/archives/win2025/entries/bounded-rationality/)). [Manski (2017, *Theory and Decision*)](https://doi.org/10.1007/s11238-017-9592-1) argues via a simple minimax-regret comparison that satisficing can dominate optimization when deliberation is costly, giving satisficing normative footing beyond a mere heuristic.

**[Byron (1998 *Ethics*](https://doi.org/10.1086/233874); [ed. 2004 Cambridge volume](https://doi.org/10.1017/CBO9780511617058))** argues that satisficing is a distinct normative account of practical reason, not merely an approximation to maximizing.

**Info-gap decision theory (IGDT)** ([Ben-Haim 2019 Springer chapter](https://doi.org/10.1007/978-3-030-05252-2_5)) addresses *severe* uncertainty: a nominal model exists but its error bounds and probability structure are unknown. Two dual immunity functions are defined against a nested family of uncertainty sets around the nominal model:

- **Robustness** α̂(q, r_c): the largest horizon of uncertainty at which decision q still guarantees a minimum acceptable reward r_c.
- **Opportuneness** β̂(q, r_w): the smallest horizon at which windfall reward r_w becomes possible.

Ben-Haim's central engineering claim ([Ben-Haim 2008 ASME ESDA](https://doi.org/10.1115/esda2008-59029); [Ben-Haim 2019](https://doi.org/10.1007/978-3-030-05252-2_5)): a design that optimizes performance under the nominal model has **zero immunity** to any deviation of reality from that model. Robustness is *bought* by relaxing aspiration. This is why engineering codes specify inequality constraints ("survive the 100-yr event", "carry load ≥ 1.5×") rather than constrained-optimal designs ([Ben-Haim 2008](https://doi.org/10.1115/esda2008-59029)).

**Robust satisficing** ([Schwartz, Ben-Haim & Dacso 2011, *J. Theory Soc. Behav.*](https://doi.org/10.1111/j.1468-5914.2010.00450.x)): choose the alternative that maximizes robustness (in the info-gap sense) subject to meeting a critical aspiration. This is the appropriate normative standard when the probability model itself is ambiguous — the Knightian setting where expected-utility maximization requires priors the decision-maker doesn't actually have.

**Applications converging on satisficing.** [Matrosov, Padula & Harou (2013, *J. Hydrology*)](https://www.sciencedirect.com/science/article/pii/S0022169413002060) apply both IGDT and Robust Decision Making ([Lempert 2019, Springer chapter](https://doi.org/10.1007/978-3-030-05252-2_2)) to London water supply; [Hall et al. (2012, *Risk Analysis*)](https://doi.org/10.1111/j.1539-6924.2012.01802.x) compare RDM and IGDT on climate mitigation. Both surface the same "meet threshold across the widest swath of futures" strategies as robust — not the same ones as expected-NPV-maximization.

**When satisficing is the right frame** (rather than Pareto or expected utility) ([Simon 1956](https://doi.org/10.1037/h0042769); [Ben-Haim 2019](https://doi.org/10.1007/978-3-030-05252-2_5); [Schwartz, Ben-Haim & Dacso 2011](https://doi.org/10.1111/j.1468-5914.2010.00450.x); [Hall et al. 2012](https://doi.org/10.1111/j.1539-6924.2012.01802.x)):

- The probability model over model-error / forcings / parameters is not credible.
- A natural externally-imposed threshold ("NSE ≥ 0.5", "peak error ≤ X mm/day") is the actual object of interest to a downstream decision-maker.
- Deliberation cost is high and marginal skill improvement past the threshold has diminishing operational value.
- The chain is applied across many sites/scenarios and the decision-maker cares about worst-case or reliability, not ensemble mean.

**Mapping to `autoengineering`.** `validate_arrays` already returns pass/warn/fail against a threshold — this is a satisficing-native primitive. Concrete implications if the framing shifts from "maximize skill" to "meet threshold":

1. `rank_opportunities` should score components by *change in threshold-satisfaction probability across an uncertainty ensemble*, not distance from a nominal target ([Schwartz, Ben-Haim & Dacso 2011](https://doi.org/10.1111/j.1468-5914.2010.00450.x)).
2. Stop rule: halt as soon as all component thresholds pass and end-to-end skill exceeds aspiration; additional swaps only justified if they buy robustness α̂, not additional nominal skill ([Ben-Haim 2008](https://doi.org/10.1115/esda2008-59029); [Ben-Haim 2019](https://doi.org/10.1007/978-3-030-05252-2_5)).
3. Add info-gap robustness α̂ as a first-class metric alongside RMSE/NSE/KGE ([Ben-Haim 2019](https://doi.org/10.1007/978-3-030-05252-2_5)).
4. Validate each component on an *uncertainty ensemble* (bootstrap of forcings, alternative parameterizations), not a single observed record — the RDM stress-test pattern ([Lempert 2019](https://doi.org/10.1007/978-3-030-05252-2_2); [Hall et al. 2012](https://doi.org/10.1111/j.1539-6924.2012.01802.x)).
5. Elicit aspiration thresholds explicitly at the start of the workflow ([Simon 1956](https://doi.org/10.1037/h0042769); [Byron 1998](https://doi.org/10.1086/233874)); the YAML `system.yaml` is the natural place for per-metric aspirations.
6. Cost-aware search: per-component "cost of swap" (runtime, effort, license) becomes first-class input to ranking so the loop prefers cheap threshold-crossing swaps over expensive skill-squeezing swaps ([Simon 1955](https://doi.org/10.2307/1884852); [Manski 2017](https://doi.org/10.1007/s11238-017-9592-1)).

---

## 5. Consolidated mapping onto the four `autoengineering` submodules

| Submodule                | Current primitive                          | Theoretical primitive imported                                                                                                     | Key sources                                                                             |
|--------------------------|--------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------|
| `system/` (define)      | DAG of components with typed ports        | XDSM diagram / MDF, IDF, AAO taxonomy; eventual feedback-coupling semantics                                                       | [Martins & Lambe 2013](https://doi.org/10.2514/1.J051895); [Martins & Ning 2021](https://doi.org/10.1017/9781108980647); [Gray et al. OpenMDAO 2019](https://doi.org/10.1007/s00158-019-02211-z)                    |
| `validate/` (validate)  | scalar metrics vs. thresholds             | Kennedy–O'Hagan discrepancy δ(x) as first-class output; ensemble validation vs. single record                                     | [Kennedy & O'Hagan 2001](https://doi.org/10.1111/1467-9868.00294); [Higdon et al. 2004](https://doi.org/10.1137/S1064827503426693)/[2008](https://doi.org/10.1198/016214507000000888); [Brynjarsdóttir & O'Hagan 2014](https://doi.org/10.1088/0266-5611/30/11/114007)                 |
| `analyze/` (rank)       | heuristic improvement-potential score     | Shapley effects on component parameters + posterior ‖δ_c‖; KG over candidate swaps; robust-satisficing threshold-probability score | [Owen 2014](https://doi.org/10.1137/130936233); [Song–Nelson–Staum 2016](https://doi.org/10.1137/15M1048070); [Frazier–Powell–Dayanik 2008](https://doi.org/10.1137/070693424); [Schwartz–Ben-Haim–Dacso 2011](https://doi.org/10.1111/j.1468-5914.2010.00450.x) |
| `execute/` (swap)       | pure `swap_component` returning new System | Sequential decision loop with KG or POMDP-style policy; marginal-VoI ≤ marginal-cost stopping                                     | [Andriotis–Papakonstantinou–Chatzi 2021](https://doi.org/10.1016/j.strusafe.2020.102072); [Ishibashi et al. 2023](https://proceedings.mlr.press/v206/ishibashi23a.html); [Xie et al. 2025](https://arxiv.org/abs/2507.12453)               |

---

## 6. Open questions and research gaps

1. **Chain-level discrepancy attribution.** We are not aware of a published procedure that combines Shapley effects with Kennedy–O'Hagan discrepancy on a DAG of models to rank components by their contribution to observed end-of-chain error. [Friedli et al. (2022)](https://doi.org/10.1115/1.4055688) does forward propagation of per-component UQ without observation-based attribution; older modular-sensitivity work in chemical engineering ([Vasudevan & Wozny 1987](https://doi.org/10.1016/0098-1354(87)85022-6)) and integrated assessment ([Jaeger et al. 2005](https://doi.org/10.1007/s10666-005-2361-5)) proposes modular sensitivity chains without Sobol'/Shapley language.
2. **Model-swap as experimental-design action.** BOED / VoI literature almost always treats "which measurement to run" as the design decision. Framing "which sub-model to replace" as a design decision (utility = ΔNSE or ΔP[threshold-met], cost = engineering effort) is a natural extension of [Andriotis et al. 2021](https://doi.org/10.1016/j.strusafe.2020.102072)'s POMDP formulation but has not been published as such.
3. **Coupled satisficing + BO.** Cost-aware BO stopping rules ([Xie et al. 2025](https://arxiv.org/abs/2507.12453); [Ishibashi et al. 2023](https://proceedings.mlr.press/v206/ishibashi23a.html)) and robust satisficing ([Ben-Haim 2019](https://doi.org/10.1007/978-3-030-05252-2_5); [Schwartz et al. 2011](https://doi.org/10.1111/j.1468-5914.2010.00450.x)) have not been combined into a single acquisition-plus-stopping policy for engineering model chains.

---

## Caveats and disagreements

- The **[Tao et al. 2021](https://doi.org/10.1115/1.4050738)** paper's specific per-model acquisition function is inferred from the JMD abstract; the exact weighting scheme requires the paywalled full text (research brief T1 marks this).
- Under **input dependence**, Sobol' first-order and total-effect indices lose their tidy interpretation; Shapley effects are the current best answer but come with permutation-estimator cost that scales poorly in dimension ([Owen 2014](https://doi.org/10.1137/130936233); [Song–Nelson–Staum 2016](https://doi.org/10.1137/15M1048070); [Iooss & Prieur 2019](https://doi.org/10.1615/Int.J.UncertaintyQuantification.2019028372); [Broto et al. 2018](https://arxiv.org/abs/1801.03300)).
- **Kennedy–O'Hagan** with a δ term is *identifiable* only under informative priors — [Brynjarsdóttir & O'Hagan (2014)](https://doi.org/10.1088/0266-5611/30/11/114007) is explicit that flat priors on δ collapse the calibration back onto biased θ.
- **KG vs. MES:** MES / PES tend to outperform KG when the decision is continuous global optimization; KG dominates when the decision set is small and discrete ([Frazier–Powell–Dayanik 2008](https://doi.org/10.1137/070693424); [Wang & Jegelka 2017](https://arxiv.org/abs/1703.01968)). `autoengineering`'s "which component to swap" is the latter, so KG is the natural fit.
- **Info-gap** has been criticized in the decision-analysis community — most prominently by [Sniedovich (2008, *Risk Analysis*)](https://doi.org/10.1111/j.1539-6924.2008.01086.x) — for being formally equivalent to a specific worst-case analysis over the nominal-centered uncertainty horizon. Fair criticism when priors are actually available; less so when they aren't — which is the regime we care about.

## Open questions (for the tool)

- Does `autoengineering` want to eventually support **feedback couplings** (MDF-style inner solves) or stay strictly feed-forward?
- Is the target user's downstream decision more naturally an **aspiration threshold** (satisficing) or a **skill maximization** (Pareto/EU)? The choice determines whether `rank_opportunities` should score by ΔP[threshold] or by ΔE[metric].
- Should the tool make **model discrepancy δ** a first-class output of `validate/` alongside pointwise metrics?

## Provenance notes

Research synthesized from four parallel researcher briefs stored in `outputs/.drafts/`:

- `multi-model-system-optimization-research-mdao.md` (T1)
- `multi-model-system-optimization-research-gsa.md` (T2)
- `multi-model-system-optimization-research-voi.md` (T3)
- `multi-model-system-optimization-research-satisficing.md` (T4)

Plus the user-supplied `background_research/deep_research_refs.csv` (53 Consensus-curated BO/multi-objective papers, treated as the pre-existing corpus and not re-scraped).

---

## Sources

All URLs verified reachable (HTML landing pages / abstract pages) via `fetch_content` / `web_search`; per task instructions, PDFs were not fetched. Sources marked with an asterisk are canonical publisher landings that return bot-check pages but resolve.

### MDAO and coupled-simulator BO

- Martins, J. R. R. A. & Lambe, A. B. (2013). "Multidisciplinary Design Optimization: A Survey of Architectures." *AIAA Journal* 51(9). https://doi.org/10.2514/1.J051895
- Martins, J. R. R. A. & Ning, A. (2021). *Engineering Design Optimization*. Cambridge University Press. https://mdobook.github.io/ ; https://doi.org/10.1017/9781108980647
- Tao, S., Van Beek, A., Apley, D. W. & Chen, W. (2021). "Multi-Model Bayesian Optimization for Simulation-Based Design." *J. Mech. Design* 143(11):111701. https://doi.org/10.1115/1.4050738
- Tao, S., Van Beek, A., Apley, D. W. & Chen, W. (2020). IDETC-2020-22651 (conference precursor). https://doi.org/10.1115/DETC2020-22651
- Kyzyurova, K. N., Berger, J. O. & Wolpert, R. L. (2018). "Coupling Computer Models through Linking Their Statistical Emulators." *SIAM/ASA J. UQ* 6(3). https://doi.org/10.1137/17M1157702
- LinkedGASP R package. https://ksenia-kyzyurova.r-universe.dev/LinkedGASP
- Ming, D. & Guillas, S. (2021). "Linked GP Emulation for Systems of Computer Models Using Matérn Kernels and Adaptive Design." *SIAM/ASA J. UQ* 9(4). https://doi.org/10.1137/20M1323771 ; https://arxiv.org/abs/1912.09468
- Ming, D., Williamson, D. & Guillas, S. (2023). "Deep Gaussian Process Emulation using Stochastic Imputation." *Technometrics*. https://doi.org/10.1080/00401706.2022.2124311 ; https://arxiv.org/abs/2107.01590
- Ming, D. & Williamson, D. (2023). "Linked Deep Gaussian Process Emulation for Model Networks." arXiv:2306.01212. https://arxiv.org/abs/2306.01212
- `dgpsi` Python package. https://github.com/mingdeyu/DGP
- Kandasamy, K., Dasarathy, G., Schneider, J. & Póczos, B. (2017). "Multi-fidelity BO with Continuous Approximations." ICML. https://proceedings.mlr.press/v70/kandasamy17a/
- Poloczek, M., Wang, J. & Frazier, P. (2017). "Multi-Information Source Optimization." NeurIPS. https://proceedings.neurips.cc/paper/2017/hash/df1f1d20ee86704251795841e6a9405a-Abstract.html
- Wu, J., Toscano-Palmerin, S., Frazier, P. I. & Wilson, A. G. (2019). "Practical Multi-fidelity BO for Hyperparameter Tuning." UAI. https://proceedings.mlr.press/v115/wu20a.html
- Li, K. et al. (2023). "Multi-fidelity Bayesian Optimization: A Review." arXiv:2311.13050. https://arxiv.org/abs/2311.13050
- Gray, J. S., Hwang, J. T., Martins, J. R. R. A., Moore, K. T. & Naylor, B. A. (2019). "OpenMDAO." *Struct. Multidisc. Optim.* 59. https://doi.org/10.1007/s00158-019-02211-z ; https://openmdao.org/
- Hwang, J. T. & Martins, J. R. R. A. (2018). "A Computational Architecture for Coupling Heterogeneous Numerical Models and Computing Coupled Derivatives." *ACM TOMS*. https://doi.org/10.1145/3182393
- Lukaczyk, T. W. et al. (2015). "SUAVE." AIAA 2015-3087. https://doi.org/10.2514/6.2015-3087 ; https://suave.stanford.edu/
- Dakota, Sandia National Laboratories. https://dakota.sandia.gov/
- Bartoli, N. et al. (2017). SEGOMOE. https://doi.org/10.2514/6.2017-4433 ; https://sbarchopt.readthedocs.io/en/stable/algo/segomoe/
- SMT: Surrogate Modeling Toolbox. https://smt.readthedocs.io/
- Roth, B. & Kroo, I. (2008). "Enhanced Collaborative Optimization." DETC2008-50038. https://doi.org/10.1115/DETC2008-50038

### GSA, Shapley effects, and model discrepancy

- Sobol', I. M. (2001). MATCOM. https://doi.org/10.1016/S0378-4754(00)00270-6
- Saltelli, A. et al. (2010). CPC. https://doi.org/10.1016/j.cpc.2009.09.018
- Owen, A. B. (2014). "Sobol' indices and Shapley value." *SIAM/ASA JUQ*. https://doi.org/10.1137/130936233
- Song, E., Nelson, B. L. & Staum, J. (2016). "Shapley effects for global sensitivity analysis." *SIAM/ASA JUQ*. https://doi.org/10.1137/15M1048070
- Iooss, B. & Prieur, C. (2019). "Shapley effects for sensitivity analysis with correlated inputs." *IJUQ*. https://doi.org/10.1615/Int.J.UncertaintyQuantification.2019028372
- Broto, B., Bachoc, F. & Depecker, M. (2018). arXiv:1801.03300. https://arxiv.org/abs/1801.03300
- Kennedy, M. C. & O'Hagan, A. (2001). "Bayesian calibration of computer models." *JRSS-B*. https://doi.org/10.1111/1467-9868.00294
- Higdon, D., Gattiker, J., Williams, B. & Rightley, M. (2008). *JASA*. https://doi.org/10.1198/016214507000000888
- Higdon, D., Kennedy, M., Cavendish, J. C., Cafeo, J. A. & Ryne, R. D. (2004). *SIAM J. Sci. Comput.* https://doi.org/10.1137/S1064827503426693
- Brynjarsdóttir, J. & O'Hagan, A. (2014). "Learning about physical parameters: the importance of model discrepancy." *Inverse Problems* 30, 114007. https://doi.org/10.1088/0266-5611/30/11/114007
- Herman, J. & Usher, W. (2017). "SALib." *JOSS*. https://doi.org/10.21105/joss.00097 ; https://salib.readthedocs.io/
- Marelli, S. & Sudret, B. UQLab (ETH Zürich). https://www.uqlab.com/
- Friedli, S. et al. (2022). "Network Uncertainty Quantification." *ASME JVVUQ*. https://doi.org/10.1115/1.4055688 ; https://arxiv.org/abs/1908.11476
- Muñoz, D. F., Moftakhari, H. & Moradkhani, H. (2024). "Quantifying cascading uncertainty in compound flood modeling with linked process-based and machine learning models." *HESS* 28:2531. https://doi.org/10.5194/hess-28-2531-2024
- Pianosi, F. et al. (2016). *Environ. Model. Softw.* https://doi.org/10.1016/j.envsoft.2016.02.008
- Wagener, T. & Pianosi, F. (2019). *WIREs Water*. https://doi.org/10.1002/wat2.1569
- Vasudevan, S. & Wozny, G. (1987). *Comp. Chem. Eng.* https://doi.org/10.1016/0098-1354(87)85022-6
- Jaeger, C. C. et al. (2005). *Environmental Modeling & Assessment*. https://doi.org/10.1007/s10666-005-2361-5

### Decision theory and value of information

- Raiffa, H. & Schlaifer, R. (1961). *Applied Statistical Decision Theory*. Wiley. https://www.wiley.com/en-gb/Applied+Statistical+Decision+Theory-p-9780471383499
- Berger, J. O. (1985). *Statistical Decision Theory and Bayesian Analysis*, 2nd ed. Springer. https://link.springer.com/book/10.1007/978-1-4757-4286-2
- Howard, R. A. (1966). "Information Value Theory." *IEEE TSSC* 2(1). https://doi.org/10.1109/TSSC.1966.300074
- Chaloner, K. & Verdinelli, I. (1995). *Statistical Science* 10(3). https://doi.org/10.1214/ss/1177009939
- Ryan, E. G., Drovandi, C. C., McGree, J. M. & Pettitt, A. N. (2016). *Int. Stat. Rev.* 84(1). https://doi.org/10.1111/insr.12107
- Rainforth, T., Foster, A., Ivanova, D. R. & Bickford Smith, F. (2024). *Statistical Science* 39(1). https://doi.org/10.1214/23-STS915
- Foster, A., Ivanova, D. R., Malik, I. & Rainforth, T. (2021). "Deep Adaptive Design." ICML. https://arxiv.org/abs/2103.02438
- Frazier, P. I., Powell, W. B. & Dayanik, S. (2008). "A Knowledge-Gradient Policy for Sequential Information Collection." *SIAM J. Control Optim.* 47(5). https://doi.org/10.1137/070693424
- Hennig, P. & Schuler, C. J. (2012). "Entropy Search." *JMLR* 13. https://www.jmlr.org/papers/v13/hennig12a.html
- Hernández-Lobato, J. M., Hoffman, M. W. & Ghahramani, Z. (2014). "Predictive Entropy Search." NeurIPS. https://arxiv.org/abs/1406.2541
- Wang, Z. & Jegelka, S. (2017). "Max-value Entropy Search." ICML. https://arxiv.org/abs/1703.01968
- Straub, D. (2014). *Structural Safety* 49. https://doi.org/10.1016/j.strusafe.2013.08.006
- Konakli, K., Sudret, B. & Faber, M. H. (2016). *ASCE-ASME J. Risk Uncertainty Eng. Syst. A* 2(3). https://doi.org/10.1061/AJRUA6.0000850
- Andriotis, C. P., Papakonstantinou, K. G. & Chatzi, E. N. (2021). *Structural Safety* 93. https://doi.org/10.1016/j.strusafe.2020.102072
- Ishibashi, H., Karasuyama, M., Takeuchi, I. & Kashima, H. (2023). AISTATS. https://proceedings.mlr.press/v206/ishibashi23a.html
- Xie, Q. et al. (2025). "Cost-aware Stopping for Bayesian Optimization." arXiv:2507.12453 (ICML 2026). https://arxiv.org/abs/2507.12453

### Satisficing, bounded rationality, and info-gap

- Simon, H. A. (1955). "A Behavioral Model of Rational Choice." *QJE* 69(1). https://doi.org/10.2307/1884852
- Simon, H. A. (1956). "Rational Choice and the Structure of the Environment." *Psychological Review* 63(2). https://doi.org/10.1037/h0042769
- Wheeler, G. (2025). "Bounded Rationality." *Stanford Encyclopedia of Philosophy*. https://plato.stanford.edu/archives/win2025/entries/bounded-rationality/
- Byron, M. (1998). "Satisficing and Optimality." *Ethics* 109(1). https://doi.org/10.1086/233874
- Byron, M. (ed., 2004). *Satisficing and Maximizing*. Cambridge UP. https://doi.org/10.1017/CBO9780511617058
- Ben-Haim, Y. (2019). "Info-Gap Decision Theory (IG)" in *Decision Making under Deep Uncertainty*. Springer. https://doi.org/10.1007/978-3-030-05252-2_5
- Ben-Haim, Y. (2008). "Robust-Satisficing in Engineering Design." ASME ESDA2008-59029. https://doi.org/10.1115/esda2008-59029
- Schwartz, B., Ben-Haim, Y. & Dacso, C. (2011). "What Makes a Good Decision? Robust Satisficing as a Normative Standard." *J. Theory Soc. Behav.* 41(2). https://doi.org/10.1111/j.1468-5914.2010.00450.x
- Matrosov, E. S., Padula, S. & Harou, J. J. (2013). *J. Hydrology* 494. https://www.sciencedirect.com/science/article/pii/S0022169413002060
- Hall, J. W. et al. (2012). "Robust Climate Policies Under Uncertainty." *Risk Analysis* 32(10). https://doi.org/10.1111/j.1539-6924.2012.01802.x
- Lempert, R. J. (2019). "Robust Decision Making (RDM)" in *Decision Making under Deep Uncertainty*. Springer. https://doi.org/10.1007/978-3-030-05252-2_2
- Manski, C. F. (2017). "Optimize, satisfice, or choose without deliberation?" *Theory and Decision* 83. https://doi.org/10.1007/s11238-017-9592-1
- Sniedovich, M. (2008). "Wald's Maximin Model: A Treasure in Disguise!" *Risk Analysis* 28(6). https://doi.org/10.1111/j.1539-6924.2008.01086.x

