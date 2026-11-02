"""Serial resource-bounded analytic prototype comparison, always a fresh root."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

from autoengineering.campaign.store import durable_write

HERE = Path(__file__).resolve().parent


def run(output):
    protocol = json.loads((HERE / "protocol.json").read_text())
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    durable_write(output / "protocol.json", (HERE / "protocol.json").read_bytes())
    sources = {str(p.relative_to(HERE)): hashlib.sha256(p.read_bytes()).hexdigest()
               for p in HERE.glob("*.py")}
    durable_write(output / "sources.json", json.dumps(sources, sort_keys=True).encode())
    started = time.monotonic()
    rows = []
    for framework in protocol["policies"]:
        for case in protocol["cases"]:
            for seed in protocol["seeds"]:
                if time.monotonic() - started >= protocol["wall_seconds_total"]:
                    raise RuntimeError("comparison total deadline exhausted")
                name = f"{framework}-{case}-{seed}"
                root = output / name
                current_sources = {str(p.relative_to(HERE)): hashlib.sha256(p.read_bytes()).hexdigest()
                                   for p in HERE.glob("*.py")}
                if current_sources != sources:
                    raise RuntimeError("comparison sources changed during execution")
                root.mkdir(mode=0o700)
                environment = dict(os.environ, OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1",
                                   MKL_NUM_THREADS="1")
                before = time.monotonic()
                reason = None
                peak = 0
                with (root / "process.log").open("xb") as log:
                    process = subprocess.Popen(
                        [sys.executable, "-m",
                         "examples.interoperability.optimizer_comparison.worker",
                         str(root), framework, case, str(seed)],
                        env=environment, stdout=log, stderr=log, start_new_session=True,
                    )
                    try:
                        while process.poll() is None:
                            # Track the owned process group, including any child work.
                            snapshot = subprocess.check_output(
                                ["ps", "-axo", "pgid=,rss="], text=True,
                            )
                            rss = sum(int(parts[1]) * 1024 for line in snapshot.splitlines()
                                      if len(parts := line.split()) == 2
                                      and int(parts[0]) == process.pid)
                            peak = max(peak, rss)
                            if rss > protocol["memory_bytes_per_process"]:
                                reason = "memory_ceiling"
                            if time.monotonic() - before > protocol["wall_seconds_per_case_seed_policy"]:
                                reason = "cell_deadline"
                            if time.monotonic() - started > protocol["wall_seconds_total"]:
                                reason = "total_deadline"
                            if reason:
                                break
                            time.sleep(.1)
                    finally:
                        if process.poll() is None:
                            os.killpg(process.pid, signal.SIGKILL)
                        process.wait()
                row = {"cell": name, "exit_code": process.returncode, "stop": reason,
                       "elapsed_seconds": time.monotonic() - before,
                       "peak_sampled_group_rss_bytes": peak}
                rows.append(row)
                durable_write(root / "supervision.json", json.dumps(row).encode())
                print(json.dumps(row), flush=True)
    durable_write(output / "execution.json", json.dumps(rows, indent=2).encode())


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    run(parser.parse_args().output)
