# Theoretical Foundations for Optimizing Systems of Compute Models

*A research memo for `autoengineering`, mapping four literatures — MDAO / coupled-simulator BO, global sensitivity and model discrepancy, decision theory and value of information, and satisficing / info-gap — onto the four-step workflow (define → validate → analyze → execute).*

## Executive summary

The `autoengineering` package asks a question that sits at the intersection of four mature but rarely-combined literatures:

> Given a directed graph of coupled compute models (each a simplified representation of reality), and validation data at one or more nodes, **which component should we improve or swap next?**

None of the reviewed fields answer that question directly. But together they supply the theoretical primitives needed to make the workflow defensible. In short:

- **Multidisciplinary Design Optimization (MDAO)** gives the *architectural* language — MDF, IDF, AAO, and distributed patterns (CO, BLISS, ATC) — for coupled compute-model systems, and its recent Bayesian-optimization extensions (Tao et al. 2021 multi-model BO; Kyzyurova/Ming linked and deep-GP emulators) give the *surrogate machinery* for BO over networks of expensive simulators [T1-3, T1-5, T1-7, T1-8].
- **Global sensitivity analysis and model discrepancy** give the *attribution* language: Sobol' and Shapley effects apportion output variance to inputs even under dependence, and Kennedy–O'Hagan Bayesian calibration cleanly separates parameter calibration from *structural* model error δ(x). The literature is thin on **chain-level** discrepancy attribution, which is precisely the gap `autoengineering` sits in [T2-4, T2-5, T2-8, T2-11, T2-14].
- **Decision theory and value of information (VoI)** give the *choice rule*: Howard's VoI framework and its knowledge-gradient / entropy-search descendants convert "which component to improve" into a preposterior expected-utility calculation. The closest formalization to an auto-engineering loop is a POMDP over "which component is the current bottleneck" (Andriotis–Papakonstantinou–Chatzi 2021) [T3-3, T3-8, T3-14].
- **Satisficing and info-gap theory** give the *stopping rule* and an alternative framing: when a downstream threshold ("NSE ≥ 0.5", "flood probability ≤ 1%") is the actual object of interest and probability priors on model error are not credible, robust satisficing dominates expected-utility maximization. This is the frame that most closely matches how engineering standards are written [T4-2, T4-6, T4-8, T4-12].

The rest of this memo (a) surveys each literature in turn, (b) maps its primitives onto `autoengineering`'s four submodules, and (c) flags three genuine research gaps that a follow-on paper could plausibly fill.

---

## 1. MDAO and coupled-simulator Bayesian optimization

**Formalism.** The MDO community's canonical taxonomy of architectures for coupled compute-model systems is due to Martins & Lambe (2013) and codified in Martins & Ning's open-access textbook *Engineering Design Optimization* (Cambridge 2021):

- **Monolithic:** MDF (Multidisciplinary Feasible — inner MDA resolves couplings at each optimizer step), IDF (Individual Discipline Feasible — coupling variables promoted to optimizer variables + consistency constraints), AAO/SAND (states + couplings + design vars all owned by the optimizer).
- **Distributed:** Collaborative Optimization (CO), BLISS/BLISS-2000, Analytical Target Cascading (ATC), plus ASO, QSD, MDOIS variants — each with different feasibility/consistency semantics.

`autoengineering` currently assumes a feed-forward chain (implicit MDF with no feedback loops). This is a real limitation once we consider systems with feedback couplings (e.g., surface-water/groundwater, atmosphere-ocean).

**Surrogate machinery for BO over networks.** Three closely related lines matter here:

- **Multi-model Bayesian optimization** (Tao, Van Beek, Apley & Chen 2021, *J. Mech. Design*): builds a per-subsystem surrogate and lets acquisition decide *which subsystem* to query rather than only where in the global design space. Directly analogous to `autoengineering`'s "which component to swap" question, with heterogeneous evaluation costs treated first-class.
- **Linked Gaussian-process emulators** (Kyzyurova, Berger & Wolpert 2018; Ming & Guillas 2021): closed-form mean and variance for the composition f₂(f₁(x)) when f₁ and f₂ are each emulated independently, generalized to Matérn kernels and adaptive design.
- **Deep-GP / networked-GP emulation** (Ming, Williamson & Guillas 2023; Ming & Williamson 2023 arXiv 2306.01212): turns training a deep GP into training a linked GP via stochastic imputation, and generalizes to arbitrary DAGs of models. Reference implementation: `dgpsi`.

**Multi-fidelity BO** (Kandasamy et al. 2017; Poloczek, Wang & Frazier 2017; Li et al. 2023 review, arXiv 2311.13050) is orthogonal — it optimizes *inside* one component with a tunable fidelity knob, whereas linked-GP / multi-model BO chooses *across* components. Both are relevant to `autoengineering` but answer different sub-questions.

**Ecosystem.** OpenMDAO (NASA/UMich; MAUD residual formulation with analytic derivatives), SUAVE (Stanford, multi-fidelity aircraft design), Dakota (Sandia, general-purpose UQ + optimization), SEGOMOE / SMT (ONERA + ISAE-SUPAERO, mixed-variable BO with Mixture-of-Experts surrogates).

**Mapping to `autoengineering`.** The `System` DAG in `autoengineering.system` is a strict subset of an XDSM diagram (Martins & Lambe convention). Adopting XDSM/MDF/IDF terminology and eventually supporting feedback couplings is the natural next architectural step. The linked-GP variance decomposition is the closest published mechanism for answering "which component contributes most to end-of-chain output uncertainty."

---

## 2. Attribution: global sensitivity, Shapley effects, and model discrepancy

**Sobol'/variance-based decomposition** (Sobol' 2001; Homma & Saltelli 1996; Saltelli et al. 2010) is the workhorse: for scalar output Y = f(X₁,…,X_d) with independent inputs, decompose Var(Y) into first-order and total-effect indices S_i and S_{T_i}. Implemented in SALib (Herman & Usher 2017) and UQLab (Marelli & Sudret). This is what practitioners use when they ask "which input matters most."

**When Sobol' breaks:** under input dependence the decomposition is not unique and Σ S_i ≠ 1. **Shapley effects** (Owen 2014; Song, Nelson & Staum 2016; Iooss & Prieur 2019; Broto, Bachoc & Depecker 2018) apply the cooperative-game-theoretic Shapley value to variance attribution: each input is a "player" and its Shapley effect φ_i is the average marginal contribution to Var(Y) across all orderings. Shapley effects are always non-negative and sum exactly to Var(Y) even under dependence. Under independence, φ_i is sandwiched between S_i and S_{T_i}.

**Model discrepancy** (Kennedy & O'Hagan 2001, *JRSS-B*): the canonical Bayesian framework for computer-model calibration writes

$$z(x) = \eta(x, \theta) + \delta(x) + \varepsilon$$

separating the simulator η (typically emulated by a GP), calibration parameters θ, a **model-discrepancy** function δ (also emulated by a GP), and observation noise ε. Higdon et al. (2004, 2008) extend this to functional / gridded outputs — directly relevant when `autoengineering` components exchange time series (its `timeseries` port type). **Brynjarsdóttir & O'Hagan (2014)** is the cautionary paper: ignoring δ makes θ estimates biased and over-confident, so any workflow that "just fits parameters" without a discrepancy term will mis-attribute structural error to parameter values.

**The chain-attribution gap.** GSA answers "which input matters" and Kennedy–O'Hagan answers "what is model discrepancy for one simulator," but the literature is thin on **which component in a DAG of coupled models is responsible for a system-level sim-obs gap, given that each component's inputs are themselves noisy outputs of upstream components.** Closest existing work:

- **Network / multi-component UQ** (Friedli et al. 2022, ASME JVVUQ; arXiv 1908.11476): forward-propagates per-component UQ through the DAG, without observation-based attribution.
- **Modular sensitivity in flowsheets** (Vasudevan/Wozny 1987; Jaeger et al. 2005 on integrated-assessment coupling): modular sensitivity chains without Sobol'/Shapley language and without closing the loop with observations.
- **Cascading-uncertainty case studies** (Peña et al. 2024, HESS on compound flooding): qualitative rather than a formal per-node decomposition.
- **Explicit "gap attribution" formulations** (Cho, Zhang & Zhou 2025, arXiv 2606.21539): still framing this as an open problem in 2025.

**Practical recipe (inferred, not directly published):** (i) Shapley effects on each component's own parameters using a Kriging surrogate; (ii) fit a Kennedy–O'Hagan δ_c per observable component; (iii) rank components by a composite of Shapley-total contribution to end-of-chain error variance and posterior ‖δ_c‖. This is a plausible synthesis of the two literatures but has not, to my knowledge, been published as a single procedure.

**Mapping to `autoengineering`.** The current `rank_opportunities` in `autoengineering.analyze` uses a heuristic distance-from-threshold score. A defensible replacement would combine Shapley-effect attribution on component parameters with a Kennedy–O'Hagan discrepancy estimate on each observable node — exactly the recipe above.

---

## 3. Decision theory and value of information

**Bayesian decision-theoretic frame.** Raiffa & Schlaifer (1961) and Berger (1985) give the canonical setup: given prior p(θ), action set A, utility u(a, θ), pick a* = argmax_a E[u(a, θ)]. When data d is available at cost c, the **preposterior expected utility** is E_d[max_a E_{p(θ|d)}[u(a, θ)]], and the **value of sample information (VoI)** is this minus max_a E[u(a, θ)]; Howard (1966) formalized this and the notion of value of clairvoyance.

**Bayesian experimental design as decision theory.** Chaloner & Verdinelli (1995, *Statistical Science*) show that A-, D-, c-optimality are all special cases of expected-utility maximization. Ryan et al. (2016) catalog the computational machinery (nested MC, ABC, sequential MC) needed when u is high-dimensional or the likelihood only accessible via a simulator — exactly the regime of coupled compute-model chains. Rainforth et al. (2024, *Statistical Science*) update this with variational EIG bounds and gradient-based BOED; Foster et al. (2021 ICML, Deep Adaptive Design) amortize the design policy into a network for real-time sequential experimentation.

**Information-theoretic acquisition functions.** Within BO, the modern taxonomy splits by utility choice:

- **Knowledge-gradient (KG)** (Frazier, Powell & Dayanik 2008, *SIAM J. Control Optim.*): utility = max of the posterior mean over the *decision* space. KG is directly a one-step VoI on the terminal decision. This is the acquisition most naturally aligned with "which component should I improve next?" — decision space = candidate replacement components; posterior mean = expected system performance after each hypothetical swap.
- **Entropy Search** (Hennig & Schuler 2012) / **Predictive ES** (Hernández-Lobato et al. 2014) / **Max-value ES** (Wang & Jegelka 2017): utility framed as entropy reduction over argmax or max-value.

For `autoengineering`, KG is the closest fit because the decision is a discrete "swap component X for candidate Y." MES/PES become attractive when the decision is continuous.

**VoI in engineering practice.** The structural-reliability community has the most developed applied VoI literature: Straub (2014, *Structural Safety*) uses FORM/SORM to compute monitoring-vs-no-monitoring VoI; Konakli, Sudret & Faber (2016) use polynomial chaos surrogates to make preposterior expectations tractable in lifecycle maintenance; **Andriotis, Papakonstantinou & Chatzi (2021, *Structural Safety*)** prove that a POMDP policy inherently realizes non-negative VoI at every observation step. Their POMDP formulation is the closest published framework for an auto-engineering loop:

- state = latent discrepancy contribution of each component,
- observation = validation metrics on terminal / intermediate nodes,
- action = which component to swap (or "stop"), with cost,
- reward = negative terminal-node discrepancy − swap cost.

A myopic (one-step) approximation is KG over the swap set. If replacement candidates are themselves uncertain (e.g., an unfit sub-model), the acquisition becomes a nested BOED problem à la Rainforth / Foster.

**Stopping rules.** Ishibashi et al. (2023 AISTATS) provide an optimality-guaranteed BO stopping rule based on the expected simple-regret gap; Wilson (2024, arXiv 2507.12453) adds an explicit cost term and regret certificates. Both are reservation-price stopping rules directly portable to `autoengineering`.

**Mapping to `autoengineering`.** `autoengineering.execute.swap_component` currently returns a new `System` with one component replaced; a defensible auto-engineering loop wraps this in a KG-over-swap-set acquisition, evaluates each candidate swap via propagated posterior expectation on the terminal metric, and terminates via a marginal-VoI ≤ marginal-cost stopping rule.

---

## 4. Satisficing, bounded rationality, and info-gap

**Simon's satisficing** (Simon 1955 *QJE*; 1956 *Psych. Review*): real decision-makers have bounded information and compute; the rational strategy is to search until an aspiration-level threshold is reached and stop. "Organisms adapt well enough to 'satisfice'; they do not, in general, 'optimize'" [Simon 1956]. Manski (2017, *Theory and Decision*) gives a minimax-regret formalization showing that under bounded deliberation cost, satisficing is normatively defensible, not just a heuristic.

**Byron** (1998 *Ethics*; ed. 2004 Cambridge volume) argues that satisficing is a distinct normative account of practical reason, not merely an approximation to maximizing.

**Info-gap decision theory (IGDT)** (Ben-Haim 2006/2010; Springer chapter 2019) addresses *severe* uncertainty: a nominal model exists but its error bounds and probability structure are unknown. Two dual immunity functions are defined against a nested family of uncertainty sets around the nominal model:

- **Robustness** α̂(q, r_c): the largest horizon of uncertainty at which decision q still guarantees a minimum acceptable reward r_c.
- **Opportuneness** β̂(q, r_w): the smallest horizon at which windfall reward r_w becomes possible.

Ben-Haim's central engineering claim (2008 ASME ESDA; 2010): a design that optimizes performance under the nominal model has **zero immunity** to any deviation of reality from that model. Robustness is *bought* by relaxing aspiration. This is why engineering codes specify inequality constraints ("survive the 100-yr event", "carry load ≥ 1.5×") rather than constrained-optimal designs.

**Robust satisficing** (Schwartz, Ben-Haim & Dacso 2011, *J. Theory Soc. Behav.*): choose the alternative that maximizes robustness (in the info-gap sense) subject to meeting a critical aspiration. This is the appropriate normative standard when the probability model itself is ambiguous — the Knightian setting where expected-utility maximization requires priors the decision-maker doesn't actually have.

**Applications converging on satisficing.** Matrosov, Padula & Harou (2013, *J. Hydrology*) apply both IGDT and Robust Decision Making (Lempert 2019, Springer chapter) to London water supply; Hall et al. (2012, *Risk Analysis*) compare RDM and IGDT on climate mitigation. Both surface the same "meet threshold across the widest swath of futures" strategies as robust — not the same ones as expected-NPV-maximization.

**When satisficing is the right frame** (rather than Pareto or expected utility):

- The probability model over model-error / forcings / parameters is not credible.
- A natural externally-imposed threshold ("NSE ≥ 0.5", "peak error ≤ X mm/day") is the actual object of interest to a downstream decision-maker.
- Deliberation cost is high and marginal skill improvement past the threshold has diminishing operational value.
- The chain is applied across many sites/scenarios and the decision-maker cares about worst-case or reliability, not ensemble mean.

**Mapping to `autoengineering`.** `validate_arrays` already returns pass/warn/fail against a threshold — this is a satisficing-native primitive. Concrete implications if the framing shifts from "maximize skill" to "meet threshold":

1. `rank_opportunities` should score components by *change in threshold-satisfaction probability across an uncertainty ensemble*, not distance from a nominal target.
2. Stop rule: halt as soon as all component thresholds pass and end-to-end skill exceeds aspiration; additional swaps only justified if they buy robustness α̂, not additional nominal skill.
3. Add info-gap robustness α̂ as a first-class metric alongside RMSE/NSE/KGE.
4. Validate each component on an *uncertainty ensemble* (bootstrap of forcings, alternative parameterizations), not a single observed record — the RDM stress-test pattern.
5. Elicit aspiration thresholds explicitly at the start of the workflow; the YAML `system.yaml` is the natural place for per-metric aspirations.
6. Cost-aware search: per-component "cost of swap" (runtime, effort, license) becomes first-class input to ranking so the loop prefers cheap threshold-crossing swaps over expensive skill-squeezing swaps.

---

## 5. Consolidated mapping onto the four `autoengineering` submodules

| Submodule                | Current primitive                          | Theoretical primitive imported                                                                                                     | Key sources                                                                             |
|--------------------------|--------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------|
| `system/` (define)      | DAG of components with typed ports        | XDSM diagram / MDF, IDF, AAO taxonomy; eventual feedback-coupling semantics                                                       | Martins & Lambe 2013; Martins & Ning 2021; Gray et al. OpenMDAO 2019                    |
| `validate/` (validate)  | scalar metrics vs. thresholds             | Kennedy–O'Hagan discrepancy δ(x) as first-class output; ensemble validation vs. single record                                     | Kennedy & O'Hagan 2001; Higdon 2004/2008; Brynjarsdóttir & O'Hagan 2014                 |
| `analyze/` (rank)       | heuristic improvement-potential score     | Shapley effects on component parameters + posterior ‖δ_c‖; KG over candidate swaps; robust-satisficing threshold-probability score | Owen 2014; Song–Nelson–Staum 2016; Frazier–Powell–Dayanik 2008; Schwartz–Ben-Haim–Dacso 2011 |
| `execute/` (swap)       | pure `swap_component` returning new System | Sequential decision loop with KG or POMDP-style policy; marginal-VoI ≤ marginal-cost stopping                                     | Andriotis–Papakonstantinou–Chatzi 2021; Ishibashi et al. 2023; Wilson 2024               |

---

## 6. Open questions and research gaps

1. **Chain-level discrepancy attribution.** No published procedure combines Shapley effects with Kennedy–O'Hagan discrepancy on a DAG of models to rank components by their contribution to observed end-of-chain error. Friedli et al. (2022) does forward propagation without attribution; Cho et al. (2025) still frames the gap as open.
2. **Model-swap as experimental-design action.** BOED / VoI literature almost always treats "which measurement to run" as the design decision. Framing "which sub-model to replace" as a design decision (utility = ΔNSE or ΔP[threshold-met], cost = engineering effort) is a natural extension of Andriotis et al. 2021's POMDP formulation but has not been published as such.
3. **Coupled satisficing + BO.** Cost-aware BO stopping rules (Wilson 2024, Ishibashi et al. 2023) and robust satisficing (Ben-Haim, Schwartz et al. 2011) have not been combined into a single acquisition-plus-stopping policy for engineering model chains.

---

## Caveats and disagreements

- The **Tao et al. 2021** paper's specific per-model acquisition function is inferred from the JMD abstract; the exact weighting scheme requires the paywalled full text (research brief T1 marks this).
- Under **input dependence**, Sobol' first-order and total-effect indices lose their tidy interpretation; Shapley effects are the current best answer but come with permutation-estimator cost that scales poorly in dimension (T2, sources 4–7).
- **Kennedy–O'Hagan** with a δ term is *identifiable* only under informative priors — Brynjarsdóttir & O'Hagan (2014) is explicit that flat priors on δ collapse the calibration back onto biased θ.
- **KG vs. MES:** MES / PES tend to outperform KG when the decision is continuous global optimization; KG dominates when the decision set is small and discrete. `autoengineering`'s "which component to swap" is the latter, so KG is the natural fit.
- **Info-gap** has been criticized in the decision-analysis community (Sniedovich) for being formally equivalent to a specific worst-case analysis. Fair criticism when priors are actually available; less so when they aren't — which is the regime we care about.

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
