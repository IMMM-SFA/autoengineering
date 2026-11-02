"""Prepare pinned Linux inference inputs offline; never install, fetch or execute.

This is an administrative input package, not a qualified image or a guest job
contract. The current v1 inference job remains bound to its host interpreter/scope.
"""

from __future__ import annotations

from dataclasses import dataclass
from email.parser import BytesParser
import hashlib
import io
from pathlib import Path, PurePosixPath
import re
import stat
from typing import Literal
from urllib.parse import urlsplit
import zipfile

import yaml

from autoengineering.campaign.artifacts import confined_file, put_bytes, read_bytes
from autoengineering.campaign.records import ArtifactRef
from autoengineering.campaign.serialization import Record, canonical_json, unique_json
from autoengineering.campaign.store import checked_directory, durable_write
from autoengineering.utility.contracts import sha256

ROOTS = ("click", "networkx", "numpy", "pandas", "python", "pyyaml", "rich", "scipy")
MAX_WHEEL = 4 * 1024 * 1024


@dataclass(frozen=True)
class CondaArchive(Record):
    name: str
    version: str
    build: str
    url: str
    sha256: str
    compressed_bytes: int
    license_metadata: str
    depends: tuple[str, ...]
    constrains: tuple[str, ...]

    def _validate(self):
        sha256(self.sha256)
        if self.compressed_bytes <= 0:
            raise ValueError("runtime archive needs its locked compressed size")
        if not re.fullmatch(r"[a-z0-9_.-]+", self.name):
            raise ValueError("unsupported conda package name")


@dataclass(frozen=True)
class InferenceEnvironmentInputs(Record):
    schema: Literal["utility-inference-environment-inputs-v1"]
    platform: Literal["linux-64"]
    environment: Literal["default"]
    lock: ArtifactRef
    wheel: ArtifactRef
    wheel_version: str
    wheel_python_sources: tuple[ArtifactRef, ...]
    roots: tuple[str, ...]
    archives: tuple[CondaArchive, ...]
    virtual_constraints: tuple[str, ...]
    locked_platform_assumptions: tuple[str, ...]
    preparer_digest: str
    starts_authorized: Literal[False] = False
    dependency_constraints_rechecked: Literal[False] = False
    runtime_qualified: Literal[False] = False

    def _validate(self):
        sha256(self.preparer_digest)
        if self.roots != ROOTS or not self.archives:
            raise ValueError("inference inputs require the fixed core dependency roots")
        names = tuple(p.name for p in self.archives)
        if names != tuple(sorted(set(names))) or not set(self.roots) <= set(names):
            raise ValueError("inference archives must be unique, ordered and cover all roots")

    @property
    def compressed_archive_bytes(self):
        return sum(p.compressed_bytes for p in self.archives)


class _UniqueLoader(yaml.SafeLoader):
    pass


def _mapping(loader, node):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=True)
        if key in result:
            raise ValueError("duplicate lockfile field")
        result[key] = loader.construct_object(value_node, deep=True)
    return result


_UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapping)


def _archive(record):
    url = record["conda"]
    location = urlsplit(url)
    path = PurePosixPath(location.path)
    if (
        location.scheme != "https"
        or location.netloc != "conda.anaconda.org"
        or location.query
        or location.fragment
        or path.parts[:3] not in (("/", "conda-forge", "linux-64"), ("/", "conda-forge", "noarch"))
        or len(path.parts) != 4
        or not re.fullmatch(r"[A-Za-z0-9_.+-]+\.(?:conda|tar\.bz2)", path.name)
    ):
        raise ValueError("inference archive must be a pinned conda-forge Linux/noarch file")
    stem = path.name.removesuffix(".conda").removesuffix(".tar.bz2")
    name, version, build = stem.rsplit("-", 2)
    return CondaArchive(
        name,
        version,
        build,
        url,
        record["sha256"],
        record["size"],
        record["license"],
        tuple(record.get("depends", ())),
        tuple(record.get("constrains", ())),
    )


def locked_archives(raw):
    """Select dependencies from the existing resolved environment; no new solver."""
    value = yaml.load(raw, Loader=_UniqueLoader)
    if (
        not isinstance(value, dict)
        or type(value.get("version")) is not int
        or value["version"] != 7
        or set(value) != {"version", "platforms", "environments", "packages"}
    ):
        raise ValueError("inference preparation supports pixi lock schema 7 only")
    records = {}
    for record in value["packages"]:
        key = record.get("conda", record.get("pypi"))
        if key in records:
            raise ValueError("duplicate locked package location")
        records[key] = record
    selected, local_projects = {}, 0
    for item in value["environments"]["default"]["packages"]["linux-64"]:
        if set(item) == {"pypi"} and item["pypi"] == "./":
            local_projects += 1
            if records.get("./", {}).get("name") != "autoengineering":
                raise ValueError("local locked project differs from the pinned wheel")
            continue  # The separately pinned wheel replaces the local editable project.
        if set(item) != {"conda"}:
            raise ValueError("unsupported non-conda dependency in the locked default environment")
        package = _archive(records[item["conda"]])
        if package.name in selected:
            raise ValueError("locked environment selects a package name twice")
        selected[package.name] = package
    if local_projects != 1:
        raise ValueError("locked default environment must select the local project once")
    pending, closure, virtual = list(ROOTS), {}, set()
    while pending:
        name = pending.pop()
        if name in closure:
            continue
        if name not in selected:
            raise ValueError("runtime dependency is absent from the locked selection")
        package = selected[name]
        closure[name] = package
        for requirement in package.depends:
            match = re.fullmatch(r"([a-z0-9_.-]+)(?:\s+[^\n]+)?", requirement)
            if match is None:
                raise ValueError("unsupported conda dependency syntax")
            if match[1].startswith("__"):
                virtual.add(requirement)
            else:
                pending.append(match[1])
    if not re.fullmatch(r"3\.12\.[0-9]+", selected["python"].version):
        raise ValueError("inference runtime must retain Python 3.12")
    platforms = [p for p in value["platforms"] if p["name"] == "linux-64"]
    if len(platforms) != 1 or not isinstance(platforms[0].get("virtual-packages"), list):
        raise ValueError("Linux platform assumptions are absent or ambiguous")
    assumptions = tuple(platforms[0]["virtual-packages"])
    if not all(isinstance(p, str) and p.startswith("__") for p in assumptions):
        raise ValueError("invalid locked virtual platform assumptions")
    if "__archspec=0=x86_64" not in assumptions:
        raise ValueError("inference inputs require locked x86-64 platform assumptions")
    return tuple(closure[n] for n in sorted(closure)), tuple(sorted(virtual)), assumptions


def wheel_sources(raw):
    """Read bounded wheel metadata/code bytes, without imports or extraction."""
    if len(raw) > MAX_WHEEL:
        raise ValueError("inference wheel exceeds the input envelope")
    sources, metadata, wheel_headers, total = [], [], [], 0
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        members = archive.infolist()
        names = [m.filename for m in members]
        if len(members) > 1024 or len(names) != len(set(names)):
            raise ValueError("inference wheel has duplicate or excessive members")
        for member in members:
            path = PurePosixPath(member.filename)
            total += member.file_size
            if (
                path.is_absolute()
                or ".." in path.parts
                or "\\" in member.filename
                or member.file_size > 1024 * 1024
                or total > 32 * 1024 * 1024
                or stat.S_ISLNK(member.external_attr >> 16)
                or member.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED)
            ):
                raise ValueError("inference wheel contains an unsafe or oversized member")
            if member.is_dir():
                continue
            if member.filename.endswith(".dist-info/METADATA"):
                metadata.append(archive.read(member))
            if member.filename.endswith(".dist-info/WHEEL"):
                wheel_headers.append(archive.read(member))
            if member.filename.endswith(".py") and path.parts[0] in ("autoengineering", "examples"):
                content = archive.read(member)
                sources.append(
                    ArtifactRef(
                        member.filename,
                        hashlib.sha256(content).hexdigest(),
                        len(content),
                        "text/x-python",
                        "pinned-wheel",
                        {},
                    )
                )
    if len(metadata) != 1 or len(wheel_headers) != 1:
        raise ValueError("inference wheel must contain exactly one project metadata record")
    fields = BytesParser().parsebytes(metadata[0])
    headers = BytesParser().parsebytes(wheel_headers[0])
    python = fields.get_all("Requires-Python", [])
    if (
        fields.get_all("Name") != ["autoengineering"]
        or fields.get_all("Version") is None
        or len(fields.get_all("Version")) != 1
        or len(python) != 1
        or sorted(p.strip() for p in python[0].split(",")) != ["<3.13", ">=3.12"]
        or headers.get_all("Root-Is-Purelib") != ["true"]
        or headers.get_all("Tag") != ["py3-none-any"]
    ):
        raise ValueError("inference wheel has unsupported project/Python metadata")
    prefix = f"autoengineering-{fields['Version']}.dist-info/"
    if prefix + "METADATA" not in names or prefix + "WHEEL" not in names:
        raise ValueError("inference wheel metadata paths differ from its project/version")
    requirements = set()
    for text in fields.get_all("Requires-Dist", []):
        if ";" in text:
            if not re.fullmatch(r'.*;\s*extra == "[A-Za-z0-9_.-]+"', text):
                raise ValueError("unsupported conditional core wheel dependency")
            continue
        match = re.match(r"[A-Za-z0-9_.-]+", text)
        if match is None:
            raise ValueError("invalid core wheel dependency")
        requirements.add(match[0].lower().replace("_", "-"))
    if requirements != set(ROOTS) - {"python"}:
        raise ValueError("inference wheel core requirements differ from the fixed roots")
    required = {
        "autoengineering/utility/inference_worker.py",
        "autoengineering/utility/inference_execution.py",
    }
    if not required <= {r.path for r in sources}:
        raise ValueError("inference wheel lacks the fixed worker sources")
    return fields["Version"], tuple(sorted(sources, key=lambda r: r.path))


def prepare_inputs(source_root, *, lock, wheel, output):
    """Publish a new owner-private metadata package, manifest last. No acquisition."""
    raw_lock = read_bytes(source_root, lock, max_bytes=8 * 1024 * 1024)
    raw_wheel = read_bytes(source_root, wheel, max_bytes=MAX_WHEEL)
    archives, virtual, assumptions = locked_archives(raw_lock)
    version, sources = wheel_sources(raw_wheel)
    filename = f"autoengineering-{version}-py3-none-any.whl"
    if PurePosixPath(wheel.path).name != filename:
        raise ValueError("inference inputs require the original pure project wheel filename")
    root = Path(output).absolute()
    if ".." in root.parts or any(part.is_symlink() for part in (*root.parents, root)):
        raise ValueError("inference package output cannot traverse parents or symlinks")
    root.mkdir(mode=0o700)  # Never replace a prepared or interrupted package.
    checked_directory(root)
    (root / "artifacts").mkdir(mode=0o700)
    saved_lock = put_bytes(
        root, raw_lock, name="pixi.lock", media_type="text/plain", producer="pixi"
    )
    saved_wheel = put_bytes(
        root,
        raw_wheel,
        name=filename,
        media_type="application/zip",
        producer="pinned-wheel",
    )
    result = InferenceEnvironmentInputs(
        "utility-inference-environment-inputs-v1",
        "linux-64",
        "default",
        saved_lock,
        saved_wheel,
        version,
        sources,
        ROOTS,
        archives,
        virtual,
        assumptions,
        hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    )
    durable_write(root / "review.json", (canonical_json(review_for(result)) + "\n").encode())
    durable_write(root / "manifest.json", (result.to_json() + "\n").encode())
    return result


def review_for(result):
    """Proposed policy only, not an actual enforced limit or admission."""
    guest = any(
        r.path == "autoengineering/utility/inference_guest.py" for r in result.wheel_python_sources
    )
    return {
        "schema": "utility-inference-environment-review-v1",
        "inputs_digest": result.digest,
        "status": "prepared_inputs_only",
        "image_identity": None,
        "compressed_archive_bytes": result.compressed_archive_bytes,
        "uncompressed_environment_bytes": None,
        "candidate_limits": {
            "memory_bytes": 1073741824,
            "cpu_count": 1,
            "pids": 16,
            "workspace_bytes": 134217728,
            "network": "none",
            "read_only_root": True,
            "timeout_seconds": 60,
        },
        "blockers": [
            "Linux x86-64 base image identity and compatibility unqualified",
            "locked archives not acquired or installed",
            "environment assembly and offline wheel installation unqualified",
            "guest transport candidate sources present; guest launcher/receipt unqualified"
            if guest
            else "v1 worker is host-interpreter/workspace-bound; guest contract missing",
            "OS privacy, memory/CPU/output/deadline/failure controls unqualified",
        ],
        "starts_authorized": False,
    }


def verify_inputs(root, *, expected_digest):
    """Reconstruct one explicitly pinned package using only its saved bytes."""
    sha256(expected_digest)
    root = checked_directory(root)

    def document(name, limit):
        with confined_file(root, name).open("rb") as stream:
            raw = stream.read(limit + 1)
        if len(raw) > limit:
            raise ValueError("inference input document exceeds its envelope")
        return unique_json(raw.decode())

    result = InferenceEnvironmentInputs.from_dict(document("manifest.json", 4 * 1024 * 1024))
    if result.digest != expected_digest:
        raise ValueError("inference input manifest differs from the explicit pin")
    archives, virtual, assumptions = locked_archives(
        read_bytes(root, result.lock, max_bytes=8 * 1024 * 1024)
    )
    version, sources = wheel_sources(read_bytes(root, result.wheel, max_bytes=MAX_WHEEL))
    if (archives, virtual, assumptions, version, sources) != (
        result.archives,
        result.virtual_constraints,
        result.locked_platform_assumptions,
        result.wheel_version,
        result.wheel_python_sources,
    ):
        raise ValueError("inference metadata differs from its pinned lock/wheel payloads")
    if canonical_json(document("review.json", 65536)) != canonical_json(review_for(result)):
        raise ValueError("inference review differs from its nonexecuting input profile")
    return result
