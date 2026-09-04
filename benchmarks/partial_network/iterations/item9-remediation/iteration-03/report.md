# Partial-network benchmark

Overall gate: **FAIL**

## Evidence

- Runs: 40
- Complete runs: 40
- Pooled final-regret difference, partial minus full: -0.001217
- Pooled regret-area difference, partial minus full: 0.003097

## Criteria

- PASS: `complete_matrix`
- PASS: `raw_reconstruction`
- PASS: `deterministic_action_and_result_replay`
- PASS: `verified_system_parent_lineage`
- PASS: `system_refresh_and_observed_recommendation`
- PASS: `controlled_informative_component`
- PASS: `final_regret_tolerance`
- PASS: `regret_area_tolerance`
- FAIL: `random_component_control`
- PASS: `conservative_component_costs`
- PASS: `bounded_fit_and_scoring_fallbacks`
- PASS: `terminal_observation_separation`

## Component selections

- `informative_chain` / `function_network_partial` / `upstream`: 5
- `informative_chain` / `function_network_partial` / `terminal`: 4
- `informative_chain` / `function_network_partial_random` / `upstream`: 10
- `informative_chain` / `function_network_partial_random` / `terminal`: 6
- `informative_chain` / `function_network_partial_cheapest_informative` / `upstream`: 13
- `informative_chain` / `function_network_partial_cheapest_informative` / `terminal`: 7
- `informative_branch` / `function_network_partial` / `left`: 2
- `informative_branch` / `function_network_partial` / `terminal`: 1
- `informative_branch` / `function_network_partial_random` / `left`: 9
- `informative_branch` / `function_network_partial_random` / `right`: 9
- `informative_branch` / `function_network_partial_random` / `terminal`: 3
- `informative_branch` / `function_network_partial_cheapest_informative` / `left`: 6
- `informative_branch` / `function_network_partial_cheapest_informative` / `right`: 4
- `informative_branch` / `function_network_partial_cheapest_informative` / `terminal`: 10

The gate evaluates Decision 0007 without changing its thresholds. Raw errors and adverse results remain in the evidence.
