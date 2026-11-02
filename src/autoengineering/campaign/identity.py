"""Scientific identities bind the declared source closure, never host metadata."""

from __future__ import annotations

from pathlib import Path
from dataclasses import replace

from .artifacts import read_bytes
from .records import relative_path, unique
from .spec import CampaignSpec
from .serialization import digest, unique_json

SCIENTIFIC_CLOSURE = "src/autoengineering/campaign/scientific-closure-v1.json"
ISOLATED_SCIENTIFIC_CLOSURE = "src/autoengineering/campaign/scientific-closure-v2.json"
INTEROPERABILITY_SCIENTIFIC_CLOSURE = "src/autoengineering/campaign/scientific-closure-v3.json"
INTEROPERABILITY_SOURCES = (
    "adapters/bmi.py",
    "adapters/openmdao.py",
    "optimization/optuna_backend.py",
    "integrations/__init__.py",
    "integrations/contracts.py",
    "integrations/replay.py",
)
ISOLATED_SOURCES = (
    "campaign/container_execution.py",
    "adapters/registration.py",
    "adapters/isolated.py",
    "agents/__init__.py",
    "agents/interface.py",
    "agents/interface_worker.py",
    "agents/workspaces.py",
    "agents/qualification.py",
    "agents/containers.py",
    "agents/container_watchdog.py",
    "agents/container_recovery.py",
    "agents/sandbox.py",
)


def scientific_source_paths(package: Path | None = None, *, version: str = "1") -> tuple[str, ...]:
    """Read the versioned, shipped source allowlist for new scientific profiles.

    Version 1 excludes workers. Version 2 adds an explicit generated execution
    boundary. Version 3 adds the scientific interoperability implementations to
    version 1. Provider adapters and role prompts are absent from all profiles.
    """
    package = package or Path(__file__).resolve().parent.parent
    from .artifacts import confined_file

    if version not in ("1", "2", "3"):
        raise ValueError("unsupported scientific closure version")
    manifest = f"campaign/scientific-closure-v{version}.json"
    document = unique_json(confined_file(package, manifest).read_text())
    if not isinstance(document, dict) or set(document) != {"schema_version", "files"}:
        raise ValueError("invalid scientific closure manifest")
    if document["schema_version"] != "1.0" or not isinstance(document["files"], list):
        raise ValueError("unsupported scientific closure manifest")
    paths = document["files"]
    if not paths:
        raise ValueError("scientific closure is empty")
    for path in paths:
        if not isinstance(path, str):
            raise ValueError("scientific source must be a path")
        relative_path(path)
        if (path.startswith("agents/") and (version != "2" or path not in ISOLATED_SOURCES)) or (
            not path.endswith(".py")
        ):
            raise ValueError("host sources cannot enter the scientific closure")
        confined_file(package, path)
    unique(paths, "scientific source")
    manifests = (SCIENTIFIC_CLOSURE,)
    if version == "2":
        previous = scientific_source_paths(package)
        expected = {
            name.removeprefix("src/autoengineering/")
            for name in previous
            if name != SCIENTIFIC_CLOSURE
        } | set(ISOLATED_SOURCES)
        if set(paths) != expected:
            raise ValueError("isolated scientific closure differs from its explicit execution set")
        manifests += (ISOLATED_SCIENTIFIC_CLOSURE,)
    elif version == "3":
        previous = scientific_source_paths(package)
        expected = {
            name.removeprefix("src/autoengineering/")
            for name in previous if name != SCIENTIFIC_CLOSURE
        } | set(INTEROPERABILITY_SOURCES)
        if set(paths) != expected:
            raise ValueError("interoperability scientific closure differs from its explicit set")
        manifests += (INTEROPERABILITY_SCIENTIFIC_CLOSURE,)
    return tuple(f"src/autoengineering/{path}" for path in paths) + manifests


def verify_dependencies(spec: CampaignSpec, root: Path) -> dict[str, str]:
    """Verify all declared sources, lock, system and data before creating campaign files.

    The adapter registry separately checks its supplied dependency list against these
    sources. This is an explicit closure, not discovery of arbitrary Python imports.
    """
    refs = (
        spec.baseline.system,
        spec.provenance.environment_lock,
        *spec.provenance.sources,
        *(data.artifact for data in spec.data),
    )
    checked = {}
    for ref in refs:
        if ref.path in checked and checked[ref.path] != ref.sha256:
            raise ValueError("conflicting artifact identity")
        read_bytes(root, ref)
        checked[ref.path] = ref.sha256
    return checked


def scientific_identity(spec: CampaignSpec, root: Path) -> str:
    manifest = verify_dependencies(spec, root)
    return digest({"specification": spec.to_dict(), "source_manifest": manifest})


def verify_runtime_sources(spec: CampaignSpec) -> None:
    """Match the explicit engine bundle to the package executing this campaign.

    Supplied profiles declare this entire known package. This is not discovery of
    arbitrary model imports. Adapter registrations verify their own locations too.
    """
    package = Path(__file__).resolve().parent.parent
    declared = {ref.path: ref for ref in spec.provenance.sources}
    if INTEROPERABILITY_SCIENTIFIC_CLOSURE in declared:
        if ISOLATED_SCIENTIFIC_CLOSURE in declared:
            raise ValueError("combined generated/interoperability execution is not qualified")
        if SCIENTIFIC_CLOSURE not in declared:
            raise ValueError("interoperability closure is missing its base manifest")
        for manifest in (SCIENTIFIC_CLOSURE, INTEROPERABILITY_SCIENTIFIC_CLOSURE):
            read_bytes(
                package,
                replace(declared[manifest], path=manifest.removeprefix("src/autoengineering/")),
            )
        required = scientific_source_paths(package, version="3")
    elif ISOLATED_SCIENTIFIC_CLOSURE in declared:
        if SCIENTIFIC_CLOSURE not in declared:
            raise ValueError("isolated scientific closure is missing its base manifest")
        for manifest in (SCIENTIFIC_CLOSURE, ISOLATED_SCIENTIFIC_CLOSURE):
            read_bytes(
                package,
                replace(declared[manifest], path=manifest.removeprefix("src/autoengineering/")),
            )
        required = scientific_source_paths(package, version="2")
    elif SCIENTIFIC_CLOSURE in declared:
        # Verify the locally shipped allowlist against the frozen profile before
        # using it. A worker cannot submit a shortened source closure.
        read_bytes(
            package,
            replace(declared[SCIENTIFIC_CLOSURE], path="campaign/scientific-closure-v1.json"),
        )
        required = scientific_source_paths(package)
    else:
        # Historical manifests retain their original entire-package check.
        required = tuple(
            f"src/autoengineering/{path.relative_to(package)}" for path in package.rglob("*.py")
        )
    if "hydrology-learned-routing-v1" in spec.execution.adapter_ids:
        # Historical allowlists predate training grants and utility artifact readers.
        # This initial learned runtime requires the current entire engine closure.
        required = tuple(sorted(set(required) | {
            f"src/autoengineering/{path.relative_to(package)}" for path in package.rglob("*.py")
        }))
    for path in required:
        relative = path.removeprefix("src/autoengineering/")
        ref = declared.get(path)
        if ref is None:
            raise ValueError("declared engine source closure is incomplete")
        read_bytes(package, replace(ref, path=relative))
