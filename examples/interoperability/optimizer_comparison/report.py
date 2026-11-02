"""Rebuild a comparison report from retained bytes without optimizer imports."""
from __future__ import annotations

import argparse
from pathlib import Path

from autoengineering.campaign.serialization import digest, unique_json
from autoengineering.integrations.contracts import IntegrationSpec
from autoengineering.integrations.replay import ReplayJournal


def load(path):
    return unique_json(path.read_text())


def reconstruct(root):
    protocol = load(root / "protocol.json")
    rows = []
    total = 0
    for policy in protocol["policies"]:
        for case in protocol["cases"]:
            for seed in protocol["seeds"]:
                path = root / f"{policy}-{case}-{seed}"
                supervision = load(path / "supervision.json")
                if not (path / "summary.json").exists():
                    # A process failure does not erase the physical work whose
                    # result bytes reached durable storage before it failed.
                    records = [load(p) for p in sorted(path.glob("result-*.json"))]
                    total += len(records)
                    rows.append((path.name, f"failed_without_summary:{len(records)}_starts",
                                 None, supervision))
                    continue
                summary = load(path / "summary.json")
                manifest = load(path / "manifest.json")
                identity = IntegrationSpec.from_dict(manifest["identity"])
                if identity.configuration_digest != digest(manifest["configuration"]):
                    raise ValueError("configuration identity differs")
                journal = ReplayJournal(path / "journal", identity)
                transitions = journal.read()
                observations = {r.action_id: r.observation for r in transitions
                                if r.phase == "synchronized"}
                history = summary["history"]
                if len(history) != summary["physical_starts"] or len(history) > 12:
                    raise ValueError("physical-start count differs")
                if len(observations) != len(history):
                    raise ValueError("committed results and synchronization count differ")
                for index, item in enumerate(history):
                    raw = load(path / f"result-{index:06d}.json")
                    observation = observations[item["action_id"]]
                    if digest(raw) != observation.result_digest:
                        raise ValueError("committed result digest differs")
                    if any(raw[key] != item[key] for key in raw):
                        raise ValueError("summary result differs from committed result")
                    result = raw["result"]
                    if (result["status"], result["feasible"], result["objective"]) != (
                        observation.status, observation.feasible, observation.objective
                    ):
                        raise ValueError("external projection differs from committed result")
                total += len(history)
                feasible = [h["result"]["objective"] for h in history
                            if h["result"]["status"] == "success" and h["result"]["feasible"]]
                rows.append((path.name, summary["stop"], min(feasible, default=None), supervision))
    if total > protocol["total_physical_start_ceiling"]:
        raise ValueError("comparison exceeded physical start ceiling")
    lines = ["# Analytic optimizer comparison", "",
             f"Committed physical starts: {total}. These are development tasks, not prediction evidence.",
             "", "| Cell | Stop | Best feasible objective | Process seconds |",
             "| --- | --- | --- | --- |"]
    for cell, stop, best, supervision in rows:
        lines.append(f"| {cell} | {stop} | {best} | {supervision['elapsed_seconds']:.3f} |")
    lines += ["", "Selection requires separate API, license, recovery, resource and burden gates.",
              "A duplicate proposal stops dispatch without an invented failed evaluation.", ""]
    return "\n".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.write_text(reconstruct(args.root))
