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

if test -n "$(git status --porcelain --untracked-files=all)"; then
  echo "candidate-generation benchmark requires a clean signed revision" >&2
  exit 2
fi
git verify-commit HEAD >/dev/null

evidence_root="benchmarks/partial_network/candidate-generation"
output="$evidence_root/$role"
manifest="$evidence_root/$role-manifest.json"
if test -e "$output" || test -L "$output" || test -e "$manifest" || test -L "$manifest"; then
  echo "candidate-generation $role evidence already exists" >&2
  exit 2
fi

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
  python - "$development_manifest" "$development_gate" <<'PY'
import json
from pathlib import Path
import sys

manifest = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
gate = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
if manifest["role"] != "development" or not gate["passed"]:
    raise SystemExit("replacement requires a passing development matrix")
PY
fi

echo "candidate-generation role: $role"
echo "output: $output"

set +e
python -m autoengineering.benchmarks.partial_network --output "$output"
benchmark_status=$?
set -e
if test "$benchmark_status" -gt 1; then
  echo "benchmark execution failed with status $benchmark_status" >&2
  exit "$benchmark_status"
fi

python - "$role" "$output" "$manifest" <<'PY'
from __future__ import annotations

import hashlib
from importlib import metadata
import json
from pathlib import Path
import platform
import subprocess
import sys

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


def git_output(repository: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", *arguments],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


role = sys.argv[1]
output = Path(sys.argv[2])
manifest_path = Path(sys.argv[3])
root = repository_root()
gate = json.loads((output / "gate.json").read_text(encoding="utf-8"))
versions = {}
for package in ("autoengineering", "numpy", "scipy", "torch", "botorch", "gpytorch"):
    try:
        versions[package] = metadata.version(package)
    except metadata.PackageNotFoundError:
        versions[package] = "not_installed"

payload = {
    "schema_version": "1.0",
    "role": role,
    "decision_0007_sha256": sha256(root / "docs/decisions/0007-partial-network-benchmark.md"),
    "decision_0008_sha256": sha256(
        root / "docs/decisions/0008-partial-network-candidate-generation.md"
    ),
    "git_head_at_execution": git_output(root, "rev-parse", "HEAD"),
    "git_commit_signed": True,
    "git_tree_clean_at_start": True,
    "command": f"pixi run -e bayes bash autoresearch-candidate-generation.sh {role}",
    "source_sha256": source_hash(root),
    "source_file_sha256": source_file_hashes(root),
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
    "python": platform.python_version(),
    "platform": platform.platform(),
    "packages": versions,
    "lock_file_sha256": {
        name: sha256(root / name) for name in ("pixi.lock", "pixi.toml", "pyproject.toml")
    },
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

manifest_path.write_text(
    json.dumps(payload, allow_nan=False, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
    newline="\n",
)

event = {
    "schema_version": "1.0",
    "event": "result",
    "role": role,
    "evidence": output.as_posix(),
    "manifest": manifest_path.as_posix(),
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
with (root / "autoresearch-candidate-generation.jsonl").open("a", encoding="utf-8") as stream:
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
