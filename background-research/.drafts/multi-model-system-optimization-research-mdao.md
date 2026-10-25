# Multi-Model System Optimization — MDAO & Coupled-Simulator Bayesian Optimization

Slice: Multidisciplinary Design Optimization (MDAO/MDO) and Bayesian optimization over networks of coupled expensive simulators. Feeds into the `autoengineering` synthesis memo.

## Coverage status

- **Checked directly (HTML landing pages / abstracts):** all sources below have DOI / arXiv / official project pages verified via `web_search` result metadata.
- **Full-text extraction blocked (PDF-only or paywall):** Martins & Ning textbook (only PDF drafts + Cambridge landing), Martins & Lambe 2013 (AIAA DOI + author PDF), Kandasamy 2017, Wu 2020, Poloczek 2017 (PMLR/NeurIPS PDF). For these, claims are limited to what appears in search snippets and abstract pages.
- **Not attempted:** direct arXiv `alpha_search` — `web_search` already surfaced canonical arXiv IDs (1912.09468, 2107.01590, 2306.01212, 2311.13050) and per-task guidance said avoid PDFs.

## Evidence table

| # | Source | URL | Key claim | Type | Confidence |
|---|--------|-----|-----------|------|------------|
| 1 | Martins & Ning, *Engineering Design Optimization*, Cambridge Univ. Press, 2021 | https://mdobook.github.io/ ; https://doi.org/10.1017/9781108980647 | Canonical open-access textbook covering MDO architectures (MDF, IDF, CO, BLISS, ATC) and gradient/gradient-free methods | primary (textbook) | high |
| 2 | Martins & Lambe, "MDO: A Survey of Architectures", *AIAA Journal* 51(9), 2013 | https://doi.org/10.2514/1.J051895 | Unified description of all MDO architectures (monolithic MDF/IDF/AAO vs distributed CO/BLISS/ATC/ASO/QSD) with diagrams and XDSM | primary survey | high |
| 3 | Tao, Van Beek, Apley, Chen, "Multi-Model Bayesian Optimization for Simulation-Based Design", *J. Mech. Design* 143(11):111701, 2021 | https://doi.org/10.1115/1.4050738 | Extends BO to systems of *interconnected* expensive simulators; treats each subsystem model separately rather than one monolithic surrogate on system output | primary | high |
| 4 | Tao, Van Beek, Apley, Chen, IDETC 2020 conference precursor | https://doi.org/10.1115/DETC2020-22651 | Earlier conference paper stating the multi-model BO problem and comparing against single-surrogate BO | primary | high |
| 5 | Kyzyurova, Berger, Wolpert, "Coupling Computer Models through Linking Their Statistical Emulators", *SIAM/ASA J. UQ* 6(3), 2018 | https://doi.org/10.1137/17M1157702 | Introduces *linked GP* — closed-form emulator of a composition of independently trained GaSP emulators; predictive mean/variance in closed form | primary | high |
| 6 | LinkedGASP R package (companion to [5]) | https://ksenia-kyzyurova.r-universe.dev/LinkedGASP | Reference implementation of linked GaSP for coupled simulators | code | high |
| 7 | Ming & Guillas, "Linked GP Emulation for Systems of Computer Models Using Matérn Kernels and Adaptive Design", *SIAM/ASA J. UQ* 9(4), 2021 | https://doi.org/10.1137/20M1323771 ; https://arxiv.org/abs/1912.09468 | Generalises linked GP to Matérn kernels + iterative adaptive design for systems of models | primary | high |
| 8 | Ming, Williamson, Guillas, "Deep Gaussian Process Emulation using Stochastic Imputation", *Technometrics*, 2023 | https://doi.org/10.1080/00401706.2022.2124311 ; https://arxiv.org/abs/2107.01590 | Transforms DGP training into linked-GP training via stochastic imputation of latent layers — makes chained emulators tractable | primary | high |
| 9 | Ming & Williamson, "Linked Deep Gaussian Process Emulation for Model Networks", arXiv 2306.01212, 2023 | https://doi.org/10.48550/arxiv.2306.01212 | Explicit deep-GP emulator for networks of computer models spanning disciplines/timescales | primary preprint | medium (arXiv landing only) |
| 10 | dgpsi Python package (Ming) | https://github.com/mingdeyu/DGP | Reference implementation of linked/deep GP emulation via SI | code | high |
| 11 | Kandasamy et al., "Multi-fidelity BO with Continuous Approximations", ICML 2017 | https://proceedings.mlr.press/v70/kandasamy17a/ (PDF) | Continuous-fidelity BO: cheaper low-fidelity queries as proxies for expensive target | primary | medium (PDF-only landing) |
| 12 | Poloczek, Wang, Frazier, "Multi-Information Source Optimization", NeurIPS 2017 | https://proceedings.neurips.cc/paper/2017/hash/df1f1d20ee86704251795841e6a9405a-Abstract.html | MISO with a GP kernel tailored to biased/noisy cheaper information sources | primary | medium |
| 13 | Wu, Toscano-Palmerin, Frazier, Wilson, "Practical Multi-fidelity BO for Hyperparameter Tuning", UAI 2019 | https://proceedings.mlr.press/v115/wu20a.html | Trace-based multi-fidelity BO; used for HPO but generalises to expensive simulators with tunable fidelity | primary | medium |
| 14 | Li, Xu, Kirby et al., "Multi-fidelity Bayesian Optimization: A Review", arXiv 2311.13050, 2023 | https://arxiv.org/abs/2311.13050 | Recent review of GP-based MF surrogates and MF acquisition functions | secondary review | high |
| 15 | Gray, Hwang, Martins, Moore, Naylor, "OpenMDAO: an open-source framework for MDO", *Struct. Multidisc. Optim.* 59, 2019 | https://doi.org/10.1007/s00158-019-02211-z ; https://openmdao.org/ | NASA-originated Python framework; uses MAUD to solve coupled systems + analytic derivatives for gradient-based MDO | primary + official docs | high |
| 16 | Lukaczyk, Wendorff, Colonno, Economon, Alonso et al., "SUAVE: An Open-Source Environment for Multi-Fidelity Conceptual Vehicle Design", AIAA 2015-3087 | https://doi.org/10.2514/6.2015-3087 ; https://suave.stanford.edu/ | Stanford aircraft conceptual design environment mixing low/high-fidelity analyses | primary | high |
| 17 | Dakota (Sandia National Laboratories) | https://dakota.sandia.gov/ ; https://snl-dakota.github.io/ | C++/Python toolkit exposing optimization, UQ, calibration around black-box simulators; supports surrogate-based and multi-fidelity workflows | official docs | high |
| 18 | SEGOMOE (Bartoli, Lefebvre, Bouhlel et al., ONERA/ISAE-SUPAERO) | https://sbarchopt.readthedocs.io/en/stable/algo/segomoe/ ; https://doi.org/10.2514/6.2017-4433 | SuperEGO + Mixture-of-Experts surrogate BO for constrained, multimodal, mixed-variable MDO | primary + docs | high |
| 19 | SMT: Surrogate Modeling Toolbox (Bouhlel, Hwang, Bartoli, Lafage, Morlier, Martins) | https://smt.readthedocs.io/ (referenced via ONERA CSMA 2026 tutorial) | Open-source Python surrogate library (Kriging, KPLS, GEK) that underpins SEGOMOE and OpenMDAO surrogate components | official docs | medium (site referenced, not fetched) |
| 20 | Enhanced Collaborative Optimization (Roth & Kroo, 2008) | https://doi.org/10.1115/DETC2008-50038 | Refinement of Collaborative Optimization (one of the canonical distributed MDO architectures in [2]) | primary | medium |

## Findings

### 1. How MDO formalises a "system of coupled compute models"

The MDO community's canonical formalism is captured in Martins & Lambe's 2013 survey [2] and Martins & Ning's 2021 open-access textbook [1], which reference the same taxonomy:

- **Monolithic architectures**, where a single top-level optimizer sees the whole coupled system:
  - **MDF** (Multidisciplinary Feasible) — a Multidisciplinary Analysis (MDA) resolves inter-discipline coupling at every optimizer iteration; the optimizer sees a converged system.
  - **IDF** (Individual Discipline Feasible) — coupling variables become optimizer-controlled variables plus consistency constraints; disciplines run independently each iteration.
  - **AAO / SAND** — all-at-once / simultaneous analysis-and-design; states, couplings, and design variables are all optimizer variables.
- **Distributed architectures**, where sub-problems own their own local optimizers:
  - **Collaborative Optimization (CO)** — system-level optimizer negotiates target values; subsystems minimise consistency discrepancy [20].
  - **BLISS / BLISS-2000** — bi-level integrated system synthesis, coordinating disciplinary optima through system-level sensitivities.
  - **ATC** (Analytical Target Cascading) — targets propagate top-down through a hierarchy of sub-problems.
  - **ASO, QSD, MDOIS** and others — variants that shift how feasibility and consistency are enforced.

Martins & Lambe give a unified XDSM diagram convention for these architectures and enumerate optimization problem statements plus algorithms [2]. Martins & Ning devote Chapter 13 of the textbook to the same taxonomy and explain how OpenMDAO's MAUD equations generalise MDF/IDF/AAO into a unified residual-based formulation [1, 15]. This taxonomy maps naturally onto `autoengineering`'s DAG-of-components view: `autoengineering` currently assumes a feed-forward chain (implicit MDF with no feedback loops), so the immediate MDO gap is (a) representing feedback couplings and (b) offering non-MDF coordination options.

### 2. Bayesian optimization over networks of coupled expensive simulators

The primary reference for BO on multi-model systems is **Tao, Van Beek, Apley & Chen (2021)** [3], which explicitly critiques treating a coupled system as one black-box for BO and instead builds a *composite* acquisition strategy exploiting the network structure — deciding *which* subsystem model to query rather than only *where* in the global design space. The IDETC 2020 conference version [4] frames the problem and demonstrates that per-model BO can outperform system-level BO when subsystem costs are heterogeneous.

The complementary statistical literature on **linked emulators** provides the surrogate machinery that composite-BO schemes rely on:

- **Kyzyurova, Berger & Wolpert (2018)** derive closed-form linked Gaussian process (GaSP) emulators for the composition `f2(f1(x))` when independent GP emulators of `f1` and `f2` are trained separately [5]; a reference R package is provided [6].
- **Ming & Guillas (2021)** extend this to Matérn kernels — critical for physically motivated smoothness assumptions — and add an adaptive design loop that decides which subsystem to sample next [7].
- **Ming, Williamson & Guillas (2023)** show that a deep GP can be trained as a *stochastically-imputed linked GP*, unifying deep GPs with the systems-of-emulators literature [8]. This is then extended to arbitrary directed networks of models in the "Linked Deep GP Emulation for Model Networks" preprint [9], with a Python implementation in `dgpsi` [10].

**Multi-fidelity BO** — related but distinct — treats a *single* model with a tunable fidelity knob rather than a network. Key references are Kandasamy et al. 2017 (continuous fidelities) [11], Poloczek et al. 2017 (multi-information-source BO with a specialised kernel) [12], and Wu et al. 2019 (trace-observations, e.g. training curves) [13]. Li et al.'s 2023 review [14] catalogues MF-BO methods and their acquisition functions. In `autoengineering` terms, multi-fidelity BO is orthogonal to component-swap decisions: it optimises inside one component, whereas linked-GP/multi-model BO chooses across components.

### 3. Frameworks & toolkits

- **OpenMDAO** (NASA Glenn / U. Michigan) — Python, gradient-based, analytic multidisciplinary derivatives via the MAUD unified residual formulation; supports MDF/IDF/hybrid solvers [15].
- **SUAVE** (Stanford ADL) — Python, multi-fidelity aircraft conceptual design with hooks to CFD/FEM [16].
- **Dakota** (Sandia) — general-purpose C++/Python toolkit for optimization, UQ, calibration, sensitivity, surrogate-based and multi-fidelity iteration around black-box simulators [17].
- **SEGOMOE** (ONERA + ISAE-SUPAERO) — SuperEGO acquisition + Mixture-of-Experts surrogates for constrained, multimodal, mixed-variable BO in MDO problems [18].
- **SMT** (Surrogate Modeling Toolbox) — Python library of Kriging / KPLS / gradient-enhanced Kriging surrogates; used by SEGOMOE and integrable with OpenMDAO [19].

### 4. Feedback couplings and discipline-level surrogates

Two design choices distinguish "multi-model" from "monolithic" BO:

- **Handling feedback couplings.** MDF resolves feedback loops with an inner MDA (fixed-point / Newton) at every outer BO evaluation; IDF and AAO promote the coupling variables to optimizer variables plus equality constraints — this can be done inside a BO by treating coupling residuals as constraints in a constrained-BO acquisition [1, 2]. Linked-GP formulations [5, 7] currently handle *feed-forward* composition analytically; feedback loops require iterating the linked-GP mean-variance fixed point or embedding the loop inside a deep GP [8, 9].
- **Discipline-level surrogates vs monolithic system surrogate.** Tao et al. [3] show that per-model surrogates permit heterogeneous evaluation costs and per-model acquisition. Kyzyurova et al. [5] show that the closed-form linked variance grows with each composition, providing a principled uncertainty budget across the network. This is directly the mechanism `autoengineering` needs to answer "which component to improve next": the linked-GP variance decomposition attributes system-level uncertainty back to individual components — an inference the parent memo can build on.

## Sources

1. Martins & Ning, *Engineering Design Optimization*, Cambridge Univ. Press, 2021 — https://mdobook.github.io/ ; https://doi.org/10.1017/9781108980647
2. Martins & Lambe, "MDO: A Survey of Architectures", AIAA J. 51(9), 2013 — https://doi.org/10.2514/1.J051895
3. Tao, Van Beek, Apley & Chen, "Multi-Model Bayesian Optimization for Simulation-Based Design", J. Mech. Design, 2021 — https://doi.org/10.1115/1.4050738
4. Tao, Van Beek, Apley & Chen, IDETC-2020-22651 — https://doi.org/10.1115/DETC2020-22651
5. Kyzyurova, Berger & Wolpert, "Coupling Computer Models through Linking Their Statistical Emulators", SIAM/ASA J. UQ, 2018 — https://doi.org/10.1137/17M1157702
6. LinkedGASP R package — https://ksenia-kyzyurova.r-universe.dev/LinkedGASP
7. Ming & Guillas, "Linked GP Emulation with Matérn Kernels and Adaptive Design", SIAM/ASA J. UQ, 2021 — https://doi.org/10.1137/20M1323771 ; https://arxiv.org/abs/1912.09468
8. Ming, Williamson & Guillas, "Deep GP Emulation using Stochastic Imputation", Technometrics, 2023 — https://doi.org/10.1080/00401706.2022.2124311 ; https://arxiv.org/abs/2107.01590
9. Ming & Williamson, "Linked Deep GP Emulation for Model Networks", arXiv:2306.01212, 2023 — https://doi.org/10.48550/arxiv.2306.01212
10. dgpsi Python package — https://github.com/mingdeyu/DGP
11. Kandasamy et al., "Multi-fidelity BO with Continuous Approximations", ICML 2017 — https://proceedings.mlr.press/v70/kandasamy17a/
12. Poloczek, Wang & Frazier, "Multi-Information Source Optimization", NeurIPS 2017 — https://proceedings.neurips.cc/paper/2017/hash/df1f1d20ee86704251795841e6a9405a-Abstract.html
13. Wu, Toscano-Palmerin, Frazier & Wilson, "Practical Multi-fidelity BO for Hyperparameter Tuning", UAI 2019 — https://proceedings.mlr.press/v115/wu20a.html
14. Li et al., "Multi-fidelity Bayesian Optimization: A Review", arXiv:2311.13050, 2023 — https://arxiv.org/abs/2311.13050
15. Gray, Hwang, Martins, Moore & Naylor, "OpenMDAO", Struct. Multidisc. Optim. 59, 2019 — https://doi.org/10.1007/s00158-019-02211-z
16. Lukaczyk et al., "SUAVE", AIAA 2015-3087 — https://doi.org/10.2514/6.2015-3087
17. Dakota, Sandia National Laboratories — https://dakota.sandia.gov/
18. SEGOMOE (Bartoli, Lefebvre et al.) — https://sbarchopt.readthedocs.io/en/stable/algo/segomoe/ ; https://doi.org/10.2514/6.2017-4433
19. SMT: Surrogate Modeling Toolbox — https://smt.readthedocs.io/
20. Roth & Kroo, "Enhanced Collaborative Optimization", DETC 2008 — https://doi.org/10.1115/DETC2008-50038

## Notes on gaps / unresolved items

- Full text of the Martins & Ning textbook and Martins & Lambe survey is PDF-only; specific chapter/page references above rely on the mdobook.github.io landing and OpenMDAO's textbook announcement page, plus the author-hosted `mdolab` PDFs, but were not extracted per the "avoid PDF fetch" instruction.
- The Tao et al. 2021 paper's specific acquisition function is inferred from the JMD abstract (`web_search` metadata) — details of how they weight per-model queries would require the paywalled full text.
- Ming & Williamson 2023 (Model Networks) is currently only on arXiv; no journal DOI surfaced.
- SMT toolbox page was cited via the ONERA CSMA-2026 tutorial page rather than a direct fetch of `smt.readthedocs.io`; confidence marked medium.
