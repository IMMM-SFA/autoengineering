# Analytic optimizer comparison

Committed physical starts: 251. These are development tasks, not prediction evidence.

| Cell | Stop | Best feasible objective | Process seconds |
| --- | --- | --- | --- |
| ax-continuous-0 | duplicate_proposal_no_dispatch | 0.07195486879102998 | 7.435 |
| ax-continuous-1 | evaluation_ceiling | 0.000591750315586255 | 24.880 |
| ax-continuous-2 | failed_without_summary:4_starts | None | 2.566 |
| ax-mixed-0 | failed_without_summary:4_starts | None | 2.207 |
| ax-mixed-1 | failed_without_summary:4_starts | None | 2.078 |
| ax-mixed-2 | failed_without_summary:4_starts | None | 2.194 |
| ax-conditional-0 | failed_without_summary:0_starts | None | 2.065 |
| ax-conditional-1 | failed_without_summary:0_starts | None | 2.059 |
| ax-conditional-2 | failed_without_summary:0_starts | None | 2.239 |
| optuna-continuous-0 | evaluation_ceiling | 0.06194563333069528 | 0.868 |
| optuna-continuous-1 | evaluation_ceiling | 0.0399597040497437 | 0.845 |
| optuna-continuous-2 | evaluation_ceiling | 0.049482169562207814 | 0.861 |
| optuna-mixed-0 | evaluation_ceiling | 0.11425702232421278 | 0.978 |
| optuna-mixed-1 | evaluation_ceiling | 0.008266749188562374 | 1.010 |
| optuna-mixed-2 | evaluation_ceiling | 0.0460790485569612 | 0.982 |
| optuna-conditional-0 | evaluation_ceiling | 0.10349695963327833 | 0.974 |
| optuna-conditional-1 | evaluation_ceiling | 0.026454726256145113 | 0.873 |
| optuna-conditional-2 | evaluation_ceiling | 0.03785254602261395 | 0.979 |
| sobol-continuous-0 | evaluation_ceiling | 0.020154959686278093 | 0.859 |
| sobol-continuous-1 | evaluation_ceiling | 0.03629703858603709 | 0.901 |
| sobol-continuous-2 | evaluation_ceiling | 0.016124443935248426 | 0.890 |
| sobol-mixed-0 | evaluation_ceiling | 0.0139818211036393 | 0.901 |
| sobol-mixed-1 | evaluation_ceiling | 0.008266749188562374 | 0.875 |
| sobol-mixed-2 | evaluation_ceiling | 0.005576751837188868 | 0.896 |
| sobol-conditional-0 | evaluation_ceiling | 0.08541022982839892 | 0.864 |
| sobol-conditional-1 | evaluation_ceiling | 0.07005739417183068 | 0.868 |
| sobol-conditional-2 | evaluation_ceiling | 0.02304281338670816 | 0.851 |

Selection requires separate API, license, recovery, resource and burden gates.
A duplicate proposal stops dispatch without an invented failed evaluation.
