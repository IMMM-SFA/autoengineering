"""Run bounded container checks over fixed authored interface fixtures.

Requires an existing pinned qualification. No model provider, data download,
scientific campaign, adapter registration or generated worker code is involved.
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import time

from autoengineering.agents.interface import (
    InterfaceCase,
    InterfaceSpec,
    check_interface,
    verify_interface,
    runner_identity,
)
from autoengineering.agents.workspaces import CandidateWorkspace
from autoengineering.campaign.records import PortContract, TimeContract
from autoengineering.campaign.serialization import canonical_json, digest
from autoengineering.campaign.store import checked_directory, durable_write


def exercise(output: Path, qualification_root: Path, qualification_digest: str):
    output = Path(output).absolute()
    checked_directory(output.parent)
    if output.exists() or output.is_symlink():
        raise ValueError("interface fixture requires a fresh output directory")
    output.mkdir(mode=0o700)
    manifest = {
        "schema_version": "1.0",
        "purpose": "authored-interface-fixtures",
        "maximum_container_starts": 10,
        "max_elapsed_seconds": 60,
        "provider_calls": 0,
        "scientific_campaigns": 0,
        "qualification_digest": qualification_digest,
        "runner_identity": runner_identity(),
        "fixture_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    durable_write(output / "manifest.json", canonical_json(manifest).encode())
    time_axis = TimeContract(
        ("2020-01-01", "2020-01-02"),
        "interval_mean",
        "P1D",
        "proleptic_gregorian",
        "end",
        (False, False),
        (True, True),
    )

    def port(name, vector=False):
        return PortContract(
            name,
            ("time",) if vector else (),
            "mm/day",
            "float",
            (),
            "scalar",
            digest([]),
            time_axis if vector else None,
        )

    def spec(vector=False, wrong=False):
        inputs = {"forcing": (1.5, 2.5) if vector else 1.5}
        expected = {"prediction": (3.0, 5.0) if vector else (8.0 if wrong else 3.0)}
        return InterfaceSpec(
            "1.0",
            (port("forcing", vector),),
            (port("prediction", vector),),
            (InterfaceCase("first", inputs, expected), InterfaceCase("second", inputs, expected)),
        )

    fixtures = (
        (
            "valid",
            b'def predict(inputs):\n return {"prediction":inputs["forcing"]*2.0}\n',
            spec(),
            "pass",
        ),
        (
            "valid-vector",
            b'def predict(inputs):\n return {"prediction":[x*2.0 for x in inputs["forcing"]]}\n',
            spec(True),
            "pass",
        ),
        (
            "mutation",
            b'def predict(inputs):\n inputs["forcing"][0]=0.0\n return {"prediction":inputs["forcing"]}\n',
            spec(True),
            "fail",
        ),
        ("cpu", b"def predict(inputs):\n while True: pass\n", spec(), "fail"),
        (
            "wrong-value",
            b'def predict(inputs):\n return {"prediction":inputs["forcing"]*2.0}\n',
            spec(wrong=True),
            "fail",
        ),
    )
    began = time.monotonic()
    checks = []
    starts = 0
    for name, source, contract, wanted in fixtures:
        if time.monotonic() - began > 60:
            raise ValueError("interface fixture elapsed allowance exhausted")
        if starts + len(contract.cases) > manifest["maximum_container_starts"]:
            raise ValueError("interface fixture start allowance exhausted")
        print(f"Checking {name}", flush=True)
        work = CandidateWorkspace.create(
            output / name, run_id="fixture", task_id=name, baseline={"adapter.py": source}
        )
        capture = work.capture()
        receipt = check_interface(
            work,
            capture,
            contract,
            qualification_root=qualification_root,
            qualification_digest=qualification_digest,
            output=output / f"{name}-checks",
        )
        verify_interface(
            output / f"{name}-checks",
            work,
            capture,
            contract,
            qualification_root=qualification_root,
            qualification_digest=qualification_digest,
            expected_receipt_digest=receipt.digest,
        )
        starts += sum(c.execution_digest is not None for c in receipt.checks)
        checks.append(
            {
                "name": name,
                "status": "pass" if receipt.status == wanted else "fail",
                "observed_status": receipt.status,
                "receipt_digest": receipt.digest,
            }
        )
        if receipt.status != wanted:
            break
    elapsed = time.monotonic() - began
    result = {
        **manifest,
        "status": "pass"
        if len(checks) == 5
        and all(c["status"] == "pass" for c in checks)
        and starts == 7
        and elapsed <= 60
        else "fail",
        "container_starts": starts,
        "checks": checks,
        "elapsed_seconds": elapsed,
    }
    durable_write(output / "result.json", canonical_json(result).encode())
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--qualification-root", type=Path, required=True)
    parser.add_argument("--qualification-digest", required=True)
    args = parser.parse_args()
    result = exercise(args.output, args.qualification_root, args.qualification_digest)
    print(canonical_json(result))
    return 0 if result["status"] == "pass" else 4


if __name__ == "__main__":
    raise SystemExit(main())
