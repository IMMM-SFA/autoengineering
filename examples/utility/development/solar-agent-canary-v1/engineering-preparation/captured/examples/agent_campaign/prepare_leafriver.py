"""Capture fresh matched Leaf River inputs without models, hosts or execution clocks.

The checked Part 2 profile is an immutable scientific template. Its broad source
closure is replaced only in new profiles. Preparation is not execution authority.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, replace
import hashlib
from pathlib import Path
from typing import Literal

import numpy as np

from autoengineering.agents.records import AgentRecord, ResourceLimits
from autoengineering.campaign.artifacts import confined_file, read_bytes, reference
from autoengineering.campaign.identity import (
    scientific_identity,
    scientific_source_paths,
    verify_runtime_sources,
)
from autoengineering.campaign.records import ArtifactRef, sha256, unique
from autoengineering.campaign.serialization import canonical_json, digest, unique_json
from autoengineering.campaign.spec import CampaignSpec
from autoengineering.campaign.store import checked_directory, durable_write
from examples.campaign_contracts.build_profile import ROOT, audit_cache
from examples.campaign_contracts.hydrology import SOURCES

VERSION = "matched-leaf-preparation-1.0"
TEMPLATE = "examples/campaign_contracts/profile/campaign.yaml"
TEMPLATE_SHA256 = "f2c35df440ea5b622e1da2d568c4db78d806ca5c120cca5a28267401555f0766"
ROUTES = ("scripted", "single_agent", "four_role")
LIVE_LIMITS = ResourceLimits(20, 16, 4, 2, 600, 30, 1048576, 65536)
ACCOUNTING = {"defaults": 2, "fitting": 32, "selected_comparison": 2, "causality": 2}
PROTOCOL = {
    "version": VERSION,
    "template_sha256": TEMPLATE_SHA256,
    "routes": list(ROUTES),
    "candidate_order": ["pet-hamon-v1", "pet-hargreaves-v1"],
    "seed": 17,
    "live_route_limits": LIVE_LIMITS.to_dict(),
    "aggregate_live_host_invocations": 40,
    "route_scientific_starts": 38,
    "aggregate_scientific_starts": 114,
    "planned_executions": ACCOUNTING,
    "confirmation": "confirmation_not_attempted",
    "exposure": "All 2019 and 2020 observations were exposed historically",
}
PROTOCOL_DIGEST = digest(PROTOCOL)
AUDIT_INPUTS = (
    "examples/campaign_contracts/build_profile.py",
    "examples/local_models/data/hydro.csv",
    "examples/local_models/data/sources.json",
    "examples/local_models/data/preparation.json",
    "examples/leaf_river/data/weather.csv",
    "examples/leaf_river/data/streamflow.csv",
    "examples/leaf_river/data/fetch_data.py",
)
SPLIT_COUNTS = {"test": 366, "train": 183, "validation": 92, "warmup": 90}


@dataclass(frozen=True)
class LeafRoute(AgentRecord):
    route: Literal["scripted", "single_agent", "four_role"]
    specification: ArtifactRef
    scientific_identity: str

    def _validate(self):
        sha256(self.scientific_identity)
        if self.specification.path != f"campaigns/{self.route}.yaml":
            raise ValueError("matched route specification path differs")


@dataclass(frozen=True)
class LeafPreparation(AgentRecord):
    schema_version: Literal["matched-leaf-preparation-1.0"]
    protocol_digest: str
    template: ArtifactRef
    recipe: ArtifactRef
    routes: tuple[LeafRoute, ...]
    inputs: tuple[ArtifactRef, ...]
    audit: ArtifactRef

    def _validate(self):
        if (
            self.protocol_digest != PROTOCOL_DIGEST
            or self.template.sha256 != TEMPLATE_SHA256
            or self.template.path != "original-template.yaml"
            or self.recipe.path != "preparation-recipe.py"
            or self.audit.path != "audit.json"
            or tuple(row.route for row in self.routes) != ROUTES
            or not 1 <= len(self.inputs) <= 256
            or sum(ref.size_bytes for ref in self.inputs) > 67108864
        ):
            raise ValueError("matched Leaf preparation differs from fixed protocol")
        unique([ref.path for ref in self.inputs], "matched input path")
        if any(not ref.path.startswith("captured_source/") for ref in self.inputs):
            raise ValueError("matched input lies outside captured source")
        unique([row.scientific_identity for row in self.routes], "matched scientific identity")


def _template(path: Path) -> CampaignSpec:
    with path.open("rb") as stream:
        raw = stream.read(1048577)
    if hashlib.sha256(raw).hexdigest() != TEMPLATE_SHA256:
        raise ValueError("checked Leaf River scientific template changed")
    return CampaignSpec.from_yaml(path)


def _derive(template, route, sources, environment_lock):
    return replace(
        template,
        name=f"matched-leaf-{route.replace('_', '-')}-v1",
        source_bundle="scientific-core-v1",
        baseline=replace(
            template.baseline,
            model=replace(
                template.baseline.model,
                source_bundle=sources,
                dependency_bundle=environment_lock.sha256,
            ),
        ),
        execution=replace(template.execution, max_executions=38),
        provenance=replace(template.provenance, sources=sources, environment_lock=environment_lock),
    )


def _refs(spec):
    return (
        spec.baseline.system,
        spec.provenance.environment_lock,
        *spec.provenance.sources,
        *(item.artifact for item in spec.data),
    )


def allocation(spec: CampaignSpec) -> dict:
    """Bound the fixed complete-pool path, without claiming physical starts.

    Match studies.run_child: an unchanged Hamon baseline reuses its default,
    each child reserves fitting plus a fresh comparison and any absent default.
    The controller performs one causal replay for each selected comparison.
    """
    if spec.calibration is None:
        raise ValueError("Leaf accounting requires fitting")
    run = spec.calibration.run
    pool = spec.interventions[0].implementation_ids
    if (
        pool != ("hamon-v1", "hargreaves-v1")
        or spec.baseline.model.implementations["pet"] != "hamon-v1"
        or spec.baseline.parameters != {"pet": "hamon", "capacity": 100.0, "recession": 0.7}
        or run.policy != "sobol"
        or run.study.seed != 17
        or spec.seed != 17
        or run.study.budget.max_evaluations != 16
        or run.target_value is not None
        or spec.workflow.max_candidates != 2
        or spec.execution.diagnostics != "causal_future_forcing_v1"
        or spec.confirmation.mode != "disabled"
    ):
        raise ValueError("Leaf accounting requires the frozen complete-pool protocol")
    children = []
    for implementation in pool:
        absent_default = implementation != spec.baseline.model.implementations["pet"]
        children.append(
            {
                "candidate": f"pet-{implementation}",
                "additional_default": int(absent_default),
                "fitting": run.study.budget.max_evaluations,
                "selected_comparison": 1,
                "child_reservation": run.study.budget.max_evaluations + 1 + int(absent_default),
                "causality": 1,
            }
        )
    total = 1 + sum(row["child_reservation"] + row["causality"] for row in children)
    if total != spec.execution.max_executions or total != 38:
        raise ValueError("Leaf accounting differs from execution ceiling")
    return {"baseline_default": 1, "children": children, "total": total}


def _check_data(template, table):
    """Compare cached inputs with their historical splits, without model arithmetic."""
    development = table[table.date < "2020-01-01"]
    expected = {
        "forcing": {
            **{
                name: development[name].to_numpy()
                for name in ("precip_mm", "tmean_c", "tmax_c", "tmin_c")
            },
            "day_of_year": np.arange(1, 366),
        },
        "fitting": {
            "prediction": development.loc[development.split == "train", "flow_mm_day"].to_numpy()
        },
        "comparison": {
            "prediction": development.loc[
                development.split == "validation", "flow_mm_day"
            ].to_numpy()
        },
    }
    for data in template.data:
        read_bytes(ROOT, data.artifact)
        with np.load(confined_file(ROOT, data.artifact.path), allow_pickle=False) as arrays:
            if set(arrays.files) != set(expected[data.id]):
                raise ValueError("checked Leaf input array names differ")
            for name, values in expected[data.id].items():
                np.testing.assert_array_equal(arrays[name], values)


def _audit(spec):
    return {
        **PROTOCOL,
        "historical_split_counts": SPLIT_COUNTS,
        "development_split_counts": {"warmup": 90, "fitting": 183, "comparison": 92},
        "period": ["2019-01-01", "2019-12-31"],
        "metadata_limit": "Original HTTP responses and quality flags are absent from the legacy cache",
        "planned_executions_kind": "ceiling for the complete pool when both fitting studies select feasible configurations; failures or stops may use less",
        "execution_allocation": allocation(spec),
        "scientific_starts": 0,
        "provider_calls": 0,
        "runtime_created": False,
        "clock_started": False,
        "execution_ready": False,
        "missing_execution_handlers": ["matched comparison driver"],
    }


def _historical_audit_inputs(template, source):
    """Bind the cache audit to historical template and original cache-source hashes."""
    historical = {ref.path: ref for ref in template.provenance.sources}
    provenance_path = "examples/local_models/data/sources.json"
    provenance = unique_json(read_bytes(source, historical[provenance_path]).decode())
    cache_sources = provenance["hydro"]["source_files"]
    for name in AUDIT_INPUTS:
        if name in historical:
            read_bytes(source, historical[name], max_bytes=4194304)
        else:
            path = confined_file(source, name)
            if path.stat().st_size > 4194304:
                raise ValueError("historical cache audit input exceeds allowance")
            if hashlib.sha256(path.read_bytes()).hexdigest() != cache_sources.get(name):
                raise ValueError("historical cache audit source changed")


def prepare(output: Path) -> LeafPreparation:
    """Create three new immutable campaign files, without initializing runtimes."""
    output = Path(output).absolute()
    checked_directory(output.parent)
    if output.exists() or output.is_symlink():
        raise ValueError("matched Leaf preparation requires an absent output directory")
    template = _template(confined_file(ROOT, TEMPLATE))
    audited_bytes = {name: confined_file(ROOT, name).read_bytes() for name in AUDIT_INPUTS}
    table = audit_cache()
    if table.split.value_counts().to_dict() != SPLIT_COUNTS:
        raise ValueError("historical cache split counts changed")
    _check_data(template, table)
    sources = tuple(
        reference(
            ROOT, name, media_type="application/octet-stream", producer="matched-profile-author"
        )
        for name in sorted({*SOURCES, *scientific_source_paths()})
    )
    environment_lock = reference(
        ROOT,
        template.provenance.environment_lock.path,
        media_type=template.provenance.environment_lock.media_type,
        producer=template.provenance.environment_lock.producer,
    )
    specs = {route: _derive(template, route, sources, environment_lock) for route in ROUTES}
    for spec in specs.values():
        allocation(spec)
        verify_runtime_sources(spec)
        scientific_identity(spec, ROOT)
    # All source/data reads and validation precede the first output write.
    captured = {}
    for ref in _refs(specs["scripted"]):
        raw = read_bytes(ROOT, ref, max_bytes=4194304)
        if ref.path in captured and captured[ref.path] != raw:
            raise ValueError("conflicting matched scientific source")
        captured[ref.path] = raw
    for name in AUDIT_INPUTS:
        ref = reference(
            ROOT, name, media_type="application/octet-stream", producer="matched-cache-audit"
        )
        captured[name] = read_bytes(ROOT, ref, max_bytes=4194304)
        if captured[name] != audited_bytes[name]:
            raise ValueError("cache audit inputs changed during preparation")
    if len(captured) > 256 or sum(map(len, captured.values())) > 67108864:
        raise ValueError("matched source capture exceeds allowance")
    output.mkdir(mode=0o700)
    durable_write(output / "original-template.yaml", confined_file(ROOT, TEMPLATE).read_bytes())
    durable_write(output / "preparation-recipe.py", Path(__file__).read_bytes())
    inputs = []
    for name, raw in sorted(captured.items()):
        target = output / "captured_source" / name
        target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        durable_write(target, raw)
        inputs.append(
            reference(
                output,
                str(target.relative_to(output)),
                media_type="application/octet-stream",
                producer="matched-capture",
            )
        )
    (output / "campaigns").mkdir(mode=0o700)
    rows = []
    for route, spec in specs.items():
        target = output / "campaigns" / f"{route}.yaml"
        spec.to_yaml(target)
        rows.append(
            LeafRoute(
                route,
                reference(
                    output,
                    str(target.relative_to(output)),
                    media_type="application/yaml",
                    producer="matched-profile-author",
                ),
                scientific_identity(spec, output / "captured_source"),
            )
        )
    _historical_audit_inputs(template, output / "captured_source")
    audit = _audit(specs["scripted"])
    durable_write(output / "audit.json", canonical_json(audit).encode())
    plan = LeafPreparation(
        VERSION,
        PROTOCOL_DIGEST,
        reference(
            output,
            "original-template.yaml",
            media_type="application/yaml",
            producer="matched-preparation",
        ),
        reference(
            output,
            "preparation-recipe.py",
            media_type="text/x-python",
            producer="matched-preparation",
        ),
        tuple(rows),
        tuple(inputs),
        reference(
            output, "audit.json", media_type="application/json", producer="matched-preparation"
        ),
    )
    durable_write(output / "leaf-preparation.json", plan.to_json().encode())
    return plan


def load(root: Path, *, expected_digest: str) -> LeafPreparation:
    """Check the caller-pinned preparation without launching work or reading credentials."""
    sha256(expected_digest)
    root = checked_directory(root)
    with confined_file(root, "leaf-preparation.json").open("rb") as stream:
        raw = stream.read(131073)
    if len(raw) > 131072 or hashlib.sha256(raw).hexdigest() != expected_digest:
        raise ValueError("matched Leaf preparation differs from trusted pin")
    plan = LeafPreparation.from_json(raw.decode())
    read_bytes(root, plan.recipe, max_bytes=65536)
    read_bytes(root, plan.template, max_bytes=1048576)
    template = _template(confined_file(root, plan.template.path))
    for ref in plan.inputs:
        read_bytes(root, ref, max_bytes=4194304)
    audit = unique_json(read_bytes(root, plan.audit, max_bytes=65536).decode())
    source = root / "captured_source"
    _historical_audit_inputs(template, source)
    sources = tuple(
        reference(
            source, name, media_type="application/octet-stream", producer="matched-profile-author"
        )
        for name in sorted({*SOURCES, *scientific_source_paths()})
    )
    for row in plan.routes:
        read_bytes(root, row.specification, max_bytes=1048576)
        spec = CampaignSpec.from_yaml(confined_file(root, row.specification.path))
        environment_lock = reference(
            source,
            template.provenance.environment_lock.path,
            media_type=template.provenance.environment_lock.media_type,
            producer=template.provenance.environment_lock.producer,
        )
        if spec != _derive(template, row.route, sources, environment_lock):
            raise ValueError("matched route changed science, sources or allowances")
        if canonical_json(audit) != canonical_json(_audit(spec)):
            raise ValueError("matched Leaf audit differs from prepared protocol")
        verify_runtime_sources(spec)
        if scientific_identity(spec, source) != row.scientific_identity:
            raise ValueError("matched route scientific identity changed")
    expected_paths = {f"captured_source/{ref.path}" for ref in _refs(spec)} | {
        f"captured_source/{name}" for name in AUDIT_INPUTS
    }
    if {ref.path for ref in plan.inputs} != expected_paths:
        raise ValueError("matched input closure differs")
    return plan


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--verify", metavar="PREPARATION_SHA256")
    args = parser.parse_args()
    plan = load(args.output, expected_digest=args.verify) if args.verify else prepare(args.output)
    print(
        canonical_json(
            {
                "status": "prepared",
                "preparation_digest": plan.digest,
                "scientific_starts": 0,
                "provider_calls": 0,
                "execution_ready": False,
            }
        )
    )


if __name__ == "__main__":
    main()
