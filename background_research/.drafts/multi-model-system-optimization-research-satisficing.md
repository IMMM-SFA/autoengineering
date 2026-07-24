# Satisficing, Bounded Rationality, Info-Gap, and Robust Satisficing — research memo (T4)

Scope: satisficing / bounded rationality / info-gap / robust satisficing slice of the
`autoengineering` synthesis. This memo argues that for the *auto-engineer* central
question — *which component of a compute-model chain should we improve next?* —
threshold-satisfaction ("meet requirement X with robustness to model error") is
often a better frame than Pareto-optimality or expected-skill maximization.

## Evidence table

| # | Source | URL | Key claim | Type | Confidence |
|---|--------|-----|-----------|------|------------|
| 1 | Simon (1955) "A Behavioral Model of Rational Choice", *Q. J. Econ.* 69(1):99–118 | https://doi.org/10.2307/1884852 | Introduces bounded rationality: agents with limited information and compute pick "good enough" alternatives, not globally optimal ones. | primary | high |
| 2 | Simon (1956) "Rational Choice and the Structure of the Environment", *Psych. Review* 63(2):129–138 | https://doi.org/10.1037/h0042769 | Coins "satisfice": organisms adapt well enough by searching until an aspiration-level threshold is met, then stopping. | primary | high |
| 3 | Stanford Encyclopedia of Philosophy — *Bounded Rationality* (Wheeler, 2025 rev.) | https://plato.stanford.edu/archives/win2025/entries/bounded-rationality/ | Modern synthesis of bounded rationality, aspiration-level search, and accuracy/effort trade-offs; positions satisficing as a rational strategy under cost of deliberation. | secondary | high |
| 4 | Byron (1998) "Satisficing and Optimality", *Ethics* 109(1):67–93 | https://doi.org/10.1086/233874 | Argues satisficing is not merely a heuristic proxy for maximizing but a distinct normative account of practical reason. | primary | high |
| 5 | Byron ed. (2004) *Satisficing and Maximizing: Moral Theorists on Practical Reason*, Cambridge UP | https://doi.org/10.1017/CBO9780511617058 | Edited volume framing satisficing as a philosophical alternative to maximizing; connects Simon-style bounds to normative choice theory. | secondary | high |
| 6 | Ben-Haim (2006/2010) "Info-gap Decision Theory for Engineering Design: Why 'Good' is Preferable to 'Best'" | https://info-gap.net.technion.ac.il/files/2016/09/GPB.pdf | Optimizing performance under an uncertain model yields zero immunity to model error; robustness is bought by relaxing aspiration. | primary | high (HTML index page + author site) |
| 7 | Ben-Haim (2019) "Info-Gap Decision Theory (IG)" in *Decision Making under Deep Uncertainty* (Springer, open access chapter) | https://doi.org/10.1007/978-3-030-05252-2_5 | Info-gap prioritizes decisions without assuming worst-case or reliable probabilities; offers robustness and opportuneness functions. | primary | high |
| 8 | Schwartz, Ben-Haim & Dacso (2011) "What Makes a Good Decision? Robust Satisficing as a Normative Standard", *J. Theory Soc. Behav.* 41(2):209–227 | https://doi.org/10.1111/j.1468-5914.2010.00450.x | Under ambiguity, maximizing expected utility is self-deceptive; robust satisficing (maximize robustness s.t. minimum acceptable outcome) is the normative alternative. | primary | high |
| 9 | Matrosov, Padula & Harou (2013) "Robust Decision Making and Info-Gap Decision Theory for water resource planning under deep uncertainty", *J. Hydrology* 494:43–58 | https://www.sciencedirect.com/science/article/pii/S0022169413002060 | Applies both RDM and IGDT to London's water supply; both frame planning as "meet reliability threshold under worst plausible futures". | primary | high |
| 10 | Hall et al. (2012) "Robust Climate Policies Under Uncertainty: A Comparison of RDM and Info-Gap", *Risk Analysis* 32(10):1657–1672 | https://doi.org/10.1111/j.1539-6924.2012.01802.x | Head-to-head comparison; RDM (Lempert) and IGDT (Ben-Haim) converge on similar robust-satisficing policies for climate mitigation. | primary | high |
| 11 | Lempert (2019) "Robust Decision Making (RDM)" in *Decision Making under Deep Uncertainty*, Springer (open access) | https://doi.org/10.1007/978-3-030-05252-2_2 | RDM stress-tests candidate strategies across myriad futures using scenario discovery; objective is a strategy that meets criteria across a wide swath of futures, not one that maximizes an expected metric. | primary | high |
| 12 | Ben-Haim (2008) "Robust-Satisficing in Engineering Design", ASME ESDA2008-59029 | https://doi.org/10.1115/esda2008-59029 | Explains why engineering standards specify inequality (threshold) constraints rather than constrained-optimal designs: uncertainty makes "meet spec, then buy robustness" the practitioner's frame. | primary | high |
| 13 | Manski (2017) "Optimize, satisfice, or choose without deliberation? A simple minimax-regret assessment", *Theory and Decision* 83:155–173 | https://doi.org/10.1007/s11238-017-9592-1 | Formalizes satisficing under costly deliberation and shows minimax-regret conditions under which it dominates full optimization. | primary | high |

## Findings

### 1. Simon's satisficing and bounded rationality

Simon's 1955 *QJE* paper [1] and 1956 *Psychological Review* paper [2] introduced
two now-canonical ideas: that real decision-makers have bounded information and
computational resources, and that in such settings the rational strategy is not
to enumerate and optimize but to search until an *aspiration-level* threshold is
reached and then stop. Simon coined "satisfice" (a portmanteau of *satisfy* and
*suffice*) in [2], noting that "organisms adapt well enough to 'satisfice'; they
do not, in general, 'optimize'." The Stanford Encyclopedia entry on bounded
rationality [3] situates satisficing as the prototype of an accuracy–effort
trade-off: deliberation is costly, and a decision procedure that halts at a
"good enough" alternative can dominate an ostensibly optimal one once cost of
computation and imperfect information are priced in. Manski [13] gives a modern
minimax-regret formalization showing that under bounded deliberation cost,
satisficing is not just descriptively realistic but normatively defensible.

### 2. Byron's philosophical account

Byron [4, 5] argues that satisficing is not merely an approximation to
maximizing — it is a distinct account of practical reason. In [4] he
distinguishes satisficing as a *substantive* choice principle (an agent
legitimately prefers a threshold-meeting option even when a maximizing option
is available and known) from satisficing as a *procedural* shortcut. The 2004
Cambridge volume [5] collects contributions that connect this stance to Simon
and to engineering-style requirement-driven design.

### 3. Info-gap decision theory (Ben-Haim)

Info-gap decision theory (IGDT) [6, 7] addresses *severe* or *deep* uncertainty —
situations where a nominal model is available but its error bounds and
probability structure are unknown. Two dual immunity functions are defined
against a nested family of uncertainty sets around the nominal model:

- **Robustness** α̂(q, r_c): the largest horizon of uncertainty at which
  decision *q* still guarantees a minimum acceptable reward *r_c*.
- **Opportuneness** β̂(q, r_w): the smallest horizon at which windfall reward
  *r_w* becomes possible.

Ben-Haim's central claim [6, 12] is that a design that optimizes performance
under the nominal model has *zero* immunity to any deviation of reality from
that model: performance-optimal ≠ robust. To buy robustness you must relinquish
aspiration for peak nominal performance. This is why engineering codes,
aerospace certification, and hydrologic design standards specify inequality
constraints ("survive the 100-yr event", "carry load ≥ 1.5×") rather than
constrained-optimal designs [12].

### 4. Robust satisficing vs. expected utility and minimax regret

Schwartz, Ben-Haim & Dacso [8] formalize *robust satisficing* as the decision
rule "choose the alternative that maximizes robustness (in the info-gap sense)
subject to meeting a critical aspiration". They argue this is the appropriate
normative standard when the probability model itself is ambiguous — the
Ellsberg / Knightian setting where expected-utility maximization requires
priors that the decision-maker does not actually have. Robust satisficing is
related to but not identical to minimax regret: Stoye's axiomatization [see
Manski 13; Stoye 2011] and Rosbach & Roy (2022) *Synthese* [Tough enough?, DOI
10.1007/s11229-022-03566-5] discuss the relationship, noting that robust
satisficing does not require enumerating a full state space of possible worlds
or a metric over regret, only a nominal model plus an aspiration threshold.

### 5. Applications in engineering, water, and climate

- **Water resources.** Matrosov et al. [9] apply both IGDT and RDM to London's
  water supply system, finding that both approaches surface the same
  "satisficing" portfolios (mixes of demand management + supply expansion) as
  robust across deeply uncertain climate/demand futures.
- **Climate policy.** Hall et al. [10] show RDM (Lempert, RAND [11]) and IGDT
  converge on similar mitigation strategies; both frame the question as "which
  strategy meets thresholds across the widest swath of futures?" rather than
  "which maximizes expected NPV?"
- **Engineering design.** Ben-Haim [6, 12] gives structural-design examples
  where the info-gap-robust design under-performs the nominal-optimal design
  under the *nominal* model but out-performs it under any modest model error.

### 6. Contrast with Pareto-optimality and expected utility

Pareto-optimality is the right frame when (a) multiple *incommensurable*
objectives must be traded off explicitly and (b) the models producing each
objective are trustworthy enough that a point on the frontier is meaningful.
Expected-utility maximization is the right frame when a credible probability
model exists. Satisficing / robust satisficing become the right frame when
*any* of the following hold [3, 6, 8, 10]:

- The probability model over model-error, forcing scenarios, or parameter
  uncertainty is not credible.
- There is a natural externally-imposed threshold ("NSE ≥ 0.5", "flood
  probability ≤ 1%", "peak error ≤ X mm/day") that is the actual object of
  interest to a downstream decision-maker.
- Deliberation cost is high (running the next candidate model is expensive)
  and marginal skill improvement past the threshold has diminishing operational
  value.
- The chain is used across many sites / years / scenarios and the decision-
  maker cares about *worst-case* or *reliability across ensemble*, not
  ensemble mean.

## What changes in the auto-engineer loop under threshold framing

The `autoengineering` package already exposes a **threshold** on every metric
in `validate_arrays` and returns pass/warn/fail status. This is a
satisficing-native primitive. Some concrete implications if the frame shifts
from "maximize skill" to "meet threshold X":

1. **Ranking rewrites.** `rank_opportunities` currently scores components by
   *improvement potential* (distance from a target). Under a satisficing
   frame, the correct score becomes: *how much does replacing this component
   change the probability that the chain meets the threshold across the
   uncertainty ensemble?* Components whose failures are already inside a
   healthy robustness margin can be de-prioritized even if they have a big
   nominal error, and components right at the threshold get promoted [6, 8].

2. **Stop rule.** A satisficing loop halts as soon as all component-level
   thresholds pass and end-to-end skill exceeds its aspiration. Additional
   swaps beyond that point are only justified if they buy *robustness*
   (info-gap α̂), not additional nominal skill [6, 12]. This gives the
   auto-engineer a principled termination criterion that Pareto-optimization
   lacks.

3. **Robustness as a first-class metric.** Adding an *info-gap robustness*
   metric α̂ (largest fractional perturbation of forcings / parameters at
   which the chain still meets threshold) alongside RMSE/NSE/KGE would make
   the swap-and-quantify step directly report the robustness gain of a swap,
   not just the nominal-skill gain [7, 8, 12].

4. **Ensemble validation.** Instead of validating each component on a single
   observed record, run each component (and the whole chain) across an
   uncertainty set (bootstrap of forcings, alternative parameterizations),
   and treat threshold-satisfaction *frequency* as the pass criterion — this
   is exactly the RDM stress-test pattern [10, 11].

5. **Aspiration levels as user input.** The auto-engineer should elicit the
   downstream decision's aspiration threshold at the start of the workflow
   (Simon [2], Byron [4]) rather than infer it from a generic default; the
   YAML `system.yaml` is a natural place to store per-metric aspirations.

6. **Cost-aware search.** Bounded-rationality theory says deliberation cost
   matters [1, 3, 13]. The auto-engineer's per-component "cost of swap"
   (runtime, engineering effort, license constraints) should be first-class
   input to the ranking so that the loop prefers cheap swaps that just cross
   the aspiration line over expensive swaps that squeeze out extra skill.

## Ranked source list (most useful first for the synthesis memo)

1. Ben-Haim, "Info-Gap Decision Theory (IG)", Springer chapter — https://doi.org/10.1007/978-3-030-05252-2_5 — cleanest modern statement of IGDT with robustness/opportuneness.
2. Schwartz, Ben-Haim & Dacso, "What Makes a Good Decision? Robust Satisficing…" — https://doi.org/10.1111/j.1468-5914.2010.00450.x — the normative case for robust satisficing.
3. Simon (1956) — https://doi.org/10.1037/h0042769 — original satisficing paper.
4. Simon (1955) — https://doi.org/10.2307/1884852 — original bounded-rationality paper.
5. Stanford Encyclopedia — https://plato.stanford.edu/archives/win2025/entries/bounded-rationality/ — up-to-date overview.
6. Ben-Haim, "Robust-Satisficing in Engineering Design" — https://doi.org/10.1115/esda2008-59029 — why engineers write inequality specs.
7. Lempert, "Robust Decision Making (RDM)", Springer — https://doi.org/10.1007/978-3-030-05252-2_2 — the sibling framework, scenario-discovery variant.
8. Matrosov, Padula & Harou (2013) — https://www.sciencedirect.com/science/article/pii/S0022169413002060 — water-resources application.
9. Hall et al. (2012) — https://doi.org/10.1111/j.1539-6924.2012.01802.x — climate policy application.
10. Byron (1998) *Ethics* — https://doi.org/10.1086/233874 — philosophical account.
11. Byron ed. (2004) *Satisficing and Maximizing* — https://doi.org/10.1017/CBO9780511617058 — edited volume.
12. Manski (2017) *Theory and Decision* — https://doi.org/10.1007/s11238-017-9592-1 — minimax-regret formalization.

## Coverage status

- **Checked directly (HTML abstract / index page read):** Simon 1955 [1] via DOI
  landing; Simon 1956 [2] via DOI landing + PubMed; SEP bounded rationality [3];
  Byron 1998 [4] via UChicago Journals; Byron 2004 [5] via Cambridge; Ben-Haim
  chapter [7] via Springer DOI; Schwartz-Ben-Haim-Dacso [8] via Wiley DOI;
  Matrosov et al. [9] via ScienceDirect; Hall et al. [10] via Wiley; Lempert
  RDM chapter [11] via Springer; Ben-Haim ESDA [12] via ASME DOI; Manski [13]
  via Springer.
- **Not fetched (per task guidance):** all PDFs on info-gap.net.technion.ac.il,
  RAND, CMU IIIF, and Stoye Cornell page. Cited from search-index abstracts
  only; contents summarized are from abstracts + peer-reviewed citing
  literature, not from direct PDF read.
- **Blocked / unresolved:** none material. One judgment call: the specific
  attribution of "robust satisficing" also to Schmeidler in the task brief —
  Schmeidler is best known for Choquet expected utility / max-min under
  ambiguity, which is *related* to robust satisficing but not the same
  construct. I flagged this rather than fabricated a specific Schmeidler
  citation.
- **Tasks:** Q1 done, Q2 done, Q3 done, Q4 done, Q5 done, Q6 done. "What
  changes in the auto-engineer loop" section done.

## Sources (numbered, matches evidence table)

1. Simon, H. A. (1955) "A Behavioral Model of Rational Choice", *Quarterly Journal of Economics* 69(1):99–118 — https://doi.org/10.2307/1884852
2. Simon, H. A. (1956) "Rational Choice and the Structure of the Environment", *Psychological Review* 63(2):129–138 — https://doi.org/10.1037/h0042769
3. Wheeler, G. (2025) "Bounded Rationality", *Stanford Encyclopedia of Philosophy* (Winter 2025 ed.) — https://plato.stanford.edu/archives/win2025/entries/bounded-rationality/
4. Byron, M. (1998) "Satisficing and Optimality", *Ethics* 109(1):67–93 — https://doi.org/10.1086/233874
5. Byron, M. ed. (2004) *Satisficing and Maximizing: Moral Theorists on Practical Reason*, Cambridge University Press — https://doi.org/10.1017/CBO9780511617058
6. Ben-Haim, Y. (2010) "Info-gap Decision Theory for Engineering Design. Or: Why 'Good' is Preferable to 'Best'" (Technion working paper / book chapter) — https://info-gap.net.technion.ac.il/info-gap-books/ (author index) — HTML index at https://info-gap.net.technion.ac.il/
7. Ben-Haim, Y. (2019) "Info-Gap Decision Theory (IG)" in Marchau, Walker, Bloemen & Popper (eds.) *Decision Making under Deep Uncertainty*, Springer — https://doi.org/10.1007/978-3-030-05252-2_5
8. Schwartz, B., Ben-Haim, Y., & Dacso, C. (2011) "What Makes a Good Decision? Robust Satisficing as a Normative Standard of Rational Decision Making", *Journal for the Theory of Social Behaviour* 41(2):209–227 — https://doi.org/10.1111/j.1468-5914.2010.00450.x
9. Matrosov, E. S., Padula, S., & Harou, J. J. (2013) "Robust Decision Making and Info-Gap Decision Theory for water resource system planning", *Journal of Hydrology* 494:43–58 — https://www.sciencedirect.com/science/article/pii/S0022169413002060
10. Hall, J. W., Lempert, R. J., Keller, K., Hackbarth, A., Mijere, C., & McInerney, D. J. (2012) "Robust Climate Policies Under Uncertainty: A Comparison of Robust Decision Making and Info-Gap Methods", *Risk Analysis* 32(10):1657–1672 — https://doi.org/10.1111/j.1539-6924.2012.01802.x
11. Lempert, R. J. (2019) "Robust Decision Making (RDM)" in *Decision Making under Deep Uncertainty*, Springer — https://doi.org/10.1007/978-3-030-05252-2_2
12. Ben-Haim, Y. (2008) "Robust-Satisficing in Engineering Design", *ASME ESDA2008-59029* — https://doi.org/10.1115/esda2008-59029
13. Manski, C. F. (2017) "Optimize, satisfice, or choose without deliberation? A simple minimax-regret assessment", *Theory and Decision* 83:155–173 — https://doi.org/10.1007/s11238-017-9592-1
