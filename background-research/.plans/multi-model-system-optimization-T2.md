# Researcher brief T2 — Global sensitivity, Shapley effects, and model discrepancy

## Context

Feeding into a synthesis memo for `autoengineering`, a Python package that represents a system as a DAG of compute-model components and asks *which component should we improve or swap next?* Existing corpus (`background_research/deep_research_refs.csv`) covers Bayesian and multi-objective optimization but is thin on **attribution** — how do you tell which component in a chain is actually responsible for the discrepancy between simulation and observation?

## Scope

You are **only** responsible for the **attribution** slice: global sensitivity analysis of computer models, Shapley effects, and Bayesian calibration / model-discrepancy frameworks.

## Questions to answer

1. **Global sensitivity analysis (GSA).**
   - Sobol indices (Sobol 1993/2001); variance-based decomposition; total-effect index.
   - Saltelli et al. textbook (*Global Sensitivity Analysis: The Primer*, 2008).
   - When Sobol fails (correlated inputs) → **Shapley effects** (Owen 2014; Song, Nelson, Staum 2016; Iooss & Prieur).
2. **Model discrepancy and Bayesian calibration of computer models.**
   - Kennedy & O'Hagan (2001) "Bayesian calibration of computer models", JRSS-B — the canonical paper. Note the model form:  z(x) = ζ(x) + ε = η(x, θ) + δ(x) + ε, separating calibration bias from *model discrepancy* δ.
   - Higdon et al. (2004, 2008) extensions to functional outputs.
   - Brynjarsdóttir & O'Hagan (2014) "Learning about physical parameters: the importance of model discrepancy".
3. **Component-level attribution in a chain of models.** Search for:
   - "output-input decomposition" / "modular sensitivity analysis" / "network sensitivity analysis"
   - Iooss et al. work on sensitivity in coupled simulators
   - Cascading uncertainty in coupled hydrologic/climate models (Wagener; Clark; Prieur)
4. **Practical software:** SALib (Python), sensitivity R package, UQLab.

## Deliverables

Write `outputs/.drafts/multi-model-system-optimization-research-gsa.md` with:

- ~600–1200 word synthesis
- ~8–15 ranked sources with DOI/URL and one-sentence takeaways
- Clear note where "chain-level attribution" is genuinely underdeveloped in the literature (this is a real research gap and OK to say so)

## Tool guidance

- `web_search` for foundational texts and reviews; `alpha_search` for arXiv preprints and recent method papers.
- Prefer HTML pages; avoid direct PDF fetches. Mark PDF-only sources as PDF-only.
- Kennedy & O'Hagan 2001 is behind a paywall — cite the DOI (10.1111/1467-9868.00294) and the standard URL; do not attempt to parse the PDF.
