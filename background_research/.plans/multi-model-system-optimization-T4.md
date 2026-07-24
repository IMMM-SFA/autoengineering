# Researcher brief T4 — Satisficing, bounded rationality, info-gap, and robust optimization

## Context

Feeding into a synthesis memo for `autoengineering`, whose central question is *which component in a system of compute models should we improve next?* The user has explicitly flagged **satisficing** as under-covered in the existing corpus (`background_research/deep_research_refs.csv`). Optimizing to Pareto-optimality may be the wrong framing when threshold-satisfaction is what actually matters in engineering practice.

## Scope

You are **only** responsible for the **satisficing / bounded rationality / info-gap / robust satisficing** slice.

## Questions to answer

1. **Simon's satisficing.**
   - Herbert Simon (1955/1956) "A Behavioral Model of Rational Choice" and "Rational Choice and the Structure of the Environment", *Psychological Review*.
   - Bounded rationality; aspiration levels; "good enough" solutions.
2. **Byron's account of satisficing** as a philosophical alternative to maximizing, and connections to engineering design.
3. **Info-gap decision theory (Yakov Ben-Haim).**
   - Ben-Haim, *Info-Gap Decision Theory: Decisions Under Severe Uncertainty*, Academic Press, 2nd ed. 2006.
   - Robustness vs. opportuneness functions.
   - Applications in engineering, water resources, climate adaptation.
4. **Robust satisficing** as an alternative to expected-utility maximization when the probability model itself is uncertain.
   - Robust satisficing (Ben-Haim, Schmeidler); connection to minimax regret.
5. **Practical uses in engineering design.**
   - Threshold- or requirement-driven design (aerospace, hydrology, defense).
   - "Design for a level of performance" in MDAO / systems engineering.
6. **Contrast with Pareto-optimality and expected utility.** When is satisficing *the right frame* vs. multi-objective optimization?

## Deliverables

Write `outputs/.drafts/multi-model-system-optimization-research-satisficing.md` with:

- ~600–1200 word synthesis
- ~6–12 ranked sources with DOI/URL/ISBN, one-sentence takeaways
- A short section on *what changes in an "auto-engineer" loop* if the objective is "meet threshold X" rather than "maximize skill".

## Tool guidance

- Many key sources are books; cite publisher URL / Google Books / DOI where possible.
- Simon 1955 is *Quarterly Journal of Economics* 69(1), 99–118; Simon 1956 is *Psychological Review* 63(2), 129–138.
- Ben-Haim has an active author page — use `web_search` "Ben-Haim info-gap decision theory" and cite recent open-access reviews.
- Avoid PDF fetches; use HTML pages.
