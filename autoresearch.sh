#!/usr/bin/env bash
set -euo pipefail

repository_root=$(git rev-parse --show-toplevel)
cd "$repository_root"

if test -n "$(git status --porcelain --untracked-files=all)"; then
  echo "autoresearch requires a clean signed revision" >&2
  exit 2
fi

iteration_root="benchmarks/partial_network/iterations/item9-remediation"
mkdir -p "$iteration_root"

iteration=1
while test -e "$iteration_root/iteration-$(printf '%02d' "$iteration")"; do
  iteration=$((iteration + 1))
done
if test "$iteration" -gt 6; then
  echo "autoresearch benchmark-run cap of 6 is exhausted" >&2
  exit 2
fi

output="$iteration_root/iteration-$(printf '%02d' "$iteration")"
echo "autoresearch iteration $iteration of 6"
echo "output: $output"

set +e
python -m autoengineering.benchmarks.partial_network --output "$output"
benchmark_status=$?
set -e

if test "$benchmark_status" -gt 1; then
  echo "benchmark execution failed with status $benchmark_status" >&2
  exit "$benchmark_status"
fi

python -c 'import json, pathlib, sys; gate=json.loads((pathlib.Path(sys.argv[1]) / "gate.json").read_text()); failed=[item["name"] for item in gate["criteria"] if not item["passed"]]; print("gate_passed={}".format(gate["passed"])); print("failed_criteria={}".format(failed))' "$output"
exit 0
