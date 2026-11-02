"""Bounded public archive acquisition, separate from installation or image execution."""

from __future__ import annotations

import argparse
import hashlib
import math
import os
from pathlib import Path, PurePosixPath
import re
import time
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

from autoengineering.campaign.artifacts import confined_file
from autoengineering.campaign.serialization import canonical_json, digest, unique_json
from autoengineering.campaign.store import checked_directory, durable_write, sync_directory
from examples.utility import guest_image
from examples.utility.guest_image_context import _ref, _stream

CHUNK = 1024**2
SECONDS = 1200
TIMEOUT = 30


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, newurl):
        raise ValueError("archive redirects are outside the fixed request")


def _document(plan, source_digest, scope):
    payloads = [p for p in plan["payloads"] if p["url"] is not None]
    if not payloads or len(payloads) > 1024:
        raise ValueError("archive request has an invalid file count")
    for item in payloads:
        location = urlsplit(item["url"])
        parts = PurePosixPath(location.path).parts
        if (
            location.scheme != "https"
            or location.netloc != "conda.anaconda.org"
            or location.query
            or location.fragment
            or len(parts) != 4
            or parts[:2] != ("/", "conda-forge")
            or parts[2] not in ("linux-64", "noarch")
            or not re.fullmatch(r"[A-Za-z0-9_.+-]+\.(?:conda|tar\.bz2)", parts[-1])
        ):
            raise ValueError("archive URL is outside the pinned public origin")
        # URL paths have four parts: /, channel, platform, filename.
        if item["path"] not in ("archives/" + parts[-1], "installer/" + parts[-1]):
            raise ValueError("archive URL and cache filename differ")
        if not 0 < item["size_bytes"] <= 512 * 1024**2:
            raise ValueError("archive exceeds per-file envelope")
        _ref(item["path"], item["sha256"], item["size_bytes"])
    if len({p["path"] for p in payloads}) != len(payloads):
        raise ValueError("archive request has duplicate destinations")
    total = sum(p["size_bytes"] for p in payloads)
    if total > 8 * 1024**3:
        raise ValueError("archive request exceeds total envelope")
    return {
        "schema": "utility-guest-archive-request-v1",
        "image_plan": plan,
        "image_plan_digest": digest(plan),
        "payloads": payloads,
        "downloader_digest": source_digest,
        "cache_scope_digest": scope,
        "max_file_gets": len(payloads),
        "max_payload_bytes": total,
        "active_seconds": SECONDS,
        "socket_timeout_seconds": TIMEOUT,
        "redirects": 0,
        "automatic_retries": 0,
        "installation_authorized": False,
        "image_execution_authorized": False,
    }


def prepare_request(plan_root, *, expected_plan_digest, cache):
    plan = guest_image.verify(plan_root, expected_digest=expected_plan_digest)
    cache = Path(cache).absolute()
    guest_image._public_directory(cache.parent)
    if cache.exists() or cache.is_symlink():
        raise ValueError("archive request requires an absent target cache")
    source = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    return _document(plan, source, digest(str(cache)))


def _checked_request(request, expected_digest):
    if digest(request) != expected_digest or canonical_json(request) != canonical_json(
        _document(
            request["image_plan"], request["downloader_digest"], request["cache_scope_digest"]
        )
    ):
        raise ValueError("archive request differs from the explicit fixed request")
    return request


def _open(opener, item, remaining):
    request = Request(item["url"], headers={"Accept-Encoding": "identity"})
    return opener.open(request, timeout=min(TIMEOUT, remaining))


def download(request, *, expected_digest, cache, fault=None):
    request = _checked_request(request, expected_digest)
    cache = Path(cache).absolute()
    guest_image._public_directory(cache.parent)
    if digest(str(cache)) != request["cache_scope_digest"]:
        raise ValueError("archive request belongs to another target cache")
    if hashlib.sha256(Path(__file__).read_bytes()).hexdigest() != request["downloader_digest"]:
        raise ValueError("archive downloader source changed")
    if cache.exists() or cache.is_symlink():
        raise ValueError("archive cache already consumed; download cannot resume or retry")
    cache.mkdir(mode=0o700)
    for name in ("control", "requests", "partial"):
        (cache / name).mkdir(mode=0o700)
    began = time.monotonic()
    intent = {"request_digest": expected_digest, "began_at": began, "deadline": began + SECONDS}
    durable_write(cache / "control/request.json", canonical_json(request).encode())
    durable_write(cache / "control/downloader.py", Path(__file__).read_bytes())
    durable_write(cache / "control/intent.json", canonical_json(intent).encode())
    fault = fault or (lambda stage: None)
    fault("archive_intended")
    opener = build_opener(ProxyHandler({}), _NoRedirect())
    refs = {}
    received = 0

    def remaining():
        seconds = intent["deadline"] - time.monotonic()
        if seconds <= 0:
            raise TimeoutError("original archive request deadline expired")
        return seconds

    try:
        for number, item in enumerate(request["payloads"], start=1):
            remaining()
            event = {"request_digest": expected_digest, "index": number, "payload": item}
            durable_write(cache / "requests" / f"{number:04d}.json", canonical_json(event).encode())
            fault("before_archive_get")
            print(
                f"[{number}/{len(request['payloads'])}] {item['path']} "
                f"({item['size_bytes']} bytes)",
                flush=True,
            )
            partial = cache / "partial" / f"{number:04d}.part"
            with _open(opener, item, remaining()) as response:
                lengths = response.headers.get_all("Content-Length", [])
                if (
                    response.status != 200
                    or len(lengths) != 1
                    or not lengths[0].isdigit()
                    or int(lengths[0]) != item["size_bytes"]
                    or response.headers.get("Transfer-Encoding") is not None
                    or response.headers.get("Content-Encoding", "identity") != "identity"
                ):
                    raise ValueError(
                        "archive HTTP status/framing differs from pinned byte envelope"
                    )
                sha = hashlib.sha256()
                left = item["size_bytes"]
                with partial.open("xb") as stream:
                    os.fchmod(stream.fileno(), 0o600)
                    while left:
                        remaining()
                        content = response.read(min(CHUNK, left))
                        if not content:
                            raise ValueError("archive HTTP body is truncated")
                        if len(content) > left:
                            raise ValueError("archive HTTP body exceeds its pinned envelope")
                        left -= len(content)
                        received += len(content)
                        sha.update(content)
                        stream.write(content)
                    stream.flush()
                    os.fsync(stream.fileno())
                if sha.hexdigest() != item["sha256"]:
                    raise ValueError("archive digest differs from pin")
            remaining()
            parent = cache
            for part in Path(item["path"]).parts[:-1]:
                parent = parent / part
                parent.mkdir(mode=0o700, exist_ok=True)
                checked_directory(parent)
            target = cache / item["path"]
            os.link(partial, target)
            partial.unlink()
            sync_directory(parent)
            refs[item["path"]] = _ref(item["path"], item["sha256"], item["size_bytes"]).to_dict()
            fault("archive_saved")
        remaining()
        result = {
            "schema": "utility-guest-archive-completion-v1",
            "request_digest": expected_digest,
            "files": refs,
            "received_payload_bytes": received,
            "elapsed_seconds": time.monotonic() - began,
            "installed": False,
            "image_built": False,
            "runtime_qualified": False,
        }
        fault("before_archive_completion")
        durable_write(cache / "complete.json", canonical_json(result).encode())
        fault("after_archive_completion")
        return result
    except Exception as error:
        failure = {
            "request_digest": expected_digest,
            "error_type": type(error).__name__,
            "received_payload_bytes": received,
            "completed_files": len(refs),
        }
        if not (cache / "complete.json").exists():
            durable_write(cache / "failure.json", canonical_json(failure).encode())
        raise


def verify(cache, *, expected_digest):
    """Cold completed-cache check; no request, clock or source probe."""
    cache = checked_directory(cache)
    result_path = confined_file(cache, "complete.json")
    if result_path.stat().st_size > 1024**2:
        raise ValueError("archive completion exceeds envelope")
    result = unique_json(result_path.read_text())
    if digest(result) != expected_digest:
        raise ValueError("archive completion differs from explicit pin")
    if (
        set(result)
        != {
            "schema",
            "request_digest",
            "files",
            "received_payload_bytes",
            "elapsed_seconds",
            "installed",
            "image_built",
            "runtime_qualified",
        }
        or result["schema"] != "utility-guest-archive-completion-v1"
    ):
        raise ValueError("archive completion fields changed")
    if type(result["elapsed_seconds"]) not in (int, float) or not (
        math.isfinite(result["elapsed_seconds"]) and result["elapsed_seconds"] >= 0
    ):
        raise ValueError("archive completion timing is invalid")
    request_path = confined_file(cache, "control/request.json")
    if request_path.stat().st_size > 1024**2:
        raise ValueError("archive request exceeds envelope")
    request = unique_json(request_path.read_text())
    _checked_request(request, result["request_digest"])
    from autoengineering.campaign.records import ArtifactRef

    files = {
        p["path"]: _ref(p["path"], p["sha256"], p["size_bytes"]).to_dict()
        for p in request["payloads"]
    }
    if result["files"] != files or result["received_payload_bytes"] != request["max_payload_bytes"]:
        raise ValueError("archive completion differs from requested files/bytes")
    for value in files.values():
        _stream(cache, ArtifactRef.from_dict(value))
    code = confined_file(cache, "control/downloader.py")
    if (
        code.stat().st_size > 1024**2
        or hashlib.sha256(code.read_bytes()).hexdigest() != request["downloader_digest"]
    ):
        raise ValueError("archive downloader evidence changed")

    def metadata(name):
        path = confined_file(cache, name)
        if path.stat().st_size > 65536:
            raise ValueError("archive intent exceeds its metadata envelope")
        return unique_json(path.read_text())

    intent = metadata("control/intent.json")
    if (
        set(intent) != {"request_digest", "began_at", "deadline"}
        or intent["request_digest"] != result["request_digest"]
        or intent["deadline"] - intent["began_at"] != SECONDS
    ):
        raise ValueError("archive request intent changed")
    for number, payload in enumerate(request["payloads"], start=1):
        event = metadata(f"requests/{number:04d}.json")
        if event != {
            "request_digest": result["request_digest"],
            "index": number,
            "payload": payload,
        }:
            raise ValueError("archive GET intent changed")
    if any(result[k] is not False for k in ("installed", "image_built", "runtime_qualified")):
        raise ValueError("archive completion cannot qualify installation or execution")
    allowed = (
        set(files)
        | {
            "complete.json",
            "control/request.json",
            "control/downloader.py",
            "control/intent.json",
        }
        | {f"requests/{n:04d}.json" for n in range(1, len(request["payloads"]) + 1)}
    )
    actual = set()
    directories = {"partial"} | {
        str(parent) for name in allowed for parent in Path(name).parents if str(parent) != "."
    }
    for count, path in enumerate(cache.rglob("*"), start=1):
        name = str(path.relative_to(cache))
        if count > 4096 or path.is_symlink():
            raise ValueError("archive cache has excessive entries or a symlink")
        if path.is_dir():
            if name not in directories:
                raise ValueError("archive cache has an unreviewed directory")
        elif path.is_file():
            actual.add(name)
        else:
            raise ValueError("archive cache has a nonregular entry")
    if actual != allowed:
        raise ValueError("archive cache has unreviewed or missing evidence")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("request")
    prepare.add_argument("plan", type=Path)
    prepare.add_argument("cache", type=Path)
    prepare.add_argument("output", type=Path)
    prepare.add_argument("--expected-plan-digest", required=True)
    fetch = commands.add_parser("download")
    fetch.add_argument("request", type=Path)
    fetch.add_argument("cache", type=Path)
    fetch.add_argument("--expected-digest", required=True)
    args = parser.parse_args()
    if args.command == "request":
        result = prepare_request(
            args.plan, expected_plan_digest=args.expected_plan_digest, cache=args.cache
        )
        durable_write(args.output, canonical_json(result).encode())
    else:
        path = args.request
        if path.is_symlink() or path.stat().st_size > 1024**2:
            raise ValueError("unsafe archive request file")
        result = download(
            unique_json(path.read_text()), expected_digest=args.expected_digest, cache=args.cache
        )
    print(canonical_json({"digest": digest(result)}))


if __name__ == "__main__":
    main()
