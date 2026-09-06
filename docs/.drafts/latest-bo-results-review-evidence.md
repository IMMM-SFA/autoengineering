# Latest BO results evidence

Inspected the implementation worktree at `/private/tmp/autoengineering-bayesian-implementation`.
Its HEAD was `16f730e` and its status was clean before and after verification.

Sources inspected:

- `autoresearch-common-utility.md`: September 5 completion and stop state.
- `docs/decisions/0007-partial-network-benchmark.md`: evaluator-cost comparison contract.
- `docs/decisions/0010-partial-network-common-utility.md`: common utility and final remediation rule.
- `benchmarks/partial_network/common-utility/development-manifest.json`: all six
  recorded evidence file hashes matched current bytes.
- `benchmarks/partial_network/common-utility/development/`: read report, gate, and
  run summary, and rebuilt all five derived artifacts from raw records.
- `src/autoengineering/benchmarks/partial_network/__main__.py`: inspected verifier
  behavior before executing it. Existing output is verified without mutation.
- `src/autoengineering/benchmarks/partial_network/summary.py`: inspected gate rules.
- `benchmarks/full_network/results/report.md`: earlier matching gate PASS.
- `benchmarks/release_a/results/report.md`: earlier whole-system gate PASS.

Verification command:

```text
pixi run -e bayes python -m autoengineering.benchmarks.partial_network --output benchmarks/partial_network/common-utility/development
```

Exit 1, `Partial-network benchmark gate: FAIL`. No verifier error occurred.
This confirms source/decision hashes and byte-identical artifact reconstruction,
then returns the scientific gate failure. No new optimizer replay was executed.

Independent CSV aggregation: five seeds in each of eight problem/method groups.
Median regret areas, value policy versus random: chain 0.14465312543546957 versus
0.14386629895452266; branch 0.279598528789492 versus 0.27959852878949204.
Median optimizer overhead seconds, value/random/full: chain 44.792/0.049/0.202;
branch 130.278/0.094/0.315. Timing values are descriptive and were not rerun.

Reported component counts: value policy six chain actions and five branch actions.
Controlled branch counts left two, right one. All 40 runs complete; zero fallbacks.
The gate reports replay consistency in 40 runs and lineage/separation checks on
90 component actions across methods. These are distinct from fresh execution.
