"""Recalculate larger-example evidence with vector oracles where available."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from pvlib.inverter import pvwatts
from pvlib.pvsystem import calcparams_desoto, singlediode

from examples.complex_models.models import BASE_DOMAIN, MODULE, evaluate, load_data, score
from examples.local_models import kernels
from examples.local_models.run import write_json


def oracle(domain: str, data, config: dict) -> dict:
    if domain in kernels.DOMAINS:
        return getattr(kernels, f"{domain}_model")(data, config)
    if domain == "hymod":
        out = evaluate(domain, data, config)
        if np.max(np.abs(out["balance_residual"])) > 1e-9:
            raise ValueError("HYMOD water balance failed")
        return out
    irradiance = data.poa_w_m2.to_numpy() * config["irradiance_scale"]
    temperature = data.air_c.to_numpy() + irradiance / config["heat_loss"]
    params = calcparams_desoto(
        irradiance,
        temperature,
        alpha_sc=MODULE["alpha_sc"],
        a_ref=MODULE["a_ref"] * config["a_scale"],
        I_L_ref=MODULE["I_L_ref"],
        I_o_ref=MODULE["I_o_ref"] * config["io_scale"],
        R_s=MODULE["R_s"] * config["rs_scale"],
        R_sh_ref=MODULE["R_sh_ref"] * config["rsh_scale"],
        EgRef=1.121,
        dEgdT=-0.0002677,
    )
    dc = singlediode(*params, method="lambertw")["p_mp"] * (2369 / MODULE["STC"]) * config["loss"]
    return {
        "prediction": pvwatts(dc, pdc0=1910 / 0.96, eta_inv_nom=0.96),
        "temperature": temperature,
    }


def audit(directory: Path) -> dict:
    rows = json.loads((directory / "results.json").read_text())["runs"]
    count = 0
    recommendations = 0
    failures = []
    ledger_hashes = {}
    for row in rows:
        name = f"{row['domain']}-{row['method']}-{row['seed']}"
        ledger = directory / name / "observations.jsonl"
        ledger_hashes[name] = hashlib.sha256(ledger.read_bytes()).hexdigest()
        entries = [json.loads(s) for s in ledger.read_text().splitlines()]
        data = load_data(row["domain"])
        dev = data.loc[data.split != "test"]
        for entry in entries:
            action, result = entry["action"], entry["result"]
            count += 1
            if result["status"] != "success":
                failures.append({"study": name, "action": action["id"], "status": result["status"]})
                continue
            prediction = oracle(row["domain"], dev, action["config"])["prediction"]
            mask = dev.split == "validation"
            observed = dev.loc[mask, kernels.TARGETS[BASE_DOMAIN[row["domain"]]]].to_numpy()
            value = float(np.sqrt(np.mean((prediction[mask] - observed) ** 2)))
            np.testing.assert_allclose(value, result["outcomes"]["rmse"], rtol=1e-8, atol=1e-8)
            assert result["cost"] == 1.0 and result["cost_unit"] == "model_call"
        snapshots = row["checkpoints"] + [
            {
                "evaluations": row["evaluations"],
                "recommendation": row["recommendation"],
                "test": row["test"],
            }
        ]
        for snapshot in snapshots:
            rec = snapshot["recommendation"]
            eligible = entries[: snapshot["evaluations"]]
            if rec["action_id"] is None:
                assert snapshot["test"] is None
                assert not any(e["result"]["status"] == "success" for e in eligible)
                continue
            selected = [e for e in eligible if e["action"]["id"] == rec["action_id"]]
            assert len(selected) == 1 and selected[0]["action"]["config"] == rec["config"]
            assert selected[0]["result"]["status"] == "success"
            assert selected[0]["result"]["outcomes"] == rec["outcomes"]
            successful = [
                e["result"]["outcomes"]["rmse"]
                for e in eligible
                if e["result"]["status"] == "success"
            ]
            assert rec["outcomes"]["rmse"] == min(successful)
            metrics = score(row["domain"], data, oracle(row["domain"], data, rec["config"]), "test")
            for key, value in metrics.items():
                np.testing.assert_allclose(value, snapshot["test"][key], rtol=1e-8, atol=1e-8)
            recommendations += 1
        print(f"Audited {name}: {len(entries)} attempts", flush=True)
    return {
        "results_sha256": hashlib.sha256((directory / "results.json").read_bytes()).hexdigest(),
        "attempts": count,
        "recommendations_recalculated": recommendations,
        "failures": failures,
        "ledger_sha256": ledger_hashes,
        "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "oracle": "Original models use vector kernels. Solar diode uses independent vector Lambert-W solver. HYMOD reruns BMI and checks mass balance.",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Audit output already exists")
    write_json(args.output, audit(args.directory))
