"""Scientific identities bind the declared source closure, never host metadata."""

from __future__ import annotations

from pathlib import Path
from dataclasses import replace

from .artifacts import read_bytes
from .spec import CampaignSpec
from .serialization import digest


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
    for path in package.rglob("*.py"):
        relative = str(path.relative_to(package))
        ref = declared.get(f"src/autoengineering/{relative}")
        if ref is None:
            raise ValueError("declared engine source closure is incomplete")
        read_bytes(package, replace(ref, path=relative))
