# Model search results

Open [the standalone figure report](report.html). It uses seven interactive figures rather than data tables, with 20 selectable views, embedded dependencies, light/dark themes and SVG print fallbacks. The report covers the audited fixed and 2,000-call target studies and the three open model chains.

[Quarto source](report.qmd), [figure data and specifications](figures/), [input and output hashes](provenance.json), [BibTeX](references.bib), and [annotated references](../../background_research/pilot-based-selection.md) accompany the HTML. The adopted heuristic and research TODO are in [optimization guidance](../../docs/optimization.md#choosing-a-search-method).

## Reproduce

From the repository root:

```sh
pixi run -e examples python -m scripts.summarize_complex_models --target-directory target-2000
pixi run --manifest-path reports/model-search-results/pixi.toml render
pixi run --manifest-path reports/model-search-results/pixi.toml check
```

To refresh the HTML verification record, from this directory:

```sh
pixi run python scripts/verify_report.py
```

The report has its own locked Pixi environment. Rendering verifies the source aggregates and produces the figures. It does not rerun optimizers or model experiments.

## Verification, 2026-09-05

- Canonical evidence regeneration verified 120 studies. Every report input hash still matched afterward.
- The figure build cross-checked 88 Markdown rows against audited records.
- Six report tests passed, including rejection of changed RMSE, false target attainment, and relabeled infeasibility.
- [HTML checks](html-check.json) verified seven figures, 20 embedded specifications matching saved JSON, resource embedding, internal links, source/output hashes, and zero data tables.
- [Layout checks](layout-check.json) found no issues across 20 specifications. The layout checker cannot extract this report's custom multi-view wrapper directly from HTML, so the checked JSON is connected to the rendered HTML by exact specification comparisons.
- [Project constraint checks](constraints-check.txt) passed. Bibliography structure and citation keys passed validation. Frazier's DOI metadata matched. JMLR publisher metadata verified the Bergstra/Bengio reference. Automatic Crossref searching for that DOI-less reference returned an unrelated candidate, which was rejected.
- Browser inspection covered light/dark themes at 1190 and 768 pixel widths, chart labels, model/runtime selectors, and navigation. No browser warning/error logs were observed. Exactly one SVG fallback was selected for each figure. Physical printing and PDF pagination were not tested.
- [Independent scientific review](../../docs/model-search-results-review.md) found no critical or major issues. Its caption and color wording suggestions were resolved. Its optional future extension to reject other termination reasons remains a future hardening suggestion; every current non-hit has the evaluation-cap stop reason.

The report preserves the benchmark's limits: five example models do not validate a universal selection rule, validation target hits do not establish test superiority, and the separate chain comparisons retain their sensor, feasibility, convergence and foresight qualifications.
