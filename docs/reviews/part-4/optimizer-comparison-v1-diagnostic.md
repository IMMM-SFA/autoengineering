# Analytic optimizer comparison

Committed physical starts: 179. These are development tasks, not prediction evidence.

| Cell | Stop | Best feasible objective | Process seconds |
| --- | --- | --- | --- |
| ax-continuous-0 | duplicate_proposal_no_dispatch | 0.07195486879102998 | 10.446 |
| ax-continuous-1 | evaluation_ceiling | 0.000591750315586255 | 24.214 |
| ax-continuous-2 | failed_without_summary:4_starts | None | 2.698 |
| ax-mixed-0 | failed_without_summary:4_starts | None | 2.341 |
| ax-mixed-1 | failed_without_summary:4_starts | None | 2.098 |
| ax-mixed-2 | failed_without_summary:4_starts | None | 2.219 |
| ax-conditional-0 | failed_without_summary:0_starts | None | 0.607 |
| ax-conditional-1 | failed_without_summary:0_starts | None | 0.617 |
| ax-conditional-2 | failed_without_summary:0_starts | None | 0.615 |
| optuna-continuous-0 | evaluation_ceiling | 0.06194563333069528 | 0.961 |
| optuna-continuous-1 | evaluation_ceiling | 0.0399597040497437 | 0.859 |
| optuna-continuous-2 | evaluation_ceiling | 0.049482169562207814 | 0.858 |
| optuna-mixed-0 | evaluation_ceiling | 0.11425702232421278 | 0.861 |
| optuna-mixed-1 | evaluation_ceiling | 0.008266749188562374 | 0.876 |
| optuna-mixed-2 | evaluation_ceiling | 0.0460790485569612 | 0.993 |
| optuna-conditional-0 | failed_without_summary:0_starts | None | 0.627 |
| optuna-conditional-1 | failed_without_summary:0_starts | None | 0.621 |
| optuna-conditional-2 | failed_without_summary:0_starts | None | 0.618 |
| sobol-continuous-0 | evaluation_ceiling | 0.020154959686278093 | 0.864 |
| sobol-continuous-1 | evaluation_ceiling | 0.03629703858603709 | 0.867 |
| sobol-continuous-2 | evaluation_ceiling | 0.016124443935248426 | 0.868 |
| sobol-mixed-0 | evaluation_ceiling | 0.0139818211036393 | 0.854 |
| sobol-mixed-1 | evaluation_ceiling | 0.008266749188562374 | 0.857 |
| sobol-mixed-2 | evaluation_ceiling | 0.005576751837188868 | 0.857 |
| sobol-conditional-0 | failed_without_summary:0_starts | None | 0.602 |
| sobol-conditional-1 | failed_without_summary:0_starts | None | 0.611 |
| sobol-conditional-2 | failed_without_summary:0_starts | None | 0.607 |

Selection requires separate API, license, recovery, resource and burden gates.
A duplicate proposal stops dispatch without an invented failed evaluation.
