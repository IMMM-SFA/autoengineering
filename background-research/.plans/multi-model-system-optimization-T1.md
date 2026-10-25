# Researcher brief T1 — MDAO and coupled-simulator Bayesian optimization

## Context

Feeding into a synthesis memo for `autoengineering`, a Python package that represents a system as a DAG of compute-model components (each a simplified representation of reality) and asks: *which component should we improve or swap next?*  The user has already gathered ~53 papers on Bayesian and multi-objective optimization via Consensus (see `background_research/deep_research_refs.csv`) and asked us to fill gaps.

## Scope of this task

You are **only** responsible for the **Multidisciplinary Design Optimization (MDAO) and coupled-simulator BO** slice. Do not re-scrape generic BO or evolutionary multi-objective survey papers.

## Questions to answer

1. How does the MDAO / MDO community formalize a "system of coupled compute models"? Name the canonical decompositions (MDF, IDF, collaborative optimization, BLISS, ATC) and the standard reference (Martins & Ning, *Engineering Design Optimization*, Cambridge 2021, open-access online).
2. What is the state of the art for **Bayesian optimization over a network of coupled expensive simulators**, in particular:
   - Tao, Van Beek, Apley, Chen (2021) "Multi-Model Bayesian Optimization for Simulation-Based Design", *J. Mech. Design*, DOI 10.1115/1.4050738 — read the abstract and cite it as the key primary source.
   - Linked emulators / linked Gaussian processes (Kyzyurova, Berger, Wolpert; Ming & Guillas).
   - Deep Gaussian processes for chained simulators (Ming, Williamson, Guillas).
   - Multi-fidelity BO (Kandasamy et al.; Poloczek; Wu; Song & Nott).
3. What frameworks / toolkits implement this in practice? OpenMDAO (NASA), SUAVE, Dakota, SMT / SEGOMOE — one line each.
4. How do these methods handle **feedback couplings** and **discipline-level surrogates** (as opposed to a monolithic surrogate on system output)?

## Deliverables

Write `outputs/.drafts/multi-model-system-optimization-research-mdao.md` with:

- Concise (~600–1200 word) synthesis
- A ranked bibliography of ~8–15 sources with title, authors, year, venue, DOI or URL, and a one-sentence takeaway
- Explicit note if any source was unavailable — do NOT fabricate

## Tool guidance

- Use `web_search` for surveys/textbooks/blogs and `alpha_search` for arXiv papers.
- Prefer HTML abstract pages and paper landing pages; do **not** fetch PDFs (workflow guidance). If only a PDF exists, cite it from search metadata and mark full-text extraction blocked.
- If a search tool returns "not found", record it and move on.
- Cite direct arXiv / DOI / publisher URLs, not aggregator pages when possible.
