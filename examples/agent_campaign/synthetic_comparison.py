"""Prepare a PET comparison using fabricated weather and labels, not measured data."""

from __future__ import annotations

import argparse
from dataclasses import replace
from datetime import date
from pathlib import Path

import numpy as np

from autoengineering.agents.batch import BatchSpec
from autoengineering.agents.hosts.fake import FakeHost
from autoengineering.agents.identity import host_environment_identity, host_source_identity
from autoengineering.agents.permissions import POLICY_DIGEST
from autoengineering.agents.records import AgentRunSpec, HostSelection, ResourceLimits
from autoengineering.agents.scheduler import template_digests
from autoengineering.agents.single_agent import single_agent_spec
from autoengineering.campaign.artifacts import confined_file, read_arrays, read_bytes, reference
from autoengineering.campaign.identity import scientific_identity
from autoengineering.campaign.serialization import canonical_json, digest
from autoengineering.campaign.spec import CampaignSpec
from autoengineering.campaign.store import checked_directory, durable_write
from autoengineering.optimization import NpzReadLimits

from . import comparison as comp
from . import prepare_leafriver as leaf

SCOPE = "Synthetic PET workflow analogue with fabricated inputs and labels; no measured Leaf River execution"
GRID = "synthetic-pet-basin"
BATCH_LIMITS = ResourceLimits(40, 32, 8, 2, 1800, 30, 2097152, 131072)


def arrays():
    day = np.arange(1, 366)
    mean = 20 + 5 * np.sin(day / 29)
    target = 5 + np.sin(day / 7)
    return {
        "forcing": {
            "precip_mm": 10 + 2 * np.sin(day / 13),
            "tmean_c": mean,
            "tmax_c": mean + 8,
            "tmin_c": mean - 8,
            "day_of_year": day,
        },
        "fitting": {"prediction": target[90:273]},
        "comparison": {"prediction": target[273:]},
    }


def _spec(template, route, source):
    def port(p):
        return replace(
            p,
            grid_id=GRID,
            coordinate_digest=digest(GRID),
            time=None
            if p.time is None
            else replace(
                p.time,
                dates=tuple(
                    date.fromisoformat(s).replace(year=2001).isoformat() for s in p.time.dates
                ),
            ),
        )

    inputs = tuple(port(p) for p in template.baseline.model.inputs)
    outputs = tuple(port(p) for p in template.baseline.model.outputs)

    def ref(name, media="application/octet-stream"):
        return reference(source, name, media_type=media, producer="synthetic-comparison-author")

    system = ref("inputs/system.yaml", "application/yaml")
    # Reuse only the verified scientific source set, not any measured data source.
    source_paths = sorted({*leaf.SOURCES, *leaf.scientific_source_paths()})
    sources = tuple(ref(name) for name in source_paths)
    environment_lock = reference(
        source,
        template.provenance.environment_lock.path,
        media_type=template.provenance.environment_lock.media_type,
        producer=template.provenance.environment_lock.producer,
    )
    model = replace(
        template.baseline.model,
        graph_digest=system.sha256,
        source_bundle=sources,
        dependency_bundle=environment_lock.sha256,
        inputs=inputs,
        outputs=outputs,
    )
    data = tuple(
        replace(
            d,
            artifact=ref(f"inputs/{d.id}.npz", "application/x-npz"),
            ports=tuple(port(p) for p in d.ports),
            prior_exposure="exposed",
        )
        for d in template.data
    )
    run = replace(
        template.calibration.run,
        study=replace(template.calibration.run.study, name="synthetic-pet-fitting"),
    )
    return replace(
        template,
        name=f"synthetic-matched-{route.replace('_', '-')}-v1",
        scientific_scope=SCOPE,
        source_bundle="scientific-core-v1",
        baseline=replace(template.baseline, system=system, model=model),
        data=data,
        calibration=replace(template.calibration, run=run),
        execution=replace(template.execution, max_executions=38),
        provenance=replace(
            template.provenance,
            sources=sources,
            expected_outputs=outputs,
            environment_lock=environment_lock,
        ),
    )


def verify(root, plan, specs):
    template = leaf._template(confined_file(root, plan.template.path))
    source = root / "captured_source"
    limits = NpzReadLimits(**comp.PROTOCOL["synthetic_npz_limits"])
    data = {d.id: d for d in specs[0].data}
    if set(data) != set(arrays()):
        raise ValueError("synthetic data roles differ")
    for role, expected in arrays().items():
        artifact = data[role].artifact
        if artifact.path != f"inputs/{role}.npz":
            raise ValueError("synthetic data path differs")
        stored = read_arrays(source, artifact, limits=limits)
        if set(stored) != set(expected):
            raise ValueError("synthetic array names differ")
        for name, values in expected.items():
            if stored[name].dtype.kind not in "fiu":
                raise ValueError("synthetic arrays must have real numeric types")
            np.testing.assert_array_equal(stored[name], values)
    # Architecture comes from the original graph but contains no measured data.
    system = read_bytes(source, specs[0].baseline.system)
    original_system = read_bytes(root, plan.original_system)
    if plan.original_system.sha256 != template.baseline.system.sha256:
        raise ValueError("synthetic original graph binding differs")
    if system != b"name: synthetic-pet-comparison\n" + original_system.split(b"\n", 1)[1]:
        raise ValueError("synthetic graph differs")
    for case, spec in zip(plan.cases, specs):
        if spec != _spec(template, case.id, source):
            raise ValueError("synthetic comparison changed data, science or limits")
        leaf.allocation(spec)
        if case.worker.permitted_interventions != ("hamon-v1", "hargreaves-v1"):
            raise ValueError("synthetic worker changes the candidate pool")
    expected_paths = {f"captured_source/{r.path}" for r in leaf._refs(specs[0])}
    if {r.path for r in plan.inputs} != expected_paths or plan.batch.limits != BATCH_LIMITS:
        raise ValueError("synthetic comparison input closure or batch limits differ")


def prepare(leaf_root: Path, *, leaf_digest: str, output: Path, runtime_root: Path):
    parent = leaf.load(leaf_root, expected_digest=leaf_digest)
    output = Path(output).absolute()
    runtime_root = Path(runtime_root).absolute()
    checked_directory(output.parent)
    checked_directory(runtime_root.parent)
    if (
        output.exists()
        or output.is_symlink()
        or runtime_root.exists()
        or runtime_root.is_symlink()
        or output.resolve().is_relative_to(runtime_root.resolve())
        or runtime_root.resolve().is_relative_to(output.resolve())
    ):
        raise ValueError("synthetic preparation and runtime must be absent and separate")
    leaf_root = checked_directory(leaf_root)
    template = leaf._template(confined_file(leaf_root, parent.template.path))
    original = CampaignSpec.from_yaml(confined_file(leaf_root, parent.routes[0].specification.path))
    captured = {
        ref.path: read_bytes(leaf_root / "captured_source", ref)
        for ref in original.provenance.sources
    }
    lock = original.provenance.environment_lock
    captured[lock.path] = read_bytes(leaf_root / "captured_source", lock)
    system = read_bytes(leaf_root / "captured_source", original.baseline.system)
    output.mkdir(mode=0o700)
    source = output / "captured_source"
    for name, raw in captured.items():
        path = source / name
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        durable_write(path, raw)
    (source / "inputs").mkdir(mode=0o700)
    durable_write(
        source / "inputs/system.yaml",
        b"name: synthetic-pet-comparison\n" + system.split(b"\n", 1)[1],
    )
    for role, values in arrays().items():
        np.savez(source / f"inputs/{role}.npz", **values)
    durable_write(
        output / "original-template.yaml", read_bytes(leaf_root, parent.template, max_bytes=1048576)
    )
    durable_write(output / "original-system.yaml", system)
    durable_write(
        output / "parent-leaf-preparation.json", (leaf_root / "leaf-preparation.json").read_bytes()
    )
    (output / "driver").mkdir(mode=0o700)
    drivers = []
    for name in comp.DRIVER_FILES:
        durable_write(output / "driver" / name, Path(__file__).with_name(name).read_bytes())
        drivers.append(
            reference(
                output,
                f"driver/{name}",
                media_type="text/x-python",
                producer="comparison-preparation",
            )
        )
    (output / "scientific").mkdir(mode=0o700)
    cases = []
    for route in leaf.ROUTES:
        spec = _spec(template, route, source)
        spec.to_yaml(output / f"scientific/{route}.yaml")
        worker = AgentRunSpec(
            "1.0",
            f"synthetic-worker-{route.replace('_', '-')}",
            spec.name,
            scientific_identity(spec, source),
            HostSelection("fake", "none", "authored-synthetic", "1.0"),
            template_digests(),
            ("hamon-v1", "hargreaves-v1"),
            POLICY_DIGEST,
            leaf.LIVE_LIMITS,
            host_source_identity(),
            host_environment_identity(),
            "supplied",
        )
        if route == "single_agent":
            worker = single_agent_spec(worker, run_id=worker.id)
        cases.append(
            comp.ComparisonCase(
                route,
                reference(
                    output,
                    f"scientific/{route}.yaml",
                    media_type="application/yaml",
                    producer="comparison-preparation",
                ),
                worker,
            )
        )
    inputs = tuple(
        reference(
            output,
            f"captured_source/{r.path}",
            media_type=r.media_type,
            producer="comparison-preparation",
        )
        for r in leaf._refs(spec)
    )
    batch = BatchSpec(
        "1.0",
        "synthetic-matched-pet-v1",
        host_source_identity(),
        host_environment_identity(),
        worker.host,
        FakeHost(()).capabilities(),
        digest({"mode": "authored_synthetic_no_credentials"}),
        BATCH_LIMITS,
        114,
        comp.batch_cases(cases),
    )
    plan = comp.ComparisonPreparation(
        comp.VERSION,
        comp.PROTOCOL_DIGEST,
        str(runtime_root),
        reference(
            output,
            "parent-leaf-preparation.json",
            media_type="application/json",
            producer="comparison-preparation",
        ),
        reference(
            output,
            "original-template.yaml",
            media_type="application/yaml",
            producer="comparison-preparation",
        ),
        reference(
            output,
            "original-system.yaml",
            media_type="application/yaml",
            producer="comparison-preparation",
        ),
        tuple(drivers),
        tuple(cases),
        inputs,
        batch,
    )
    verify(output, plan, [_spec(template, route, source) for route in leaf.ROUTES])
    durable_write(output / "comparison.json", plan.to_json().encode())
    return plan


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--leaf-preparation", type=Path, required=True)
    parser.add_argument("--leaf-digest", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--runtime-root", type=Path, required=True)
    args = parser.parse_args()
    plan = prepare(
        args.leaf_preparation,
        leaf_digest=args.leaf_digest,
        output=args.output,
        runtime_root=args.runtime_root,
    )
    print(
        canonical_json(
            {
                "preparation_digest": plan.digest,
                "runtime_created": False,
                "scientific_starts": 0,
                "kind": "authored_synthetic_dry_run",
            }
        )
    )


if __name__ == "__main__":
    main()
