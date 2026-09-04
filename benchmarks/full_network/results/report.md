# Full-observability function-network benchmark

Gate result: PASS

The frozen criteria test whether the network method matches the whole-system method. The evidence is retained whether the comparison is favorable, null, or adverse.

## Results

| Problem | Method | Runs | Median final regret | Median regret area | Fallbacks |
| --- | --- | ---: | ---: | ---: | ---: |
| smooth_chain | system | 10 | 0.007331 | 0.174853 | 0 |
| smooth_chain | function_network_full | 10 | 0.002160 | 0.164208 | 0 |
| constrained_branch | system | 10 | 0.001144 | 0.209303 | 0 |
| constrained_branch | function_network_full | 10 | 0.001889 | 0.207570 | 0 |

## Frozen criteria

| Criterion | Result | Details |
| --- | --- | --- |
| complete_matrix | PASS | `{"acquisitions":240,"complete_runs":40,"evaluations":400,"expected_runs":40,"missing_runs":0,"observed_runs":40}` |
| raw_record_audit | PASS | `{"issue_count":0,"passed":true,"reported_issues":[]}` |
| system_scope | PASS | `{"system_scope_runs":40}` |
| deterministic_replay | PASS | `{"consistent_runs":40}` |
| heldout_calibration | PASS | `{"constraint_brier":0.19822282791137696,"coverage_90":0.828125,"expected_records":320,"finite_moments":true,"issue_count":0,"observed_records":320,"reported_issues":[],"unique_records":320}` |
| pooled_final_regret_match | PASS | `{"full_median":0.002047533300596316,"full_minus_system":-0.00016750148132033127,"maximum":0.05,"system_median":0.002215034781916647}` |
| problem_final_regret_match | PASS | `{"constrained_branch":{"full_median":0.001888910935436694,"full_minus_system":0.0007449327205730216,"maximum":0.1,"system_median":0.0011439782148636723},"smooth_chain":{"full_median":0.0021599759032891463,"full_minus_system":-0.00517077033621649,"maximum":0.1,"system_median":0.007330746239505637}}` |
| pooled_regret_area_match | PASS | `{"full_median":0.17001656265556842,"full_minus_system":-0.005885910999184646,"maximum":0.05,"system_median":0.17590247365475306}` |
| bounded_full_network_fallbacks | PASS | `{"modeled_suggestions":120,"overall_maximum":0.05,"overall_rate":0.0,"problem_maximum":0.15,"problem_rates":{"constrained_branch":0.0,"smooth_chain":0.0},"unresolved_suggestions":0}` |

## Run failures

Incomplete runs: 0
