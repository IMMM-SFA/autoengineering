# Release A benchmark report

Gate result: PASS

## Aggregate results

| Problem | Method | Runs | Mean final regret | Median | P10 | P90 | Mean regret area |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| smooth_continuous | fixed | 30 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.177778 |
| smooth_continuous | random | 30 | 0.022187 | 0.014329 | 0.001626 | 0.043176 | 0.170429 |
| smooth_continuous | sobol | 30 | 0.017286 | 0.014043 | 0.005373 | 0.036269 | 0.159449 |
| smooth_continuous | smac | 30 | 0.019416 | 0.016589 | 0.001871 | 0.037793 | 0.160030 |
| smooth_continuous | botorch | 30 | 0.000443 | 0.000158 | 0.000029 | 0.001106 | 0.153640 |
| constrained_continuous | fixed | 30 | 0.080000 | 0.080000 | 0.080000 | 0.080000 | 0.264000 |
| constrained_continuous | random | 30 | 0.108643 | 0.026905 | 0.003344 | 0.130695 | 0.380547 |
| constrained_continuous | sobol | 30 | 0.042009 | 0.027057 | 0.008446 | 0.102709 | 0.303106 |
| constrained_continuous | smac | 30 | 0.076102 | 0.038210 | 0.005778 | 0.166963 | 0.314705 |
| constrained_continuous | botorch | 30 | 0.001832 | 0.000188 | 0.000019 | 0.003376 | 0.293860 |
| mixed_space | fixed | 30 | 0.045156 | 0.045156 | 0.045156 | 0.045156 | 0.174250 |
| mixed_space | random | 30 | 0.047623 | 0.040390 | 0.002491 | 0.126247 | 0.194119 |
| mixed_space | sobol | 30 | 0.046292 | 0.044598 | 0.000127 | 0.087227 | 0.191735 |
| mixed_space | smac | 30 | 0.068444 | 0.081627 | 0.005122 | 0.120252 | 0.195581 |
| mixed_space | botorch | 30 | 0.031049 | 0.014168 | 0.000010 | 0.082845 | 0.187928 |
| conditional_space | fixed | 30 | 0.080000 | 0.080000 | 0.080000 | 0.080000 | 0.210000 |
| conditional_space | random | 30 | 0.049233 | 0.043183 | 0.017582 | 0.100140 | 0.199712 |
| conditional_space | sobol | 30 | 0.061386 | 0.058127 | 0.012497 | 0.103242 | 0.187636 |
| conditional_space | smac | 30 | 0.054272 | 0.040958 | 0.010459 | 0.102531 | 0.186282 |
| conditional_space | botorch | 30 | 0.026729 | 0.006797 | 0.000408 | 0.091054 | 0.182375 |
| noisy_chain | fixed | 30 | 0.059647 | 0.061375 | 0.044378 | 0.074083 | 0.181593 |
| noisy_chain | random | 30 | 0.062963 | 0.056054 | 0.003790 | 0.141168 | 0.240124 |
| noisy_chain | sobol | 30 | 0.048034 | 0.036679 | 0.012312 | 0.103205 | 0.180807 |
| noisy_chain | smac | 30 | 0.047080 | 0.034955 | 0.003930 | 0.109920 | 0.180338 |
| noisy_chain | botorch | 30 | 0.032427 | 0.023144 | 0.000000 | 0.090988 | 0.173424 |

## Release criteria

| Criterion | Result | Details |
| --- | --- | --- |
| complete_matrix | PASS | `{"complete_runs":750,"exact_evaluation_indices":true,"expected_evaluations":7500,"expected_runs":750,"missing_runs":0,"observed_evaluations":7500,"observed_runs":750,"unexpected_runs":0}` |
| scientific_record_audit | PASS | `{"issue_count":0,"passed":true,"reported_issues":[]}` |
| valid_and_within_budget | PASS | `{"budget_overruns":0,"invalid_configurations":0}` |
| native_replay | PASS | `{"consistent_native_runs":600,"expected_native_runs":600,"observed_native_runs":600}` |
| smac_completion | PASS | `{"complete_smac_runs":150,"expected_smac_runs":150,"observed_smac_runs":150}` |
| bounded_botorch_fallbacks | PASS | `{"maximum_in_one_run":1,"modeled_suggestions":750,"unresolved_rate":0.004,"unresolved_suggestions":3}` |
| botorch_vs_random_pooled | PASS | `{"botorch_area":0.19824529319389358,"botorch_final":0.018496074915765246,"complete":true,"per_problem":{"conditional_space":{"botorch_final":0.026728933645290654,"random_final":0.04923261682631179,"sobol_final":0.061385954093287835},"constrained_continuous":{"botorch_final":0.0018318943103501461,"random_final":0.10864288318238809,"sobol_final":0.04200910737508039},"mixed_space":{"botorch_final":0.031049330217502825,"random_final":0.04762296428927775,"sobol_final":0.04629176932011204},"noisy_chain":{"botorch_final":0.032427348698825215,"random_final":0.06296307668784115,"sobol_final":0.048033607036739666},"smooth_continuous":{"botorch_final":0.0004428677068573935,"random_final":0.022186584481935834,"sobol_final":0.01728647140519942}},"random_area":0.23698619405959903,"random_final":0.05812962509355092,"sobol_area":0.20454688939788754,"sobol_final":0.04300138184608387}` |
| botorch_vs_sobol_pooled | PASS | `{"botorch_area":0.19824529319389358,"botorch_final":0.018496074915765246,"complete":true,"per_problem":{"conditional_space":{"botorch_final":0.026728933645290654,"random_final":0.04923261682631179,"sobol_final":0.061385954093287835},"constrained_continuous":{"botorch_final":0.0018318943103501461,"random_final":0.10864288318238809,"sobol_final":0.04200910737508039},"mixed_space":{"botorch_final":0.031049330217502825,"random_final":0.04762296428927775,"sobol_final":0.04629176932011204},"noisy_chain":{"botorch_final":0.032427348698825215,"random_final":0.06296307668784115,"sobol_final":0.048033607036739666},"smooth_continuous":{"botorch_final":0.0004428677068573935,"random_final":0.022186584481935834,"sobol_final":0.01728647140519942}},"random_area":0.23698619405959903,"random_final":0.05812962509355092,"sobol_area":0.20454688939788754,"sobol_final":0.04300138184608387}` |
| botorch_problem_limits | PASS | `{"per_problem":{"conditional_space":{"botorch_final":0.026728933645290654,"random_final":0.04923261682631179,"sobol_final":0.061385954093287835},"constrained_continuous":{"botorch_final":0.0018318943103501461,"random_final":0.10864288318238809,"sobol_final":0.04200910737508039},"mixed_space":{"botorch_final":0.031049330217502825,"random_final":0.04762296428927775,"sobol_final":0.04629176932011204},"noisy_chain":{"botorch_final":0.032427348698825215,"random_final":0.06296307668784115,"sobol_final":0.048033607036739666},"smooth_continuous":{"botorch_final":0.0004428677068573935,"random_final":0.022186584481935834,"sobol_final":0.01728647140519942}},"random_wins_or_ties":5}` |

## Run failures

Incomplete runs: 0
