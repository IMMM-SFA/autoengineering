"""Prepare an offline candidate image recipe; never acquire, install or execute.

Base image and installer metadata were inspected on 2026-10-30. Recipe generation
is not evidence that the installer, image, runtime or privacy boundary works.
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path, PurePosixPath

from autoengineering.campaign.artifacts import confined_file, put_bytes, read_bytes
from autoengineering.campaign.records import ArtifactRef
from autoengineering.campaign.serialization import canonical_json, digest, unique_json
from autoengineering.campaign.store import checked_directory, durable_write
from autoengineering.utility.guest_receipts import BOOTSTRAP_COMMAND, ENVIRONMENT
from examples.utility.inference_environment import verify_inputs

BASE = {
    "repository": "docker.io/library/python",
    "platform": "linux/amd64",
    "manifest_digest": "sha256:623674a14ef93d052bb9b0de4dbf5f28eb578a35263838941cc8aa43213c1487",
    "image_id": "sha256:37ccb536022bb36c4570856b55ebfa85bf07827e3c2fa3eba37f0dac62eebc05",
    "compressed_layer_bytes": 45269741,
    "metadata_url": "https://raw.githubusercontent.com/docker-library/repo-info/"
    "master/repos/python/remote/3.12-slim-bookworm.md",
}
INSTALLER = {
    "filename": "micromamba-2.9.0-0.tar.bz2",
    "url": "https://conda.anaconda.org/conda-forge/linux-64/micromamba-2.9.0-0.tar.bz2",
    "sha256": "8761c382127e6363bd9e0a2451aa3ef90d071a79133f736e2f759a3bf13040dd",
    "size_bytes": 6988090,
    "metadata_url": "https://api.anaconda.org/release/conda-forge/micromamba/2.9.0",
    "license_metadata": "BSD-3-Clause AND MIT AND OpenSSL",
}


def _public_directory(path):
    path = Path(path).absolute()
    if ".." in path.parts or any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError("guest image scope contains traversal or a symlink")
    if not path.is_dir():
        raise ValueError("guest image scope directory is missing")
    return path


def _source_alignment(inputs, source_root):
    """All core files and every declared wheel Python source must match bytes."""
    source_root = _public_directory(source_root)
    core = {
        "autoengineering/" + str(p.relative_to(source_root / "src/autoengineering"))
        for p in (source_root / "src/autoengineering").rglob("*.py")
    }
    wheel_core = {
        r.path for r in inputs.wheel_python_sources if r.path.startswith("autoengineering/")
    }
    if not core or core != wheel_core:
        raise ValueError("guest image wheel differs from the current core source set")
    for ref in inputs.wheel_python_sources:
        name = "src/" + ref.path if ref.path.startswith("autoengineering/") else ref.path
        path = confined_file(source_root, name)
        with path.open("rb") as stream:
            content = stream.read(ref.size_bytes + 1)
        if len(content) != ref.size_bytes or hashlib.sha256(content).hexdigest() != ref.sha256:
            raise ValueError("guest image wheel differs from current declared source bytes")


def _payloads(inputs):
    files = [
        {
            "path": "archives/" + PurePosixPath(p.url).name,
            "sha256": p.sha256,
            "size_bytes": p.compressed_bytes,
            "url": p.url,
        }
        for p in inputs.archives
    ]
    files.append(
        {
            "path": "installer/" + INSTALLER["filename"],
            **{k: INSTALLER[k] for k in ("sha256", "size_bytes", "url")},
        }
    )
    filename = PurePosixPath(inputs.wheel.path).name
    if filename != f"autoengineering-{inputs.wheel_version}-py3-none-any.whl":
        raise ValueError("guest image recipe supports only the reviewed pure Python wheel name")
    files.append(
        {
            "path": "wheel/" + filename,
            "sha256": inputs.wheel.sha256,
            "size_bytes": inputs.wheel.size_bytes,
            "url": None,
        }
    )
    if len({f["path"] for f in files}) != len(files):
        raise ValueError("guest image payload names collide")
    return files


def _recipes(inputs):
    files = _payloads(inputs)
    explicit = "@EXPLICIT\n" + "".join(
        "file:///build/archives/" + PurePosixPath(p.url).name + "#sha256:" + p.sha256 + "\n"
        for p in inputs.archives
    )
    checksums = "".join(f"{f['sha256']}  {f['path']}\n" for f in files)
    extract = '''"""Run only inside the authorized image build after archive hash verification."""
from pathlib import Path
import tarfile
with tarfile.open('/build/installer/micromamba-2.9.0-0.tar.bz2', 'r:bz2') as archive:
    members = archive.getmembers()
    if len(members) > 1024 or sum(m.size for m in members) > 64 * 1024 * 1024:
        raise ValueError('installer archive exceeds its extraction envelope')
    selected = [m for m in members if m.name == 'bin/micromamba']
    if len(selected) != 1 or not selected[0].isfile() or selected[0].size > 32 * 1024 * 1024:
        raise ValueError('installer executable differs from reviewed archive layout')
    with archive.extractfile(selected[0]) as stream:
        content = stream.read(32 * 1024 * 1024 + 1)
    if len(content) != selected[0].size:
        raise ValueError('installer executable size differs')
path = Path('/build/micromamba')
with path.open('xb') as stream:
    stream.write(content)
path.chmod(0o555)
'''
    wheel = next(f["path"] for f in files if f["path"].startswith("wheel/"))
    dockerfile = f"""FROM {BASE["repository"]}@{BASE["manifest_digest"]}
WORKDIR /build
COPY archives/ /build/archives/
COPY installer/ /build/installer/
COPY wheel/ /build/wheel/
COPY explicit.txt checksums.sha256 extract_installer.py /build/
RUN sha256sum -c checksums.sha256
RUN /usr/local/bin/python -I /build/extract_installer.py
RUN /build/micromamba --no-rc --no-env --root-prefix /opt/mamba create \\
    --yes --prefix /opt/inference --offline --file /build/explicit.txt
RUN /usr/local/bin/python -I -m pip --python /opt/inference/bin/python install \\
    --no-index --no-deps --no-compile --disable-pip-version-check /build/{wheel}
RUN /opt/inference/bin/python -I -c "import numpy, scipy, pandas, autoengineering"
RUN mkdir -p /work && chown 1000:1000 /work && chmod 0700 /work
RUN rm -rf /build /opt/mamba
WORKDIR /work
USER 1000:1000
"""
    dockerfile += "".join(f"ENV {name}={value}\n" for name, value in ENVIRONMENT)
    dockerfile += "ENTRYPOINT []\nCMD " + canonical_json(list(BOOTSTRAP_COMMAND)) + "\n"
    names = ["Dockerfile", "explicit.txt", "checksums.sha256", "extract_installer.py"]
    ignore = "**\n" + "".join("!" + name + "\n" for name in names)
    ignore += "!archives/\n!installer/\n!wheel/\n"
    ignore += "".join("!" + f["path"] + "\n" for f in files)
    return {
        "Dockerfile": dockerfile.encode(),
        "explicit.txt": explicit.encode(),
        "checksums.sha256": checksums.encode(),
        "extract_installer.py": extract.encode(),
        ".dockerignore": ignore.encode(),
    }


def _plan(inputs, preparer, recipes):
    return {
        "schema": "utility-guest-image-preparation-v1",
        "environment_inputs_digest": inputs.digest,
        "base": BASE,
        "installer": INSTALLER,
        "payloads": _payloads(inputs),
        "remote_payload_bytes": inputs.compressed_archive_bytes
        + INSTALLER["size_bytes"]
        + BASE["compressed_layer_bytes"],
        "registry_metadata_budget_bytes": 1048576,
        "wheel_python_sources_digest": digest([r.to_dict() for r in inputs.wheel_python_sources]),
        "preparer": preparer.to_dict(),
        "recipes": {name: ref.to_dict() for name, ref in recipes.items()},
        "build_platform": "linux/amd64",
        "build_network": "none",
        "candidate_build_limits": {"attempts": 1, "wall_seconds": 1200, "disk_bytes": 8 * 1024**3},
        "status": "recipe_only",
        "acquisition_authorized": False,
        "build_authorized": False,
        "starts_authorized": False,
        "runtime_qualified": False,
        "uncompressed_bytes": None,
    }


def prepare(environment_root, *, expected_digest, source_root, output):
    """Generate reviewed input/recipe bytes only, refusing stale wheels and overwrite."""
    inputs = verify_inputs(environment_root, expected_digest=expected_digest)
    _source_alignment(inputs, source_root)
    recipes = _recipes(inputs)
    output = Path(output).absolute()
    if output.exists() or output.is_symlink():
        raise ValueError("guest image preparation requires an absent output")
    _public_directory(output.parent)
    output.mkdir(mode=0o700)
    environment = output / "environment"
    environment.mkdir(mode=0o700)
    # Copy only the two declared payloads and bounded metadata, never other files.
    for ref in (inputs.lock, inputs.wheel):
        content = read_bytes(environment_root, ref, max_bytes=8 * 1024 * 1024)
        target = environment / ref.path
        target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        durable_write(target, content)
    for name in ("manifest.json", "review.json"):
        content = confined_file(environment_root, name).read_bytes()
        if len(content) > 4 * 1024 * 1024:
            raise ValueError("guest environment metadata exceeds envelope")
        durable_write(environment / name, content)
    (output / "artifacts").mkdir(mode=0o700)
    preparer = put_bytes(
        output,
        Path(__file__).read_bytes(),
        name="guest_image.py",
        media_type="text/x-python",
        producer="guest-image-preparation",
    )
    refs = {
        name: put_bytes(
            output,
            data,
            name=name.lstrip("."),
            media_type="text/plain",
            producer="guest-image-preparation",
        )
        for name, data in recipes.items()
    }
    plan = _plan(inputs, preparer, refs)
    durable_write(output / "plan.json", canonical_json(plan).encode())
    return plan


def verify(root, *, expected_digest):
    """Verify saved bytes only. No source workspace, clock, process or service."""
    root = checked_directory(root)
    path = confined_file(root, "plan.json")
    if path.stat().st_size > 1024 * 1024:
        raise ValueError("guest image plan exceeds envelope")
    plan = unique_json(path.read_text())
    if digest(plan) != expected_digest:
        raise ValueError("guest image plan differs from explicit pin")
    inputs = verify_inputs(root / "environment", expected_digest=plan["environment_inputs_digest"])
    preparer = ArtifactRef.from_dict(plan["preparer"])
    read_bytes(root, preparer, max_bytes=1024 * 1024)
    refs = {name: ArtifactRef.from_dict(value) for name, value in plan["recipes"].items()}
    recipes = _recipes(inputs)
    if set(refs) != set(recipes):
        raise ValueError("guest image recipe file set differs")
    for name, ref in refs.items():
        if read_bytes(root, ref, max_bytes=1024 * 1024) != recipes[name]:
            raise ValueError("guest image recipe differs from its reviewed inputs")
    if canonical_json(plan) != canonical_json(_plan(inputs, preparer, refs)):
        raise ValueError("guest image plan differs from its nonexecuting recipe")
    return plan


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("environment", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--expected-digest", required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    plan = prepare(
        args.environment,
        expected_digest=args.expected_digest,
        source_root=args.source_root,
        output=args.output,
    )
    print(
        canonical_json(
            {
                "plan_digest": digest(plan),
                "status": plan["status"],
                "remote_payload_bytes": plan["remote_payload_bytes"],
            }
        )
    )


if __name__ == "__main__":
    main()
