"""Probe one owned CFPreferences canary domain, never existing user preferences.

This writes/removes one new random test-domain key using public CF APIs. It is a
policy diagnostic with a substituted executable, not actual host qualification.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import plistlib
import stat
from pathlib import Path
import platform
import subprocess
import sys
import time
import uuid

from autoengineering.agents.hosts.claude_policy import ClaudePolicy, VERSION, render_claude_policy
from autoengineering.agents.identity import host_source_identity
from autoengineering.agents.process import supervise_process, recover_completed_process
from autoengineering.campaign.artifacts import confined_file
from autoengineering.campaign.records import sha256
from autoengineering.campaign.serialization import unique_json
from autoengineering.campaign.store import durable_write

PREFIX = "org.autoengineering.qualification."
SOURCE = r"""
#include <CoreFoundation/CoreFoundation.h>
#include <stdio.h>
#include <string.h>
static int hex32(const char *v) {
 return strlen(v)==32 && strspn(v,"0123456789abcdef")==32;
}
int main(int argc,char **argv) {
 const char *prefix="org.autoengineering.qualification.";
 if(argc!=4 || strncmp(argv[2],prefix,strlen(prefix)) ||
    !hex32(argv[2]+strlen(prefix)) || !hex32(argv[3])) return 2;
 int seed=!strcmp(argv[1],"seed"), clear=!strcmp(argv[1],"clear");
 if(!seed && !clear && strcmp(argv[1],"read")) return 2;
 CFStringRef domain=CFStringCreateWithCString(NULL,argv[2],kCFStringEncodingUTF8);
 CFStringRef expected=CFStringCreateWithCString(NULL,argv[3],kCFStringEncodingUTF8);
 CFStringRef key=CFSTR("AEQualificationCanary");
 if(!domain || !expected) return 3;
 CFPropertyListRef before=CFPreferencesCopyValue(key,domain,kCFPreferencesCurrentUser,kCFPreferencesAnyHost);
 if((seed && before) || (clear && before && !CFEqual(before,expected))) return 4;
 if(before) CFRelease(before);
 int synchronized=-1;
 if(seed || clear) {
  CFPreferencesSetValue(key,seed?expected:NULL,domain,kCFPreferencesCurrentUser,kCFPreferencesAnyHost);
  synchronized=CFPreferencesSynchronize(domain,kCFPreferencesCurrentUser,kCFPreferencesAnyHost)?1:0;
 }
 CFPropertyListRef value=CFPreferencesCopyValue(key,domain,kCFPreferencesCurrentUser,kCFPreferencesAnyHost);
 printf("{\"present\":%d,\"visible\":%d,\"synchronized\":%d}\n",
        value?1:0,value&&CFEqual(value,expected)?1:0,synchronized);
 if(value) CFRelease(value);
 CFRelease(expected);CFRelease(domain);return 0;
}
"""


def _validate_domain(domain, marker):
    suffix = domain.removeprefix(PREFIX)
    if (
        not domain.startswith(PREFIX)
        or len(suffix) != 32
        or len(marker) != 32
        or any(c not in "0123456789abcdef" for c in suffix + marker)
    ):
        raise ValueError("only one owned random qualification domain is permitted")


def _decode(raw):
    value = unique_json(raw.decode())
    if (
        not isinstance(value, dict)
        or set(value) != {"present", "visible", "synchronized"}
        or any(type(value[k]) is not int or value[k] not in (0, 1) for k in ("present", "visible"))
        or type(value["synchronized"]) is not int
        or value["synchronized"] not in (-1, 0, 1)
        or value["visible"] > value["present"]
    ):
        raise ValueError("invalid preference canary observation")
    return value


class PendingPreferenceFlush(ValueError):
    """Only this run's known canary remains in its otherwise owned domain."""


def _remove_empty_domain(preferences_root: Path, domain: str, *, expected_canary=None):
    """Remove only this bound owned domain's empty, regular, single-link file."""
    _validate_domain(domain, "0" * 32)
    root = Path(preferences_root).absolute()
    if any(p.is_symlink() for p in (root, *root.parents)):
        raise ValueError("preference storage parent is symlinked")
    path = root / (domain + ".plist")
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except FileNotFoundError:
        return False
    try:
        info = os.fstat(descriptor)
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != os.getuid()
            or info.st_nlink != 1
            or info.st_size > 4096
        ):
            raise ValueError("owned preference storage is not a bounded private regular file")
        raw = os.read(descriptor, 4097)
        if len(raw) > 4096:
            raise ValueError("owned preference storage exceeds bound")
        value = plistlib.loads(raw)
        if value != {}:
            if expected_canary is not None:
                _validate_domain(domain, expected_canary)
                if value == {"AEQualificationCanary": expected_canary}:
                    raise PendingPreferenceFlush("owned canary has not flushed to empty storage")
            raise ValueError("owned preference storage is not empty; refusing deletion")
        current = path.lstat()
        if (current.st_dev, current.st_ino) != (info.st_dev, info.st_ino):
            raise ValueError("owned preference storage changed before cleanup")
        path.unlink()
    finally:
        os.close(descriptor)
    return True


def _wait_remove_empty_domain(root, domain, marker, *, timeout_seconds=5):
    _validate_domain(domain, marker)
    if type(timeout_seconds) not in (int, float) or not 0 <= timeout_seconds <= 5:
        raise ValueError("preference flush wait must be bounded by five seconds")
    deadline = time.monotonic() + timeout_seconds
    pending = 0
    while True:
        try:
            removed = _remove_empty_domain(root, domain, expected_canary=marker)
            return {
                "removed": removed,
                "deferred_flush_observations": pending,
                "wait_limit_seconds": timeout_seconds,
            }
        except PendingPreferenceFlush:
            pending += 1
            if time.monotonic() >= deadline:
                raise ValueError("owned preference canary did not flush within the bound") from None
            time.sleep(min(0.05, max(0, deadline - time.monotonic())))


def probe(output: Path):
    if sys.platform != "darwin" or platform.machine() != "arm64":
        raise ValueError("this preference-service diagnostic requires macOS ARM64")
    output = Path(output).absolute()
    if output.exists() or any(p.is_symlink() for p in (output, *output.parents)):
        raise ValueError("preference probe requires a fresh nonsymlink directory")
    output.mkdir(mode=0o700)
    for name in ("code", "workspace", "home", "auth", "private"):
        (output / name).mkdir(mode=0o700)
    source, binary = output / "code/probe.c", output / "code/probe"
    durable_write(source, SOURCE.encode())
    compiled = subprocess.run(
        (
            "/usr/bin/clang",
            "-std=c11",
            "-O0",
            str(source),
            "-framework",
            "CoreFoundation",
            "-o",
            str(binary),
        ),
        capture_output=True,
        timeout=30,
        check=False,
    )
    durable_write(output / "compile.stdout", compiled.stdout)
    durable_write(output / "compile.stderr", compiled.stderr)
    if compiled.returncode:
        raise ValueError("preference probe compilation failed")
    helper = output / "auth/helper"
    durable_write(helper, b"#!/bin/sh\nexit 0\n")
    helper.chmod(0o700)
    python = Path(sys.executable).resolve()
    spec = ClaudePolicy(
        VERSION,
        str(output / "workspace"),
        str(output / "home"),
        str(binary),
        str(helper),
        str(python),
        str(Path(sys.prefix).resolve()),
        (),
        (),
        (str(output / "private"), str(Path.cwd().resolve())),
    )
    policy = output / "policy.sb"
    durable_write(policy, render_claude_policy(spec).encode())
    domain, marker = PREFIX + uuid.uuid4().hex, uuid.uuid4().hex
    _validate_domain(domain, marker)
    # Keep an immutable cleanup binding before any preference write. The probe
    # can only address its new random domain and fixed key, never a known app.
    durable_write(output / "scope.json", json.dumps({"domain": domain, "marker": marker}).encode())
    real_home = str(Path.home().resolve())
    preference_file = Path(real_home) / "Library/Preferences" / (domain + ".plist")
    if preference_file.exists() or preference_file.is_symlink():
        raise ValueError("random canary domain already has storage; refusing to write")
    observations = {}
    stops_verified = True
    seed_attempted = False

    def run(name, mode, *, sandbox=False, private_home=False):
        nonlocal stops_verified
        command = (str(binary), mode, domain, marker)
        if sandbox:
            command = ("/usr/bin/sandbox-exec", "-f", str(policy), *command)
        result = supervise_process(
            command,
            directory=output / name,
            cwd=output / "workspace",
            environment={
                "PATH": "/usr/bin:/bin",
                "LANG": "C.UTF-8",
                "HOME": str(output / "home") if private_home else real_home,
            },
            nonce="preference-" + name,
            stdin=b"",
            timeout_seconds=10,
            max_output_bytes=8192,
            on_launch=lambda _: None,
            parent_watchdog=True,
        )
        if not result.stopped:
            stops_verified = False
        if result.status != "completed" or result.returncode != 0 or not result.stopped:
            raise ValueError("preference canary process failed; original records retained")
        observations[name] = _decode(result.stdout)
        return observations[name]

    failure = None
    try:
        if run("absent", "read")["present"]:
            raise ValueError("random canary key already exists; refusing to seed")
        seed_attempted = True
        if run("seed", "seed") != {"present": 1, "visible": 1, "synchronized": 1}:
            raise ValueError("synthetic canary could not be synchronized")
        if run("control", "read", private_home=True) != {
            "present": 1,
            "visible": 1,
            "synchronized": -1,
        }:
            raise ValueError("private-home unsandboxed control cannot see the canary")
        run("sandbox", "read", sandbox=True, private_home=True)
    except (ValueError, OSError) as error:
        failure = type(error).__name__ + ": " + str(error)
    finally:
        # Cleanup only the bound owned key. The C helper refuses to clear a
        # present value that differs from this run's canary.
        try:
            if seed_attempted:
                run("cleanup", "clear")
                run("after", "read")
        except (ValueError, OSError) as error:
            failure = (failure or "") + " cleanup: " + type(error).__name__ + ": " + str(error)
    cleaned = (
        stops_verified
        and observations.get("cleanup") == {"present": 0, "visible": 0, "synchronized": 1}
        and observations.get("after", {}).get("present") == 0
    )
    empty_file_removed = False
    flush = None
    if cleaned:
        try:
            flush = _wait_remove_empty_domain(preference_file.parent, domain, marker)
            empty_file_removed = flush["removed"]
        except (ValueError, OSError) as error:
            failure = (failure or "") + " empty storage cleanup: " + str(error)
    controls = observations.get("control", {}).get("visible") == 1
    denied = observations.get("sandbox") == {"present": 0, "visible": 0, "synchronized": -1}
    summary = {
        "schema": "claude-owned-preference-service-probe-v1",
        "source_identity": host_source_identity(),
        "policy_version": VERSION,
        "domain": domain,
        "observations": observations,
        "failure": failure,
        "controls_valid": controls,
        "owned_stops_verified": stops_verified,
        "seed_attempted": seed_attempted,
        "canary_key_removed": cleaned,
        "empty_preference_file_removed": empty_file_removed,
        "storage_cleanup": flush,
        "preference_file_remains": preference_file.exists(),
        "canary_not_visible_under_policy": bool(
            controls and denied and cleaned and failure is None
        ),
        "scope": "one owned synthetic user domain; not workspace or shared-memory qualification",
        "executable_substituted": True,
        "actual_client_started": False,
        "host_qualified": False,
        "provider_calls": 0,
        "real_credentials_opened": False,
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "binary_sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
        "policy_sha256": hashlib.sha256(policy.read_bytes()).hexdigest(),
    }
    durable_write(output / "summary.json", json.dumps(summary, indent=2).encode() + b"\n")
    return summary


def reconcile_cleanup(output: Path, *, expected_scope_sha256: str):
    """Read original stopped processes and remove only the bound empty test file."""
    sha256(expected_scope_sha256)
    root = Path(output).absolute()
    if any(p.is_symlink() for p in (root, *root.parents)):
        raise ValueError("cleanup root must not be symlinked")

    def record(name, limit):
        path = confined_file(root, name)
        if path.stat().st_size > limit:
            raise ValueError("cleanup metadata exceeds bound")
        raw = path.read_bytes()
        return raw, unique_json(raw.decode())

    raw, scope = record("scope.json", 1024)
    if hashlib.sha256(raw).hexdigest() != expected_scope_sha256 or set(scope) != {
        "domain",
        "marker",
    }:
        raise ValueError("cleanup scope differs from trusted pin")
    domain, marker = scope["domain"], scope["marker"]
    _validate_domain(domain, marker)
    summary_raw, original = record("summary.json", 65536)
    if (
        original.get("schema") != "claude-owned-preference-service-probe-v1"
        or original.get("domain") != domain
        or original.get("source_identity") != host_source_identity()
        or original.get("owned_stops_verified") is not True
        or original.get("canary_key_removed") is not True
    ):
        raise ValueError("original canary cleanup is not bound to stopped current sources")
    for name, field in (
        ("code/probe.c", "source_sha256"),
        ("code/probe", "binary_sha256"),
        ("policy.sb", "policy_sha256"),
    ):
        if hashlib.sha256(confined_file(root, name).read_bytes()).hexdigest() != original[field]:
            raise ValueError("original cleanup probe input changed")
    if (root / "code/probe.c").read_bytes() != SOURCE.encode():
        raise ValueError("original cleanup probe differs from fixed source")
    expected = {
        "absent": {"present": 0, "visible": 0, "synchronized": -1},
        "seed": {"present": 1, "visible": 1, "synchronized": 1},
        "control": {"present": 1, "visible": 1, "synchronized": -1},
        "sandbox": {"present": 0, "visible": 0, "synchronized": -1},
        "cleanup": {"present": 0, "visible": 0, "synchronized": 1},
        "after": {"present": 0, "visible": 0, "synchronized": -1},
    }
    real_home = str(Path.home().resolve())
    for name, mode in (
        ("absent", "read"),
        ("seed", "seed"),
        ("control", "read"),
        ("sandbox", "read"),
        ("cleanup", "clear"),
        ("after", "read"),
    ):
        process = recover_completed_process(
            root / name, nonce="preference-" + name, max_output_bytes=8192
        )
        command = [str(root / "code/probe"), mode, domain, marker]
        if name == "sandbox":
            command = ["/usr/bin/sandbox-exec", "-f", str(root / "policy.sb"), *command]
        _, job = record(name + "/job.json", 16384)
        if (
            job
            != {
                "command": command,
                "cwd": str(root / "workspace"),
                "environment": {
                    "PATH": "/usr/bin:/bin",
                    "LANG": "C.UTF-8",
                    "HOME": str(root / "home") if name in ("control", "sandbox") else real_home,
                },
                "keep_group_leader": True,
                "owner_lease": "pipe-eof-v1",
            }
            or process.status != "completed"
            or process.returncode != 0
            or not process.stopped
            or _decode(process.stdout) != expected[name]
            or original["observations"].get(name) != expected[name]
        ):
            raise ValueError("original preference control, cleanup or process binding differs")
    # No new CFPreferences call. The previously cleared domain is now inspected
    # only through its own bounded empty file, never another application domain.
    flush = _wait_remove_empty_domain(Path(real_home) / "Library/Preferences", domain, marker)
    path = Path(real_home) / "Library/Preferences" / (domain + ".plist")
    receipt = {
        "schema": "owned-preference-cleanup-reconciliation-v1.1",
        "scope_sha256": expected_scope_sha256,
        "original_summary_sha256": hashlib.sha256(summary_raw).hexdigest(),
        "domain": domain,
        "storage_cleanup": flush,
        "preference_file_remains": path.exists(),
        "canary_not_visible_under_policy": not path.exists(),
        "new_probe_process_starts": 0,
        "process_observation_subprocesses": "used_by_original_watchdog_verifier",
        "new_preference_calls": 0,
        "host_qualified": False,
    }
    directory = root / "cleanup-reconciliations"
    directory.mkdir(mode=0o700, exist_ok=True)
    count = len(list(directory.glob("*.json")))
    if count >= 16:
        raise ValueError("cleanup reconciliation record bound exhausted")
    durable_write(
        directory / f"{count + 1:06d}.json", json.dumps(receipt, indent=2).encode() + b"\n"
    )
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cleanup", action="store_true")
    parser.add_argument("--expected-scope-sha256")
    args = parser.parse_args()
    if args.cleanup and not args.expected_scope_sha256:
        parser.error("cleanup requires the original caller-pinned scope digest")
    if not args.cleanup and args.expected_scope_sha256:
        parser.error("a scope pin is valid only for cleanup")
    report = (
        reconcile_cleanup(args.output, expected_scope_sha256=args.expected_scope_sha256)
        if args.cleanup
        else probe(args.output)
    )
    print(json.dumps(report, indent=2))
    if not report["canary_not_visible_under_policy"]:
        raise SystemExit(1)
