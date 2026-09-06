# Model search results report

Create a standalone Quarto report at reports/model-search-results/report.qmd and
report.html using the audited RESULTS.md and its underlying JSON records.

The approach will live in docs/optimization.md, with a concise entry in concept.md
and operational guidance in .claude/agents/auto-engineer.md. Add the requested TODO
there and save verified BO references in the report bibliography and a reusable
background_research note. No optimizer policy or frozen experiment changes.

Figures replace numeric tables: target calls and censoring; paired validation and
held-out checkpoints; model and controller time; search dimension and evaluation
cost; solar selection/test improvements; wind coarse/fine-grid sensitivity; hybrid
revenue and SOC screening. Show replicate structure without claiming confidence
intervals from these few seeds. Use interactive model/experiment selectors where
useful, consistent method colors, and static SVG fallbacks for print.

Claims: target difficulty is distinct from physical detail; initialization solves
many easy cases; BO can improve validation attainment without improving held-out
prediction; infeasibility and wind sensitivity qualify apparent component gains.
Retrospective cutoff and unequal success rates remain explicit. The pilot rule is
an adopted working heuristic, not a validated universal classifier.

Verify aggregate values against every RESULTS.md numeric table used, hash inputs,
retain figure JSON and CSV exports, validate citations, render self-contained HTML,
inspect desktop and narrow layouts in both themes, check Plotly layout, and obtain
an independent final review. Use a separate report Pixi environment so the frozen
model environment manifests remain unchanged.
