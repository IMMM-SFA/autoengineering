#!/usr/bin/env bash
set -euo pipefail

repository_root=$(git rev-parse --show-toplevel)
cd "$repository_root"

role=${1:-}
case "$role" in
  development | replacement) ;;
  *)
    echo "usage: $0 {development|replacement}" >&2
    exit 2
    ;;
esac

decision_path="docs/decisions/0010-partial-network-common-utility.md"
expected_decision_sha256="5a7c3f7da1e928c141a0490b55c26ddcaa10d39fa06517f4ff7bedab305451da"
actual_decision_sha256=$(shasum -a 256 "$decision_path" | awk '{print $1}')
if test "$actual_decision_sha256" != "$expected_decision_sha256"; then
  echo "Decision 0010 hash differs from the approved protocol" >&2
  exit 2
fi

evidence_root="benchmarks/partial_network/common-utility"
output="$evidence_root/$role"
manifest="$evidence_root/$role-manifest.json"
resume_finalization=false
if test -d "$output" && ! test -L "$output" && ! test -e "$manifest" && ! test -L "$manifest"; then
  resume_finalization=true
elif test -e "$output" || test -L "$output" || test -e "$manifest" || test -L "$manifest"; then
  echo "common-utility $role evidence already exists" >&2
  exit 2
fi

if test "$resume_finalization" = false \
  && test -n "$(git status --porcelain --untracked-files=all)"; then
  echo "common-utility benchmark requires a clean signed revision" >&2
  exit 2
fi
git verify-commit HEAD >/dev/null

if test "$role" = "replacement"; then
  development_manifest="$evidence_root/development-manifest.json"
  development_gate="$evidence_root/development/gate.json"
  if ! test -f "$development_manifest" || ! test -f "$development_gate"; then
    echo "replacement requires complete development evidence" >&2
    exit 2
  fi
  if ! python -m autoengineering.benchmarks.partial_network \
    --output "$evidence_root/development"; then
    echo "replacement requires reconstructible passing development evidence" >&2
    exit 2
  fi
  python - "$development_manifest" "$development_gate" "$expected_decision_sha256" <<'PY'
import json
from pathlib import Path
import sys

manifest = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
gate = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
if (
    manifest["role"] != "development"
    or manifest["decision_0010_sha256"] != sys.argv[3]
    or not gate["passed"]
):
    raise SystemExit("replacement requires a passing Decision 0010 development matrix")
PY
fi

echo "common-utility role: $role"
echo "output: $output"

set +e
if test "$resume_finalization" = true; then
  echo "resuming companion-manifest finalization without rerunning the matrix"
fi
python -m autoengineering.benchmarks.partial_network --output "$output"
benchmark_status=$?
set -e
if test "$benchmark_status" -gt 1; then
  echo "benchmark execution failed with status $benchmark_status" >&2
  exit "$benchmark_status"
fi

python - "$role" "$output" "$manifest" "$expected_decision_sha256" <<'PY'
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from autoengineering.benchmarks.partial_network.__main__ import (
    repository_root,
    source_file_hashes,
    source_hash,
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def directory_sha256(root: Path, repository: Path) -> str:
    lines = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(repository).as_posix()
        lines.append(f"{sha256(path)}  {relative}\n")
    return hashlib.sha256("".join(lines).encode()).hexdigest()


role = sys.argv[1]
root = repository_root()
output_argument = Path(sys.argv[2])
manifest_argument = Path(sys.argv[3])
expected_decision_sha256 = sys.argv[4]
output = (
    (root / output_argument).resolve()
    if not output_argument.is_absolute()
    else output_argument
)
manifest_path = (
    (root / manifest_argument).resolve()
    if not manifest_argument.is_absolute()
    else manifest_argument
)
gate = json.loads((output / "gate.json").read_text(encoding="utf-8"))
provenance = gate["provenance"]
execution_head = provenance["git_head_at_execution"]
subprocess.run(
    ["git", "verify-commit", execution_head],
    cwd=root,
    check=True,
    capture_output=True,
    text=True,
)
current_head = subprocess.run(
    ["git", "rev-parse", "HEAD"],
    cwd=root,
    check=True,
    capture_output=True,
    text=True,
).stdout.strip()
if current_head != execution_head:
    raise SystemExit("current revision differs from the completed matrix")
if provenance["source_sha256"] != source_hash(root):
    raise SystemExit("current benchmark source differs from the completed matrix")
if provenance["source_file_sha256"] != source_file_hashes(root):
    raise SystemExit("current benchmark source-file inventory differs from the completed matrix")
if sha256(root / "docs/decisions/0010-partial-network-common-utility.md") != (
    expected_decision_sha256
):
    raise SystemExit("Decision 0010 differs from the controller contract")

payload = {
    "schema_version": "1.0",
    "role": role,
    "decision_0007_sha256": sha256(root / "docs/decisions/0007-partial-network-benchmark.md"),
    "decision_0008_sha256": sha256(
        root / "docs/decisions/0008-partial-network-candidate-generation.md"
    ),
    "decision_0009_sha256": sha256(
        root / "docs/decisions/0009-partial-network-decision-pool.md"
    ),
    "decision_0010_sha256": expected_decision_sha256,
    "git_head_at_execution": execution_head,
    "git_commit_signed": True,
    "git_tree_clean_at_start": bool(provenance["git_tree_clean"]),
    "command": f"pixi run -e bayes bash autoresearch-common-utility.sh {role}",
    "source_sha256": provenance["source_sha256"],
    "source_file_sha256": provenance["source_file_sha256"],
    "raw_sha256": sha256(output / "raw-records.jsonl"),
    "evidence_directory_sha256": directory_sha256(output, root),
    "evidence_file_sha256": {
        path.relative_to(output).as_posix(): sha256(path)
        for path in sorted(item for item in output.rglob("*") if item.is_file())
    },
    "gate_passed": bool(gate["passed"]),
    "failed_criteria": [
        criterion["name"] for criterion in gate["criteria"] if not criterion["passed"]
    ],
    "python": provenance["python"],
    "platform": provenance["platform"],
    "packages": provenance["packages"],
    "lock_file_sha256": provenance["lock_file_sha256"],
}
if role == "replacement":
    development = json.loads(
        (output.parent / "development-manifest.json").read_text(encoding="utf-8")
    )
    if payload["source_sha256"] != development["source_sha256"]:
        raise SystemExit("replacement source differs from passing development source")
    payload["passing_development"] = {
        "evidence_directory_sha256": development["evidence_directory_sha256"],
        "git_head_at_execution": development["git_head_at_execution"],
        "source_sha256": development["source_sha256"],
    }

manifest_path.parent.mkdir(parents=True, exist_ok=True)
descriptor, temporary_name = tempfile.mkstemp(
    dir=manifest_path.parent,
    prefix=f".{manifest_path.name}.",
    suffix=".tmp",
    text=True,
)
temporary_path = Path(temporary_name)
try:
    with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(payload, allow_nan=False, indent=2, sort_keys=True) + "\n")
    os.link(temporary_path, manifest_path)
    temporary_path.unlink()
except BaseException:
    temporary_path.unlink(missing_ok=True)
    raise

event = {
    "schema_version": "1.0",
    "event": "result",
    "role": role,
    "evidence": output.relative_to(root).as_posix(),
    "manifest": manifest_path.relative_to(root).as_posix(),
    "revision": payload["git_head_at_execution"],
    "source_sha256": payload["source_sha256"],
    "raw_sha256": payload["raw_sha256"],
    "evidence_directory_sha256": payload["evidence_directory_sha256"],
    "gate_passed": payload["gate_passed"],
    "failed_criteria": payload["failed_criteria"],
    "decision": (
        "qualifies_for_replacement"
        if role == "development" and payload["gate_passed"]
        else "replacement_passed"
        if role == "replacement" and payload["gate_passed"]
        else "stop_adverse"
    ),
}
with (root / "autoresearch-common-utility.jsonl").open("a", encoding="utf-8") as stream:
    stream.write(json.dumps(event, allow_nan=False, separators=(",", ":"), sort_keys=True) + "\n")
PY

python - "$manifest" <<'PY'
import json
from pathlib import Path
import sys

manifest = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print(f"gate_passed={manifest['gate_passed']}")
print(f"failed_criteria={manifest['failed_criteria']}")
print(f"raw_sha256={manifest['raw_sha256']}")
PY

exit 0
