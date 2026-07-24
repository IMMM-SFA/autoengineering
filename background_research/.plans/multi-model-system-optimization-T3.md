# Researcher brief T3 — Value of information and decision theory for model improvement

## Context

Feeding into a synthesis memo for `autoengineering`, a Python package that treats systems as DAGs of compute-model components and iteratively decides which component to improve or swap. The user has explicitly flagged **decision theory** as under-covered in the existing corpus (`background_research/deep_research_refs.csv` is dominated by BO/multi-objective papers). Your job is to make the decision-theoretic backbone rigorous.

## Scope

You are **only** responsible for the **decision theory / value-of-information (VoI) / sequential experimental design** slice.

## Questions to answer

1. **Bayesian decision theory basics as applied to engineering design.**
   - Raiffa & Schlaifer (1961), *Applied Statistical Decision Theory*.
   - Berger (1985), *Statistical Decision Theory and Bayesian Analysis*.
   - How is expected utility used to choose among design/model actions?
2. **Value of information (VoI) in engineering and simulation-based design.**
   - Howard (1966) foundational VoI paper.
   - Applications to structural reliability and engineering (Straub; Konakli; Papakonstantinou).
   - VoI in Bayesian networks and model chains.
3. **Sequential experimental design / optimal experimental design.**
   - Chaloner & Verdinelli (1995) "Bayesian Experimental Design: A Review", *Statistical Science*.
   - Ryan et al. (2016) review of Bayesian experimental design.
   - Foster et al. work on gradient-based / amortized OED.
4. **Knowledge-gradient and information-theoretic acquisition functions in BO.**
   - Frazier, Powell, Dayanik (2008) "A knowledge-gradient policy for sequential information collection".
   - Predictive entropy search (Hernández-Lobato et al. 2014).
   - Max-value entropy search (Wang & Jegelka 2017).
   - Connection between KG and "which component to improve next".
5. **Stopping rules and reservation-price style stopping** in Bayesian optimization / sequential decision-making.

## Deliverables

Write `outputs/.drafts/multi-model-system-optimization-research-voi.md` with:

- ~600–1200 word synthesis
- ~8–15 ranked sources with DOI/URL, one-sentence takeaways
- Explicit connection: *how would a decision-theoretic loop pick the component to improve given a discrepancy attribution?* Feel free to say the literature does not directly answer this and cite the closest work.

## Tool guidance

- `web_search` for classical texts (many are books; cite the ISBN/publisher page).
- `alpha_search` for KG, entropy search, and OED papers.
- Avoid PDFs — use HTML abstracts / arXiv landing pages.
