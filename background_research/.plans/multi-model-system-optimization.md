# Plan: Optimization of Complex Systems Composed of Multiple Compute Models

**Slug:** `multi-model-system-optimization`
**Date:** 2026-07-07
**Requestor context:** The user maintains the `autoengineering` package (this repo). Its four-step workflow — define system as a graph of components → validate arrays → rank improvement opportunities → swap a component → re-validate — needs to stand on a defensible theoretical foundation. The user has already done a Consensus search and collected ~50 references under `background_research/`, plus notes on systems-engineering standards (SysML v2, BMI, MBSE) and workflow tools.

## Research objective

Find **theoretically sound** approaches from systems engineering, operations research, uncertainty quantification, and decision theory for **optimizing multi-model systems** — where "optimize" here specifically means *identifying which component sub-model to improve or replace* rather than tuning a scalar design vector. Map those approaches to the `autoengineering` workflow so we can (a) justify design choices, (b) find gaps in what we do, and (c) point at concrete methods to adopt.

## Key questions

1. **Framing.** How does the literature formalize "a system of coupled compute models" (multidisciplinary analysis, network-of-models, coupled simulators, model chains)? What is the standard vocabulary — MDAO, MDO, linked/networked emulators, BMI-style coupling, digital twin, model-based systems engineering?
2. **Component-level improvement.** Given a fixed system topology, what principled methods exist to (a) *localize* which component contributes most to output error / cost / risk, and (b) *quantify* the value of improving one component vs. another? Candidates: global sensitivity analysis (Sobol, Shapley), value-of-information (VoI), knowledge gradient, contribution analysis, model discrepancy (Kennedy–O'Hagan), causal Bayesian optimization.
3. **Optimization under expensive coupled simulators.** What is the state of the art for BO / surrogate-assisted optimization when the black box is itself a *chain* of expensive models? Key entries: multi-model / linked-emulator BO (Tao et al. 2021), multi-fidelity BO, MDAO surrogate methods.
4. **Multi-objective and Pareto framing.** When "improve the system" involves trading skill vs. runtime vs. simplicity vs. data needs, which multi-objective decision frameworks apply? What role does the Pareto front play vs. scalarization vs. lexicographic ordering?
5. **Satisficing and bounded rationality.** Where does satisficing (Simon; Byron; Ben-Haim's info-gap; robust satisficing) fit in engineering-design optimization? Is there a formal case for "stop improving when the component meets threshold X" rather than pushing to Pareto-optimality?
6. **Decision theory.** Which decision-theoretic foundations (expected utility, VoI, sequential decision theory, robust/minimax, info-gap, Bayesian decision theory) are used to *choose which experiment / model swap to try next*? This is the theoretical core of an "auto-engineer" loop.
7. **Reproducibility and reporting.** What standards/frameworks (MBSE, SysML v2, BMI, CSDMS) address the reporting and reproducibility side of multi-model system improvement, and how should results feed back into system design?

## Evidence needed

- Foundational textbooks / review papers on: multi-objective optimization; Bayesian optimization; multidisciplinary design optimization (MDAO); global sensitivity analysis; Kennedy–O'Hagan model discrepancy; value-of-information in engineering; satisficing / info-gap; decision theory in engineering design.
- Recent (≥ 2019) survey or method papers on Bayesian optimization for **coupled / multi-model / networked** systems, multi-fidelity BO, causal BO.
- At least one primary source on each of: **satisficing / robust satisficing** (Simon 1956; Ben-Haim info-gap); **value of information** in model-based design; **Kennedy–O'Hagan** model discrepancy / Bayesian calibration of computer models.
- The existing `background_research/deep_research_refs.csv` (53 papers) as the starting corpus.

## Scale decision

**Broad survey, multi-faceted.** The topic legitimately spans BO, MO, sensitivity analysis, decision theory, MDAO, and satisficing/info-gap — five subfields with distinct literatures. The Consensus results are heavily weighted toward BO and multi-objective evolutionary methods; the user has explicitly called out satisficing and decision theory as underrepresented, and MDAO / Kennedy–O'Hagan / VoI / sensitivity analysis are not visible in the CSV at all. Simple direct search would miss those gaps.

**Decision: use 4 `researcher` subagents in parallel**, each targeting one gap area, plus lead-owned synthesis and (after user approval of the plan) the standard verifier + reviewer passes. The existing CSV covers BO/MO reasonably well, so no researcher is assigned to re-scrape that ground; the lead will pull from the CSV directly.

## Task ledger

| ID  | Owner              | Task                                                                                                                                                                                                                    | Output                                                          | Status  |
| --- | ------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------- | ------- |
| T0  | lead               | Read `background_research/deep_research_refs.csv` + notes; extract themes and pre-cited papers.                                                                                                                         | notes in draft                                                  | done    |
| T1  | researcher (async) | **Multidisciplinary Design Optimization (MDAO) & coupled-simulator BO.** Survey MDAO frameworks (Martins & Ning textbook, OpenMDAO), linked-emulator BO (Tao et al. 2021), multi-fidelity BO, network-of-models methods. | `outputs/.drafts/multi-model-system-optimization-research-mdao.md` | pending |
| T2  | researcher (async) | **Global sensitivity analysis, Shapley effects, model discrepancy.** Sobol/Shapley for computer models; Kennedy–O'Hagan Bayesian calibration; how to attribute output error to individual components in a chain.        | `outputs/.drafts/multi-model-system-optimization-research-gsa.md`  | pending |
| T3  | researcher (async) | **Value of information & decision theory for model improvement.** VoI in engineering design; Bayesian decision theory; sequential experimental design; knowledge-gradient acquisition; when-to-stop rules.              | `outputs/.drafts/multi-model-system-optimization-research-voi.md`  | pending |
| T4  | researcher (async) | **Satisficing, bounded rationality, info-gap, robust optimization.** Simon's satisficing; Ben-Haim info-gap decision theory; robust satisficing vs. optimizing; connections to engineering design.                      | `outputs/.drafts/multi-model-system-optimization-research-satisficing.md` | pending |
| T5  | lead               | Synthesize into draft with sections mapped to `autoengineering` workflow. Include a table mapping each theoretical primitive to a package concern (System, validate, analyze/rank, execute/swap).                       | `outputs/.drafts/multi-model-system-optimization-draft.md`         | pending |
| T6  | verifier           | Add inline citations, verify URLs, produce cited draft.                                                                                                                                                                 | `outputs/.drafts/multi-model-system-optimization-cited.md`         | pending |
| T7  | reviewer           | Flag unsupported claims, single-source critical claims, overstated confidence.                                                                                                                                          | `outputs/.drafts/multi-model-system-optimization-verification.md`  | pending |
| T8  | lead               | Apply reviewer fixes; deliver final artifact + provenance.                                                                                                                                                              | `outputs/multi-model-system-optimization.md` + `.provenance.md`    | pending |

Decision to spawn subagents was made **after** the scale decision (broad, multi-domain, 4 gap areas).

## Verification log

*(populated during execution)*

- [ ] Every quantitative or attribution claim traces to a URL or a source in `background_research/deep_research_refs.csv`.
- [ ] Each of the four theoretical pillars (BO/surrogate, sensitivity/attribution, decision theory/VoI, satisficing/robust) has ≥ 2 independent primary sources.
- [ ] Final artifact exists at `outputs/multi-model-system-optimization.md`.
- [ ] Provenance sidecar exists at `outputs/multi-model-system-optimization.provenance.md`.
- [ ] Reviewer FATAL findings resolved.

## Decision log

- **2026-07-07** — Chose broad-survey scale with 4 researcher subagents targeting **only the gaps** (MDAO, GSA/model discrepancy, VoI/decision theory, satisficing). Rationale: user's Consensus corpus already covers BO and multi-objective methods densely; spawning researchers on those would duplicate effort.
- **2026-07-07** — Avoiding PDF parsing per workflow guidance; researchers will work from abstracts, HTML pages, and metadata.
- **2026-07-07** — Final artifact type: `outputs/*.md` (annotated reading list + framework mapping), not a paper-style draft. This is an internal research memo, not a publication.
