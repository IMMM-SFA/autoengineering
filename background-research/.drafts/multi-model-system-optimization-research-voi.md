# Decision Theory and Value of Information for Multi-Model System Optimization

**Brief:** T3 — VoI / decision theory / sequential experimental design slice, feeding a synthesis memo for `autoengineering`.
**Scope note:** Bounded to the decision-theoretic backbone; complementary BO / multi-objective coverage lives in other slices.

## Coverage status

- **Directly checked (abstract/landing pages):** Chaloner & Verdinelli 1995; Ryan et al. 2016; Rainforth et al. 2024; Frazier–Powell–Dayanik 2008; Hennig & Schuler 2012; Hernández-Lobato et al. 2014; Wang & Jegelka 2017; Foster et al. 2021 (DAD); Straub 2014; Andriotis–Papakonstantinou–Chatzi 2021; Konakli–Sudret–Faber 2016; Howard 1966 (bibliographic + summary abstract); Raiffa & Schlaifer 1961 (publisher pages); Berger 1985 (Springer page); Ishibashi et al. 2023 (BO stopping); Wilson 2024 "Cost-aware Stopping for BO."
- **Not directly checked (books, no free HTML text):** interior text of Raiffa & Schlaifer, Berger — cited from publisher metadata only.
- **PDFs deliberately skipped** per task guidance.

## Evidence table

| # | Source | URL | Key claim | Type | Confidence |
|---|--------|-----|-----------|------|------------|
| 1 | Raiffa & Schlaifer, *Applied Statistical Decision Theory* (1961; Wiley reissue 2000) | https://www.wiley.com/en-gb/Applied+Statistical+Decision+Theory-p-9780471383499 | Foundational text unifying subjective probability and utility for "typical sampling problems"; introduces preposterior analysis. | primary (book) | high |
| 2 | Berger, *Statistical Decision Theory and Bayesian Analysis*, 2nd ed. (Springer, 1985) | https://link.springer.com/book/10.1007/978-1-4757-4286-2 | Canonical treatment of expected-utility decision rules, admissibility, and Bayesian decision analysis. | primary (book) | high |
| 3 | Howard, "Information Value Theory," IEEE TSSC 2(1), 1966 | https://doi.org/10.1109/TSSC.1966.300074 | Defines the value of clairvoyance / expected value of perfect and sample information by combining probability with the utility of decisions. | primary | high |
| 4 | Chaloner & Verdinelli, "Bayesian Experimental Design: A Review," *Statistical Science* 10(3), 1995 | https://doi.org/10.1214/ss/1177009939 | Unifies Bayesian design under a decision-theoretic utility maximization, subsuming EIG, D-, A-, and utility-based criteria. | primary review | high |
| 5 | Ryan, Drovandi, McGree, Pettitt, "A Review of Modern Computational Algorithms for Bayesian Optimal Design," *Int. Stat. Rev.* 84(1), 2016 | https://doi.org/10.1111/insr.12107 | Reviews simulation-based / nested-MC / ABC methods for computing expected utility when likelihood is intractable. | primary review | high |
| 6 | Rainforth, Foster, Ivanova, Bickford Smith, "Modern Bayesian Experimental Design," *Statistical Science* 39(1), 2024 | https://doi.org/10.1214/23-STS915 | Modern review: variational EIG bounds, gradient-based BOED, amortization; frames experimental design as sequential decision problem. | primary review | high |
| 7 | Foster, Ivanova, Malik, Rainforth, "Deep Adaptive Design (DAD)," ICML 2021 | https://arxiv.org/abs/2103.02438 | Amortizes sequential BOED into a neural design network trained to maximize expected information gain, enabling real-time adaptive experimentation. | primary | high |
| 8 | Frazier, Powell, Dayanik, "A Knowledge-Gradient Policy for Sequential Information Collection," *SIAM J. Control Optim.* 47(5), 2008 | https://doi.org/10.1137/070693424 | KG myopically maximizes the one-step expected increase in the maximum posterior value; optimal at horizon = 1 and asymptotically. | primary | high |
| 9 | Hennig & Schuler, "Entropy Search for Information-Efficient Global Optimization," *JMLR* 13, 2012 | https://www.jmlr.org/papers/v13/hennig12a.html | Recasts BO as reducing entropy of the location of the optimum, not chasing low function values. | primary | high |
| 10 | Hernández-Lobato, Hoffman, Ghahramani, "Predictive Entropy Search (PES)," NeurIPS 2014 | https://arxiv.org/abs/1406.2541 | Selects x* maximizing expected KL between prior and posterior over the argmax, using a tractable predictive reformulation. | primary | high |
| 11 | Wang & Jegelka, "Max-value Entropy Search (MES)," ICML 2017 | https://arxiv.org/abs/1703.01968 | Uses mutual information with the *max value* rather than the argmax; cheaper and has a regret bound. | primary | high |
| 12 | Straub, "Value of information analysis with structural reliability methods," *Structural Safety* 49, 2014 | https://doi.org/10.1016/j.strusafe.2013.08.006 | Operationalizes VoI computation for engineering reliability using FORM/SORM; treats monitoring as a preposterior decision. | primary | high |
| 13 | Konakli, Sudret, Faber, "Numerical Investigations into the Value of Information in Lifecycle Analysis of Structural Systems," *ASCE-ASME J. Risk Uncertainty Eng. Syst. A* 2(3), 2016 | https://doi.org/10.1061/AJRUA6.0000850 | Preposterior VoI in maintenance decisions using surrogate models (PCE) to make expectations tractable. | primary | high |
| 14 | Andriotis, Papakonstantinou, Chatzi, "Value of structural health information in partially observable stochastic environments," *Structural Safety* 93, 2021 | https://doi.org/10.1016/j.strusafe.2020.102072 | Shows POMDPs *inherently* implement VoI: policy value differences quantify VoSHM/VoI; information gains under POMDP policies are non-negative. | primary | high |
| 15 | Ishibashi, Karasuyama, Takeuchi, Kashima, "A Stopping Criterion for BO by the Gap of Expected Minimum Simple Regrets," AISTATS 2023 | https://proceedings.mlr.press/v206/ishibashi23a.html | Provides an optimality-guaranteed stopping rule: stop when expected regret gap falls below a tolerance — a reservation-price analogue. | primary | high |
| 16 | Wilson, "Cost-aware Stopping for Bayesian Optimization," 2024 (arXiv) | https://arxiv.org/abs/2507.12453 | Cost-adjusted simple-regret stopping rule with regret certificates; explicitly frames stopping as a marginal-VoI ≤ marginal-cost condition. | primary | medium |

## Findings (synthesis)

### 1. The Bayesian decision-theoretic frame

The canonical setup (Raiffa & Schlaifer [1]; Berger [2]) is: given a parameter/state θ with prior p(θ), a set of actions A, and a utility u(a, θ), pick a* = argmax_a E_p(θ)[u(a, θ)]. When data d can be observed at cost c, the *preposterior* expected utility is E_d[max_a E_{p(θ|d)}[u(a, θ)]], and the **value of sample information** is that quantity minus max_a E_p(θ)[u(a, θ)], with the value of perfect information as its limit (Howard [3]). This is the exact object the `autoengineering` loop must optimize when deciding which component to invest in improving: each component swap or diagnostic run is a costly "experiment" whose only justification is that its expected posterior improvement of the whole-system objective exceeds its cost.

### 2. Bayesian experimental design as decision theory

Chaloner & Verdinelli [4] argue explicitly that Bayesian experimental design *is* a decision problem, with classical A-, D-, and c-optimality falling out as special utility choices. Ryan et al. [5] catalog the computational machinery (nested MC, ABC, laplace, sequential MC) needed when u is high-dimensional or the likelihood is only accessible through a simulator — the exact regime of coupled compute-model chains. Rainforth et al. [6] update the picture with variational EIG bounds and gradient-based BOED, and Foster et al.'s DAD [7] shows the design policy can be *amortized* into a network so that per-step decisions are cheap even when the underlying expectations are not. For a system-optimization tool this maps to: EIG over a system-level utility (e.g., a validation metric of the terminal component) is the principled acquisition; the question is which component's replacement most reduces posterior uncertainty in that utility.

### 3. Information-theoretic acquisition and knowledge-gradient

Within BO, the modern acquisition-function taxonomy splits neatly along utility choice:

- **Knowledge-gradient (KG)** (Frazier–Powell–Dayanik [8]): utility = the *max of the posterior mean* over the decision space. KG is directly a one-step VoI on the terminal decision — "which measurement most improves the recommendation I would make if forced to stop now?" This is the acquisition function most naturally aligned with "which component should I improve next?" — the decision space is the set of candidate replacement components, the posterior mean is the expected system performance after each hypothetical swap, and KG scores each candidate by the expected posterior improvement.
- **Entropy Search (ES)** (Hennig & Schuler [9]): utility = negative entropy of p(argmax).
- **Predictive Entropy Search (PES)** (Hernández-Lobato et al. [10]) and **Max-value Entropy Search (MES)** (Wang & Jegelka [11]): tractable reformulations, with MES targeting mutual information with the max value.

These are all VoI in Howard's [3] sense with different terminal utilities. KG is the closest fit to `autoengineering`'s workflow, because the decision to be supported is a discrete "swap component X for candidate Y," and KG's terminal-decision framing is native to that setting. MES/PES become attractive when the decision is continuous and one cares about identifying the optimum rather than acting.

### 4. VoI in engineering practice

The structural-reliability community has the most developed applied VoI literature. Straub [12] shows how to compute VoI using FORM/SORM for monitoring-vs-no-monitoring decisions. Konakli, Sudret & Faber [13] use polynomial chaos surrogates to make preposterior expectations tractable in lifecycle maintenance — a directly analogous problem to `autoengineering`'s "should I invest to reduce discrepancy in component X?" Andriotis, Papakonstantinou & Chatzi [14] prove that a POMDP policy inherently realizes a non-negative VoI at every observation step; this generalizes the myopic KG-style analysis to genuinely sequential settings and is the closest published framework for the auto-engineering loop, because a POMDP over "which component is the current bottleneck" with observations = validation metrics and actions = component swaps is a direct formalization of what the tool does.

### 5. Stopping rules

Classical stopping rules in Bayesian decision theory reduce to: *stop when marginal VoI ≤ marginal cost*. Ishibashi et al. [15] operationalize this in BO by monitoring the expected gap between the current recommendation's regret and the optimum's; Wilson [16] extends this with an explicit cost term and provides ε-δ regret certificates. Both are reservation-price stopping rules for the sequential improvement loop and are directly portable to `autoengineering`: after each swap, evaluate whether the expected further improvement across remaining candidate swaps exceeds the fixed engineering cost of proposing and running another swap.

### 6. Connection to `autoengineering` — how would a decision-theoretic loop pick the component to improve?

**The literature does not directly answer this.** The closest match is a POMDP formulation in the Andriotis–Papakonstantinou–Chatzi [14] tradition, where:

- state = latent "true" discrepancy contribution of each component,
- observation = validation metrics (RMSE, NSE, KGE, etc.) of the terminal or intermediate node,
- action = which component to swap (or, "stop"), with a cost,
- reward = negative terminal-node discrepancy − swap cost.

A myopic (one-step) approximation is the knowledge-gradient over the swap set [8]: for each candidate replacement, propagate its expected posterior effect through the DAG to the terminal metric and pick the swap that maximizes expected improvement. If replacement candidates are themselves uncertain (e.g., an unfit sub-model), the acquisition step becomes a nested BOED problem in the Rainforth [6] / Foster [7] mold. Discrepancy attribution then plays the role of *evidence* in Bayes' rule: it shifts the prior over which component's improvement carries the most VoI, but decision theory tells us attribution alone is not the criterion — the criterion is expected marginal improvement of the *system-level* utility per unit cost.

The gap in the literature is that VoI/BOED is almost always about which *experiment/measurement* to run, not which *sub-model to replace*. Framing model-swap as a design decision (utility = ΔNSE, cost = engineering effort) is a natural but under-explored extension, and would be a novel contribution of the `autoengineering` framework.

## Sources

1. Raiffa, H. & Schlaifer, R. (1961). *Applied Statistical Decision Theory.* Wiley. https://www.wiley.com/en-gb/Applied+Statistical+Decision+Theory-p-9780471383499
2. Berger, J. O. (1985). *Statistical Decision Theory and Bayesian Analysis*, 2nd ed. Springer. https://link.springer.com/book/10.1007/978-1-4757-4286-2
3. Howard, R. A. (1966). Information Value Theory. *IEEE Trans. Syst. Sci. Cybern.* 2(1), 22–26. https://doi.org/10.1109/TSSC.1966.300074
4. Chaloner, K. & Verdinelli, I. (1995). Bayesian Experimental Design: A Review. *Statistical Science* 10(3), 273–304. https://doi.org/10.1214/ss/1177009939
5. Ryan, E. G., Drovandi, C. C., McGree, J. M., Pettitt, A. N. (2016). A Review of Modern Computational Algorithms for Bayesian Optimal Design. *Int. Stat. Rev.* 84(1), 128–154. https://doi.org/10.1111/insr.12107
6. Rainforth, T., Foster, A., Ivanova, D. R., Bickford Smith, F. (2024). Modern Bayesian Experimental Design. *Statistical Science* 39(1). https://doi.org/10.1214/23-STS915
7. Foster, A., Ivanova, D. R., Malik, I., Rainforth, T. (2021). Deep Adaptive Design: Amortizing Sequential Bayesian Experimental Design. ICML. https://arxiv.org/abs/2103.02438
8. Frazier, P. I., Powell, W. B., Dayanik, S. (2008). A Knowledge-Gradient Policy for Sequential Information Collection. *SIAM J. Control Optim.* 47(5), 2410–2439. https://doi.org/10.1137/070693424
9. Hennig, P. & Schuler, C. J. (2012). Entropy Search for Information-Efficient Global Optimization. *JMLR* 13, 1809–1837. https://www.jmlr.org/papers/v13/hennig12a.html
10. Hernández-Lobato, J. M., Hoffman, M. W., Ghahramani, Z. (2014). Predictive Entropy Search for Efficient Global Optimization of Black-box Functions. NeurIPS. https://arxiv.org/abs/1406.2541
11. Wang, Z. & Jegelka, S. (2017). Max-value Entropy Search for Efficient Bayesian Optimization. ICML. https://arxiv.org/abs/1703.01968
12. Straub, D. (2014). Value of information analysis with structural reliability methods. *Structural Safety* 49, 75–85. https://doi.org/10.1016/j.strusafe.2013.08.006
13. Konakli, K., Sudret, B., Faber, M. H. (2016). Numerical Investigations into the Value of Information in Lifecycle Analysis of Structural Systems. *ASCE-ASME J. Risk Uncertainty Eng. Syst. A* 2(3). https://doi.org/10.1061/AJRUA6.0000850
14. Andriotis, C. P., Papakonstantinou, K. G., Chatzi, E. N. (2021). Value of structural health information in partially observable stochastic environments. *Structural Safety* 93. https://doi.org/10.1016/j.strusafe.2020.102072
15. Ishibashi, H., Karasuyama, M., Takeuchi, I., Kashima, H. (2023). A Stopping Criterion for Bayesian Optimization by the Gap of Expected Minimum Simple Regrets. AISTATS. https://proceedings.mlr.press/v206/ishibashi23a.html
16. Wilson, J. (2024). Cost-aware Stopping for Bayesian Optimization. arXiv:2507.12453. https://arxiv.org/abs/2507.12453
