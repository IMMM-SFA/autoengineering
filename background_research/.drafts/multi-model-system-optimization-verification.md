# Verification pass — `multi-model-system-optimization-cited.md`

Task: verify citations and claims in the cited memo. This is a verification pass, not a peer review. Focus: (1) DOI/URL plausibility and attribution, (2) faithfulness of the four literatures, (3) research-gap defensibility, (4) author/year/venue accuracy. PDFs were not fetched; verification is based on landing-page metadata via web search.

Labels: **FATAL** (citation is wrong in a way that will not survive any review), **MAJOR** (wrong or misleading enough to change a reader's takeaway), **MINOR** (polish / hedging / small error).

---

## Summary of findings

Three citations are demonstrably wrong on author, year, or identifier. One "still open in 2025" gap claim rests on a fabricated arXiv ID and should be treated as unsupported. Two more citations have year/author drift. The rest of the reference list is plausible and, where spot-checked, correctly attributed.

The four literatures are represented reasonably, but the memo's most load-bearing rhetorical claim — that chain-level discrepancy attribution is an *open* gap "still framed as open in 2025" — is currently propped up by the fabricated arXiv reference and needs to be either (a) removed, (b) reframed as the authors' own assessment, or (c) supported by a real citation.

---

## FATAL findings

### F1 — Peña et al. 2024 HESS: wrong authors
> "Cascading-uncertainty case studies ([Peña et al. 2024, HESS](https://hess.copernicus.org/articles/28/2531/2024/) on compound flooding)"
> Also in Sources: "Peña, F. et al. (2024). 'Cascading uncertainty in compound flood modeling.' *HESS*."

The URL `hess.copernicus.org/articles/28/2531/2024/` resolves to a real paper, but the authors are **Muñoz, D. F.; Moftakhari, H.; Moradkhani, H.** (title: "Quantifying cascading uncertainty in compound flood modeling with linked process-based and machine learning models"; DOI `10.5194/hess-28-2531-2024`). There is no "Peña" on the byline. Fix: replace with `Muñoz, Moftakhari & Moradkhani (2024)` in both the body and the Sources list.

### F2 — Cho, Zhang & Zhou 2025, arXiv:2606.21539: fabricated / impossible identifier
> "Explicit 'gap attribution' formulations ([Cho, Zhang & Zhou 2025, arXiv:2606.21539](https://arxiv.org/abs/2606.21539)): still framing this as an open problem in 2025."
> Also: "[Cho et al. (2025)](https://arxiv.org/abs/2606.21539) still frames the gap as open."

The arXiv identifier `2606.21539` implies submission in June **2026** (arXiv IDs are YYMM.NNNNN), which is inconsistent with the "2025" year. Searches for this ID return no such paper; the June-2026 arXiv corpus does not contain a Cho/Zhang/Zhou "gap attribution" paper matching this description. Two independent problems: the year is inconsistent with the ID, and no evidence the paper exists at all. This citation is load-bearing — it is the *only* source cited to establish that chain-level discrepancy attribution is "still open in 2025." Fix: remove the citation, and either drop the "still open in 2025" claim or attribute it as the memo authors' own assessment based on absence of prior work, not to Cho et al.

### F3 — "Wilson 2024, arXiv:2507.12453": wrong year and wrong author
> "[Wilson (2024, arXiv:2507.12453)](https://arxiv.org/abs/2507.12453) adds an explicit cost term and regret certificates."
> Sources: "Wilson, J. (2024). 'Cost-aware Stopping for Bayesian Optimization.' arXiv:2507.12453."

The arXiv ID `2507.12453` resolves to the real paper "Cost-aware Stopping for Bayesian Optimization", submitted **July 2025**, not 2024. The first author on the corresponding code repo and paper record is **Qian ("Jane") Xie** (github.com/QianJaneXie/CostAwareStoppingBayesOpt), not "Wilson." The paper is cited twice in the body plus once in Sources; all three copies are wrong. Fix: correct year to 2025 and author to Xie et al. (verify exact byline against the arXiv record).

---

## MAJOR findings

### M1 — Overstated novelty of the "chain-level discrepancy attribution" gap
> "The literature is thin on **chain-level** discrepancy attribution, which is precisely the gap `autoengineering` sits in ([Friedli et al. 2022]; [Cho, Zhang & Zhou 2025])."
> "**Explicit 'gap attribution' formulations** ... still framing this as an open problem in 2025."
> "No published procedure combines Shapley effects with Kennedy–O'Hagan discrepancy on a DAG of models..."

With F2 removed, the gap claim rests solely on Friedli et al. 2022 (which the memo itself describes as "forward propagates per-component UQ ... without observation-based attribution"), i.e. on the *absence* of a citation rather than on any positive evidence. That may be defensible, but the memo currently states the gap with more confidence than the evidence supports. Fix: hedge to "we are not aware of a published procedure that ..." and drop the appearance of citation-backed novelty.

### M2 — "Manski (2017) gives a minimax-regret formalization"
> "[Manski (2017, *Theory and Decision*)](https://doi.org/10.1007/s11238-017-9592-1) gives a minimax-regret formalization showing that under bounded deliberation cost, satisficing is normatively defensible..."

The Manski 2017 *Theory and Decision* paper is titled "Optimize, satisfice, or choose without deliberation? A simple minimax-regret assessment." That title supports the citation, but the memo's claim goes further than a brief assessment: "*shows that* ... satisficing is normatively defensible." A "simple minimax-regret assessment" that compares three rules is not the same as a proof of normative defensibility. Fix: soften ("argues via a minimax-regret comparison that satisficing can dominate optimization under deliberation cost").

### M3 — LinkedGASP attribution / claim scope
> "**Linked Gaussian-process emulators** ([Kyzyurova, Berger & Wolpert 2018]; [Ming & Guillas 2021], [arXiv:1912.09468]): closed-form mean and variance for the composition f₂(f₁(x)) when f₁ and f₂ are each emulated independently, generalized to Matérn kernels and adaptive design."

The "generalized to Matérn kernels and adaptive design" phrase collapses two different papers into one claim (Kyzyurova et al. give closed-form only for a restricted covariance/link class; the Matérn/adaptive generalization is the Ming & Guillas contribution). This is not wrong, but as written a skeptical reader will read the closed-form claim as applying to both papers. Fix: split the two contributions in one clause each.

### M4 — Higdon 2004 / 2008 scope
> "[Higdon et al. (2004, 2008)] extend this to functional / gridded outputs — directly relevant when `autoengineering` components exchange time series (its `timeseries` port type)."

Higdon 2008 (JASA) is the canonical high-dimensional/functional-output KOH extension; Higdon 2004 (SISC) is the earlier basis / calibration paper and does not itself introduce the same functional-output machinery as strongly as the phrasing implies. Not a fatal misattribution, but "extend this to functional / gridded outputs" is more accurately attached to the 2008 paper alone. Fix: keep 2008; move 2004 to a supporting cite.

---

## MINOR findings

### m1 — "Song, Nelson & Staum 2016" journal
> "*SIAM/ASA JUQ*" — the paper appeared in *SIAM Journal on Uncertainty Quantification* (SIAM/ASA JUQ). Correct as written; flagging only because the memo uses the same abbreviation for Owen 2014 without expansion at first use. Cosmetic.

### m2 — Wu et al. year vs. PMLR path
> "[Wu et al. 2019](https://proceedings.mlr.press/v115/wu20a.html)"

Body says 2019 (UAI 2019, correct); PMLR path is `wu20a` because PMLR v115 was published in 2020. Not an error, but a skeptical reader may flag the year/path mismatch. Consider adding an "UAI 2019 (PMLR v115, 2020)" note or citing the arXiv preprint (`arXiv:1903.04703`).

### m3 — Sniedovich criticism paraphrase
> "**Info-gap** has been criticized ... (Sniedovich) for being formally equivalent to a specific worst-case analysis."

Sniedovich's critique is bibliographically real and widely known, but the memo names him without a citation — the only unsourced named critique in the document. Add a specific reference (e.g., Sniedovich 2008 in *Risk Analysis* or the 2012 note in *OMEGA*) or drop the name.

### m4 — "Byron (ed., 2004) Cambridge volume" DOI
> "Byron, M. (ed., 2004). *Satisficing and Maximizing*. Cambridge UP. https://doi.org/10.1017/CBO9780511617058"

Plausible DOI (Cambridge Companions numbering), but was not directly verified in this pass; low risk.

### m5 — "MAUD residual formulation with analytic derivatives"
> "([OpenMDAO] ... MAUD residual formulation with analytic derivatives; [Gray et al. 2019])"

MAUD (Modular Analysis and Unified Derivatives) is Hwang & Martins, not the 2019 OpenMDAO overview paper; correct citation for MAUD is Hwang & Martins 2018 (*ACM TOMS*). The Gray et al. 2019 cite covers the framework overview but is often paired with the MAUD paper when the residual/derivative machinery is invoked. Fix: add Hwang & Martins 2018 as the MAUD source; keep Gray et al. 2019 for OpenMDAO itself.

### m6 — "Foster et al. (2021 ICML, Deep Adaptive Design)"
> "[Foster et al. (2021 ICML, Deep Adaptive Design)](https://arxiv.org/abs/2103.02438)"

Author list in the Sources block is "Foster, A., Ivanova, D. R., Malik, I. & Rainforth, T." The paper's actual byline order (Foster, Ivanova, Malik, Kleinegesse, Gutmann, Rainforth) is longer — the memo drops middle authors silently. Not fatal but should be flagged (either use "et al." or list the full byline).

### m7 — "Roth & Kroo 2008" DETC vs. AIAA
> "Collaborative Optimization (CO; see [Roth & Kroo 2008](https://doi.org/10.1115/DETC2008-50038))"

There are two Roth & Kroo 2008 papers on Enhanced Collaborative Optimization: the ASME DETC2008-50038 and the AIAA 2008-5841 (MDO conference). Both exist; the DOI resolves. The memo correctly cites *one* of them but might benefit from also pointing at the AIAA 2008-5841 which is the more frequently cited version.

---

## Faithfulness of the four literatures

- **MDAO / coupled BO** — represented faithfully. The MDF/IDF/AAO taxonomy, XDSM, and the linked-GP / deep-GP line are all cited to primary sources. The characterization of Tao et al. 2021 as "which subsystem to query" is correctly hedged in the Caveats block ("specific per-model acquisition function is inferred from the JMD abstract").
- **GSA + KOH discrepancy** — faithful. Sobol'/Shapley trade-off correctly stated (Σ S_i ≠ 1 under dependence; Shapley effects always sum to Var(Y)). Kennedy–O'Hagan identifiability caveat via Brynjarsdóttir–O'Hagan 2014 is correctly hedged.
- **Decision theory / VoI** — faithful. Frazier–Powell–Dayanik 2008 as one-step VoI on the terminal decision is a reasonable framing. The Andriotis et al. 2021 POMDP mapping ("state = latent discrepancy contribution of each component") is a paraphrase and a stretch of that paper's structural-reliability framing; the memo does not claim they applied it to model-swap, so the mapping reads as an analogy and is acceptable as written. Consider making the "state = latent discrepancy" step explicitly labeled as *the memo's proposed mapping*, not the paper's.
- **Satisficing / info-gap** — faithful, with the M2 hedge above and m3 Sniedovich citation gap. The Ben-Haim "zero immunity under nominal optimization" claim is stated as strongly as Ben-Haim himself states it — that's fair reporting but a reader who does not accept info-gap axioms will not accept the claim; flag as author's-view, which the Caveats section partly does.

---

## Research-gap defensibility

The memo lists three gaps in §6. After F2 (Cho et al. 2025) is removed:

- **Gap 1 (chain-level discrepancy attribution)** — defensible as an *absence-of-citation* claim, but currently overstated. See M1. Downgrade language from "No published procedure combines ..." to "We are not aware of a published procedure that combines ...".
- **Gap 2 (model-swap as experimental-design action)** — defensible; the memo hedges appropriately ("natural extension ... but has not been published as such").
- **Gap 3 (coupled satisficing + BO)** — defensible; hedged appropriately.

Overall the gap section is close to acceptable *once F2 is removed and M1 is softened*.

---

## Recommendations (ordered by revision priority)

1. **Fix F1, F2, F3 in body and Sources.** These are non-negotiable — one wrong author (Peña vs. Muñoz), one fabricated arXiv ID (2606.21539), one wrong author-and-year (Wilson 2024 vs. Xie et al. 2025).
2. **Rewrite the "still open in 2025" sentence** in §2 and §6 so it no longer depends on the removed Cho et al. citation (M1).
3. **Soften M2 Manski attribution** and add an actual Sniedovich citation for m3.
4. **Split M3 linked-GP claim** across Kyzyurova et al. and Ming & Guillas.
5. **Cosmetic:** m4–m7 fixes and abbreviation consistency.

---

## Sources consulted for this verification pass

- HESS 28:2531 (2024) landing page — https://hess.copernicus.org/articles/28/2531/2024/ (Muñoz, Moftakhari, Moradkhani; DOI 10.5194/hess-28-2531-2024)
- arXiv:2507.12453 — https://arxiv.org/abs/2507.12453 ("Cost-aware Stopping for Bayesian Optimization", submitted July 2025; code repo QianJaneXie/CostAwareStoppingBayesOpt)
- Search for arXiv:2606.21539 (Cho/Zhang/Zhou "gap attribution") — no matching record found
- PMLR v115 wu20a — https://proceedings.mlr.press/v115/wu20a.html (Wu, Toscano-Palmerin, Frazier, Wilson; UAI 2019, PMLR volume dated 2020)
- DETC2008-50038 (Roth & Kroo, "Enhanced Collaborative Optimization") — https://doi.org/10.1115/DETC2008-50038

```acceptance-report
{
  "criteriaSatisfied": [
    {
      "id": "criterion-1",
      "status": "satisfied",
      "evidence": "Verification-only pass. Produced findings file at the parent-specified path; no edits to the source memo or package code."
    }
  ],
  "changedFiles": [
    ".pi-subagents/artifacts/outputs/acc3f60c/outputs/.drafts/multi-model-system-optimization-verification.md"
  ],
  "testsAddedOrUpdated": [],
  "commandsRun": [
    {
      "command": "web_search (arXiv 2606.21539, arXiv 2507.12453, HESS 28/2531/2024, Wu et al. UAI 2019 v115, Roth & Kroo 2008)",
      "result": "passed",
      "summary": "Confirmed F1 wrong authors (Muñoz not Peña), F2 non-existent arXiv ID, F3 wrong year+author (Xie 2025 not Wilson 2024)"
    }
  ],
  "validationOutput": [
    "3 FATAL citation errors (F1 Peña→Muñoz, F2 arXiv:2606.21539 fabricated, F3 Wilson 2024→Xie 2025)",
    "4 MAJOR issues: overstated gap novelty, Manski overreach, LinkedGASP conflation, Higdon 2004/2008 scope",
    "7 MINOR polish items including MAUD attribution, Sniedovich unsourced, Foster et al. byline",
    "Four literatures faithfully represented modulo the fixes above; gap section defensible once F2 is removed and M1 softened"
  ],
  "residualRisks": [
    "PDFs were not fetched per instructions; verification relied on search-engine metadata for landing pages",
    "Byron 2004 Cambridge DOI and a few older DOIs were not individually checked (low risk)"
  ],
  "noStagedFiles": true,
  "diffSummary": "New verification memo only; source cited memo unchanged.",
  "reviewFindings": [
    "blocker: 3 FATAL citation errors in outputs/.drafts/multi-model-system-optimization-cited.md must be fixed before the memo is shared externally"
  ],
  "manualNotes": "The load-bearing 'chain-level discrepancy attribution is still open in 2025' claim currently depends on a fabricated arXiv ID and should be rewritten as an authors'-assessment claim after F2 is removed."
}
```
