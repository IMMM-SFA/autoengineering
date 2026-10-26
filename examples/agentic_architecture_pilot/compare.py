"""Compare deterministic CLI transport with direct standalone scheduling."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import subprocess
import sys
import time

from .control import CANDIDATE, request, scripted_messages
from .science import identity, write_json


def drive(directory: Path, route: str) -> dict:
    started = time.monotonic()
    transcript = []

    def call(message):
        if route == "cli":
            process = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "examples.agentic_architecture_pilot.control",
                    str(directory),
                ],
                input=json.dumps(message),
                text=True,
                capture_output=True,
                timeout=1800,
            )
            if process.returncode:
                raise RuntimeError(process.stdout + process.stderr)
            response = json.loads(process.stdout)
        else:
            response = request(directory, message)
        transcript.append(dict(request=message, response=response))
        return response

    for message in scripted_messages():
        result = call(message)
    for step in ("review", "decide"):
        call(dict(id=step, tool=step, payload=dict(decision=result["decision"])))
    write_json(directory / "transcript.json", transcript)
    return dict(
        route=route,
        worker="deterministic_stub",
        seconds=time.monotonic() - started,
        decision=result["decision"],
        executions=result["total_executions"],
        tool_calls=len(transcript),
        tokens=0,
        usd=0,
        candidate=CANDIDATE,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    write_json(args.output / "source-hashes.json", identity())
    runs = []
    reference = None
    for route in ("cli", "standalone"):
        for repeat in range(3):
            directory = args.output / f"{route}-{repeat}"
            print(f"Running {route} deterministic replay {repeat + 1}/3", flush=True)
            row = drive(directory, route)
            result = json.loads((directory / "evaluation.json").read_text())["response"]
            if reference is None:
                reference = result
            if result != reference:
                raise RuntimeError("transport parity failed")
            row["repeat"] = repeat
            row["artifact"] = str(directory.relative_to(args.output) / "evaluation.json")
            runs.append(row)
    with (args.output / "runs.csv").open("w") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(runs[0]))
        writer.writeheader()
        writer.writerows(runs)
    write_json(
        args.output / "parity.json",
        dict(equal=True, runs=6, scientific_executions=sum(r["executions"] for r in runs)),
    )


if __name__ == "__main__":
    main()
