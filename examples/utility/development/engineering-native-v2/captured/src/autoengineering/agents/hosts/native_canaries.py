"""Synthetic syscall checks for the fixed macOS policy, without a provider.

The probe substitutes its own executable for the native CLI's executable literal.
It measures policy permissions only. It cannot qualify native behavior, preference
service privacy, production credentials or a complete host profile.
"""

from __future__ import annotations

from dataclasses import asdict
import ctypes
import errno
import hashlib
import mmap
import os
from pathlib import Path
import plistlib
import re
import socket
import subprocess
import sys
import threading
import uuid

from autoengineering.agents.identity import host_source_identity
from autoengineering.agents.process import (
    recover_completed_process,
    recover_watchdog_stop,
    supervise_process,
)
from autoengineering.campaign.artifacts import confined_file, put_bytes, read_bytes
from autoengineering.campaign.records import ArtifactRef, sha256
from autoengineering.campaign.serialization import canonical_json, unique_json
from autoengineering.campaign.store import checked_directory, durable_write

from .native_policy import render_native_policy
from .native_profile import boundary_source_identity, native_runtime

VERSION = "native-policy-canaries-1.3"
PREFERENCE_CANARY = "synthetic preference canary"
SHM_CANARY = b"synthetic shared-memory canary"
UNVERIFIED = [
    "native_cli_behavior",
    "preference_service_privacy",
    "native_lifecycle",
    "host_profile_qualification",
]
FIELDS = (
    "private_read_denied",
    "checkout_read_denied",
    "evaluator_read_denied",
    "cache_read_denied",
    "lease_read_denied",
    "outside_write_denied",
    "allowed_read_succeeded",
    "workspace_write_denied",
    "home_write_succeeded",
    "symlink_read_denied",
    "symlink_write_denied",
    "endpoint_allowed",
    "unapproved_tcp_denied",
    "unapproved_unix_denied",
    "unapproved_exec_denied",
    "private_preference_read_denied",
    "workspace_preference_read_denied",
    "unapproved_preference_shm_denied",
    "process_environment_read_denied",
)
SOURCE = r"""
#include <arpa/inet.h>
#include <dlfcn.h>
#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/mman.h>
#include <sys/sysctl.h>
#include <sys/un.h>
#include <sys/wait.h>
#include <unistd.h>

static int denied(int rc) {
    int saved = errno;
    if (rc >= 0) close(rc);
    return rc < 0 && (saved == EACCES || saved == EPERM);
}
static int opened(const char *path, int flags) {
    int fd = open(path, flags, 0600);
    if (fd < 0) return 0;
    close(fd);
    return 1;
}
static int allowed_read(const char *path) {
    const char *expected = "approved native probe brief\n";
    char value[128] = {0};
    int fd = open(path, O_RDONLY);
    if (fd < 0) return 0;
    ssize_t count = read(fd, value, sizeof(value));
    close(fd);
    return count == (ssize_t)strlen(expected) && !memcmp(value, expected, count);
}
/* Return 1 for connected, 0 for denied, and -1 for an invalid control. */
static int connected(int family, int port, const char *path) {
    int fd = socket(family, SOCK_STREAM, 0);
    if (fd < 0) return -1;
    fcntl(fd, F_SETFL, O_NONBLOCK);
    int rc;
    if (family == AF_INET) {
        struct sockaddr_in address = {0};
        address.sin_family = AF_INET;
        address.sin_port = htons(port);
        address.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
        rc = connect(fd, (struct sockaddr *)&address, sizeof(address));
    } else {
        struct sockaddr_un address = {0};
        address.sun_family = AF_UNIX;
        if (strlen(path) >= sizeof(address.sun_path)) { close(fd); return -1; }
        strcpy(address.sun_path, path);
        rc = connect(fd, (struct sockaddr *)&address, sizeof(address));
    }
    int saved = errno;
    if (rc < 0 && saved == EINPROGRESS) {
        struct pollfd wait = {fd, POLLOUT, 0};
        if (poll(&wait, 1, 1000) != 1) { close(fd); return -1; }
        socklen_t size = sizeof(saved);
        if (getsockopt(fd, SOL_SOCKET, SO_ERROR, &saved, &size)) {
            close(fd); return -1;
        }
        rc = saved == 0 ? 0 : -1;
    }
    close(fd);
    return rc == 0 ? 1 : (saved == EACCES || saved == EPERM ? 0 : -1);
}
static int denied_exec(void) {
    pid_t child = fork();
    if (child < 0) return 0;
    if (!child) {
        char *const args[] = {"/usr/bin/true", NULL};
        execv(args[0], args);
        _exit(errno == EACCES || errno == EPERM ? 123 : 124);
    }
    int status;
    if (waitpid(child, &status, 0) != child) return 0;
    return WIFEXITED(status) && WEXITSTATUS(status) == 123;
}
/* Public CoreFoundation APIs, loaded dynamically so no extra link dependency
   enters the POSIX probes. Domains name only the two synthetic plist paths. */
static int preference_read(const char *domain_name) {
    void *library = dlopen("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation", RTLD_NOW);
    if (!library) return -1;
    void *(*string)(void *, const char *, unsigned int) = dlsym(library, "CFStringCreateWithCString");
    void *(*copy)(void *, void *, void *, void *) = dlsym(library, "CFPreferencesCopyValue");
    unsigned char (*equal)(void *, void *) = dlsym(library, "CFEqual");
    void (*release)(void *) = dlsym(library, "CFRelease");
    void **current = dlsym(library, "kCFPreferencesCurrentUser");
    void **any = dlsym(library, "kCFPreferencesAnyHost");
    if (!string || !copy || !equal || !release || !current || !any) return -1;
    void *key = string(NULL, "Canary", 0x08000100);
    void *domain = string(NULL, domain_name, 0x08000100);
    void *expected = string(NULL, "synthetic preference canary", 0x08000100);
    if (!key || !domain || !expected) return -1;
    void *value = copy(key, domain, *current, *any);
    int result = value ? (equal(value, expected) ? 1 : -1) : 0;
    if (value) release(value);
    release(expected); release(domain); release(key);
    dlclose(library);
    return result;
}
static int shared_memory_denied(const char *name) {
    int fd = shm_open(name, O_RDONLY, 0);
    if (fd < 0) {
        if (errno == EACCES || errno == EPERM) {
            fprintf(stderr, "synthetic shm open denied: %d\n", errno);
            return 1;
        }
        _exit(4);  /* A missing or broken fixture cannot establish denial. */
    }
    size_t size = strlen("synthetic shared-memory canary");
    char *bytes = mmap(NULL, size, PROT_READ, MAP_SHARED, fd, 0);
    int saved = errno;
    close(fd);
    if (bytes == MAP_FAILED) {
        if (saved == EACCES || saved == EPERM) {
            fprintf(stderr, "synthetic shm map denied: %d\n", saved);
            return 1;
        }
        _exit(4);
    }
    int matched = !memcmp(bytes, "synthetic shared-memory canary", size);
    munmap(bytes, size);
    if (!matched) _exit(3);
    return 0;
}
static int environment_denied(const char *pid) {
    int name[] = {CTL_KERN, KERN_PROCARGS2, atoi(pid)};
    size_t size = 0;
    if (sysctl(name, 3, NULL, &size, NULL, 0)) {
        if (errno == EACCES || errno == EPERM) return 1;
        _exit(5);
    }
    if (!size || size > 1048576) _exit(5);
    char *bytes = calloc(size, 1);
    if (!bytes) _exit(5);
    if (sysctl(name, 3, bytes, &size, NULL, 0)) {
        int saved = errno;
        free(bytes);
        if (saved == EACCES || saved == EPERM) return 1;
        _exit(5);
    }
    const char *expected = "AE_NATIVE_QUAL_ENV=synthetic-environment-canary";
    int found = 0;
    for (size_t i = 0; i + strlen(expected) <= size; i++) {
        if (!memcmp(bytes + i, expected, strlen(expected))) { found = 1; break; }
    }
    free(bytes);
    if (!found) _exit(5);
    return 0;
}
int main(int argc, char **argv) {
    if (argc != 19) return 2;
    int values[19];
    for (int i = 0; i < 5; i++) values[i] = denied(open(argv[i+1], O_RDONLY));
    values[5] = denied(open(argv[6], O_WRONLY | O_CREAT, 0600));
    values[6] = allowed_read(argv[7]);
    values[7] = denied(open(argv[8], O_WRONLY | O_CREAT, 0600));
    values[8] = opened(argv[9], O_WRONLY | O_CREAT);
    values[9] = denied(open(argv[10], O_RDONLY));
    values[10] = denied(open(argv[11], O_WRONLY));
    values[11] = connected(AF_INET, atoi(argv[12]), NULL) == 1;
    values[12] = connected(AF_INET, atoi(argv[13]), NULL) == 0;
    values[13] = connected(AF_UNIX, 0, argv[14]) == 0;
    values[14] = denied_exec();
    values[15] = preference_read(argv[15]) == 0;
    values[16] = preference_read(argv[16]) == 0;
    values[17] = shared_memory_denied(argv[17]);
    values[18] = environment_denied(argv[18]);
    printf("[");
    for (int i = 0; i < 19; i++) printf("%s%s", i ? "," : "", values[i] ? "true" : "false");
    printf("]\n");
    return 0;
}
"""


class _SharedCanary:
    """Own exactly one synthetic object. Never enumerate or read real objects."""

    def __init__(self):
        self.name = "apple.cfprefs.ae." + uuid.uuid4().hex[:8]
        self.unlinked = False
        self.library = ctypes.CDLL(None, use_errno=True)
        # shm_open is variadic. On Apple ARM64, declaring mode as fixed sends
        # it in the wrong ABI location and can create unpredictable permissions.
        self.library.shm_open.argtypes = [ctypes.c_char_p, ctypes.c_int]
        self.library.shm_open.restype = ctypes.c_int
        self.library.shm_unlink.argtypes = [ctypes.c_char_p]
        self.library.shm_unlink.restype = ctypes.c_int
        fd = self.library.shm_open(
            self.name.encode(), os.O_CREAT | os.O_EXCL | os.O_RDWR, ctypes.c_uint(0o600)
        )
        if fd < 0:
            raise ValueError("synthetic shared-memory creation failed")
        try:
            os.ftruncate(fd, len(SHM_CANARY))
            with mmap.mmap(fd, len(SHM_CANARY)) as view:
                view[:] = SHM_CANARY
        except BaseException:
            self.close()
            raise
        finally:
            os.close(fd)

    def close(self):
        self.unlinked = self.library.shm_unlink(self.name.encode()) == 0
        return self.unlinked

    @staticmethod
    def absent(name):
        if type(name) is not str or re.fullmatch(r"apple\.cfprefs\.ae\.[0-9a-f]{8}", name) is None:
            raise ValueError("invalid synthetic shared-memory name")
        library = ctypes.CDLL(None, use_errno=True)
        library.shm_open.argtypes = [ctypes.c_char_p, ctypes.c_int]
        library.shm_open.restype = ctypes.c_int
        fd = library.shm_open(name.encode(), os.O_RDONLY, ctypes.c_uint(0))
        if fd >= 0:
            os.close(fd)
            return False
        return ctypes.get_errno() == errno.ENOENT


class _Listener:
    def __init__(self, path=None):
        self.socket = socket.socket(socket.AF_UNIX if path else socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.socket.bind(str(path) if path else ("127.0.0.1", 0))
            self.socket.listen(4)
            self.socket.settimeout(0.05)
        except BaseException:
            self.socket.close()
            raise
        self.port = None if path else self.socket.getsockname()[1]
        self.accepted = 0
        self.closed = threading.Event()
        self.thread = threading.Thread(target=self._serve, daemon=True)
        self.thread.start()

    def _serve(self):
        while not self.closed.is_set():
            try:
                connection, _ = self.socket.accept()
            except TimeoutError:
                continue
            except OSError:
                return
            with connection:
                self.accepted += 1

    def close(self):
        self.closed.set()
        self.socket.close()
        self.thread.join(timeout=1)
        return not self.thread.is_alive()


class _EnvironmentCanary:
    """A direct owned child with only an explicit synthetic environment."""

    def __init__(self):
        self.process = subprocess.Popen(
            (sys.executable, "-I", "-S", "-B", "-c", "import time; time.sleep(30)"),
            env={"PATH": "/usr/bin:/bin", "AE_NATIVE_QUAL_ENV": "synthetic-environment-canary"},
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def close(self):
        if self.process.poll() is None:
            self.process.terminate()
        self.process.wait(timeout=2)
        return self.process.returncode is not None


def decode_observations(raw: bytes):
    values = unique_json(raw.decode())
    if (
        not isinstance(values, list)
        or len(values) != len(FIELDS)
        or any(type(value) is not bool for value in values)
    ):
        raise ValueError("invalid native canary output")
    return dict(zip(FIELDS, values, strict=True))


def _arguments(root, allowed_port, forbidden_port, shared_name, environment_pid):
    private, workspace, home = (root / name for name in ("private", "workspace", "home"))
    return (
        *(private / name for name in ("labels", "checkout", "evaluator", "cache", "lease")),
        private / "write-marker",
        workspace / "brief.txt",
        workspace / "write-marker",
        home / "write-marker",
        workspace / "linked-private",
        home / "linked-private",
        allowed_port,
        forbidden_port,
        root / "u.sock",
        private / "prefs",
        workspace / "prefs",
        shared_name,
        environment_pid,
    )


def _control_expected():
    return {
        name: name
        in (
            "allowed_read_succeeded",
            "home_write_succeeded",
            "endpoint_allowed",
        )
        for name in FIELDS
    }


def _metadata(result):
    return asdict(result) | {"stdout": None, "stderr": None}


def _local(root, name, limit=65536):
    path = confined_file(root, name)
    if path.stat().st_size > limit:
        raise ValueError("native canary file exceeds its size limit")
    return path.read_bytes()


def probe_native_policy(output: Path, *, compiler: Path = Path("/usr/bin/clang")):
    """Compile trusted canaries and measure one exact rendered policy.

    Only synthetic files and local sockets are touched. The executable literal
    differs from a native CLI policy, and that substitution is recorded. This
    produces partial permission evidence, never a qualified host manifest.
    """
    if sys.platform != "darwin":
        raise ValueError("native policy probe requires macOS")
    output = Path(output).absolute()
    checked_directory(output.parent)
    compiler = confined_file(compiler.parent, compiler.name)
    if len(str(output / "u.sock").encode()) > 100:
        raise ValueError("native policy probe needs a shorter output path for its Unix socket")
    output.mkdir(mode=0o700)
    for name in ("artifacts", "workspace", "home", "private"):
        (output / name).mkdir(mode=0o700)
    workspace, home, private = (output / name for name in ("workspace", "home", "private"))
    secrets = {
        name: f"synthetic-{name}-{uuid.uuid4().hex}".encode()
        for name in ("labels", "checkout", "evaluator", "cache", "lease")
    }
    for name, raw in secrets.items():
        durable_write(private / name, raw)
    preference_fixture = plistlib.dumps({"Canary": PREFERENCE_CANARY})
    for directory in (private, workspace):
        durable_write(directory / "prefs.plist", preference_fixture)
    durable_write(workspace / "brief.txt", b"approved native probe brief\n")
    (workspace / "linked-private").symlink_to(private / "labels")
    (home / "linked-private").symlink_to(private / "labels")
    source = output / "probe.c"
    durable_write(source, SOURCE.encode())
    environment = {"PATH": "/usr/bin:/bin", "LANG": "C", "HOME": str(home), "TMPDIR": str(home)}

    def run(name, command, seconds=5):
        return supervise_process(
            tuple(map(str, command)),
            directory=output / name,
            cwd=workspace,
            environment=environment,
            nonce="canary-" + uuid.uuid4().hex,
            stdin=b"",
            timeout_seconds=seconds,
            max_output_bytes=16384,
            on_launch=lambda _: None,
            parent_watchdog=True,
        )

    binary = output / "probe"
    listeners = []
    stopped = []
    shared = None
    environment_probe = None
    environment_stopped = False
    try:
        shared = _SharedCanary()
        environment_probe = _EnvironmentCanary()
        print("Compiling trusted native policy canaries", flush=True)
        compiled = run(
            "compile", (compiler, "-Wall", "-Wextra", "-Werror", "-o", binary, source), 30
        )
        if compiled.status != "completed" or not compiled.stopped:
            raise ValueError("native canary compilation failed; saved process evidence is retained")
        allowed = _Listener()
        listeners.append(allowed)
        forbidden = _Listener()
        listeners.append(forbidden)
        unix = _Listener(output / "u.sock")
        listeners.append(unix)
        policy = output / "policy.sb"
        durable_write(policy, render_native_policy(workspace, home, binary, allowed.port).encode())
        arguments = _arguments(
            output, allowed.port, forbidden.port, shared.name, environment_probe.process.pid
        )
        print("Checking unrestricted positive controls", flush=True)
        control = run("control", (binary, *arguments))
        control_values = decode_observations(control.stdout)
        for path in (private / "write-marker", workspace / "write-marker"):
            path.unlink(missing_ok=True)
        print("Checking fixed macOS policy permissions", flush=True)
        confined = run("confined", ("/usr/bin/sandbox-exec", "-f", policy, binary, *arguments))
        observed = decode_observations(confined.stdout)
    finally:
        for listener in listeners:
            stopped.append(listener.close())
        if shared is not None:
            shared.close()
        if environment_probe is not None:
            environment_stopped = environment_probe.close()
    unchanged = all((private / name).read_bytes() == raw for name, raw in secrets.items())
    unchanged = unchanged and all(
        (directory / "prefs.plist").read_bytes() == preference_fixture
        for directory in (private, workspace)
    )
    no_exposure = all(
        secret not in result.stdout + result.stderr
        for secret in secrets.values()
        for result in (control, confined)
    )
    counts = {
        "allowed": allowed.accepted,
        "forbidden_tcp": forbidden.accepted,
        "forbidden_unix": unix.accepted,
    }
    passed = (
        control.status == confined.status == "completed"
        and control.stopped
        and confined.stopped
        and control_values == _control_expected()
        and all(observed.values())
        and counts == {"allowed": 2, "forbidden_tcp": 1, "forbidden_unix": 1}
        and all(stopped)
        and shared.unlinked
        and environment_stopped
        and unchanged
        and no_exposure
        and not (private / "write-marker").exists()
        and not (workspace / "write-marker").exists()
    )

    def artifact(raw, name, media_type):
        return put_bytes(
            output, raw, name=name, media_type=media_type, producer="native-canaries"
        ).to_dict()

    receipt = {
        "version": VERSION,
        "status": "passed" if passed else "failed",
        "host_qualified": False,
        "scope": "syscall-policy-canaries",
        "executable_substitution": True,
        "source_identity": host_source_identity(),
        "boundary_source_identity": boundary_source_identity(),
        "runtime": native_runtime(),
        "compiler": {
            "path": str(compiler),
            "sha256": hashlib.sha256(compiler.read_bytes()).hexdigest(),
        },
        "probe_sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
        "endpoints": {"allowed_port": allowed.port, "forbidden_port": forbidden.port},
        "shared_memory": {"name": shared.name, "unlinked": shared.unlinked},
        "environment_probe": {"pid": environment_probe.process.pid, "stopped": environment_stopped},
        "observed": observed,
        "control": control_values,
        "listener_connections": counts,
        "listeners_stopped": all(stopped),
        "private_canaries_unchanged": unchanged,
        "private_values_absent_from_output": no_exposure,
        "provider_calls": 0,
        "scientific_calls": 0,
        "real_credentials_used": False,
        "processes": {
            name: _metadata(result)
            for name, result in (
                ("compile", compiled),
                ("control", control),
                ("confined", confined),
            )
        },
        "artifacts": {
            "source": artifact(SOURCE.encode(), "probe.c", "text/x-c"),
            "policy": artifact(policy.read_bytes(), "policy.sb", "text/plain"),
            "control": artifact(control.stdout, "control.json", "application/json"),
            "observed": artifact(confined.stdout, "observed.json", "application/json"),
            "preferences": artifact(preference_fixture, "prefs.plist", "application/x-plist"),
        },
        "unverified": UNVERIFIED,
    }
    durable_write(output / "receipt.json", canonical_json(receipt).encode())
    return receipt


def recover_native_policy_probe(root: Path, *, expected_digest: str):
    """Check pinned partial evidence without compiling, starting or signalling."""
    sha256(expected_digest)
    root = checked_directory(root)
    raw = _local(root, "receipt.json")
    if hashlib.sha256(raw).hexdigest() != expected_digest:
        raise ValueError("native canary receipt differs from pinned evidence")
    value = unique_json(raw.decode())
    if (
        not isinstance(value, dict)
        or set(value)
        != {
            "version",
            "status",
            "host_qualified",
            "scope",
            "executable_substitution",
            "source_identity",
            "boundary_source_identity",
            "runtime",
            "compiler",
            "probe_sha256",
            "endpoints",
            "shared_memory",
            "environment_probe",
            "observed",
            "control",
            "listener_connections",
            "listeners_stopped",
            "private_canaries_unchanged",
            "private_values_absent_from_output",
            "provider_calls",
            "scientific_calls",
            "real_credentials_used",
            "processes",
            "artifacts",
            "unverified",
        }
        or value["version"] != VERSION
        or value["status"] not in ("passed", "failed")
        or value["host_qualified"] is not False
        or value["scope"] != "syscall-policy-canaries"
        or value["executable_substitution"] is not True
        or value["source_identity"] != host_source_identity()
        or value["boundary_source_identity"] != boundary_source_identity()
        or value["runtime"] != native_runtime()
        or value["unverified"] != UNVERIFIED
        or type(value["provider_calls"]) is not int
        or value["provider_calls"] != 0
        or type(value["scientific_calls"]) is not int
        or value["scientific_calls"] != 0
        or value["real_credentials_used"] is not False
    ):
        raise ValueError("native canary evidence is incomplete or incompatible")
    endpoints = value["endpoints"]
    if (
        set(endpoints) != {"allowed_port", "forbidden_port"}
        or any(type(port) is not int or not 0 < port < 65536 for port in endpoints.values())
        or endpoints["allowed_port"] == endpoints["forbidden_port"]
    ):
        raise ValueError("invalid native canary endpoint binding")
    compiler = Path(value["compiler"]["path"])
    if set(value["compiler"]) != {"path", "sha256"} or (
        hashlib.sha256(_local(compiler.parent, compiler.name, 1048576)).hexdigest()
        != value["compiler"]["sha256"]
    ):
        raise ValueError("native canary compiler changed")
    binary, source, policy = (root / name for name in ("probe", "probe.c", "policy.sb"))
    if hashlib.sha256(_local(root, "probe", 1048576)).hexdigest() != value["probe_sha256"]:
        raise ValueError("native canary executable changed")
    artifacts = value["artifacts"]
    if set(artifacts) != {"source", "policy", "control", "observed", "preferences"}:
        raise ValueError("native canary artifacts are incomplete")
    saved = {
        key: read_bytes(root, ArtifactRef.from_dict(ref), max_bytes=65536)
        for key, ref in artifacts.items()
    }
    if (
        saved["source"] != SOURCE.encode()
        or _local(root, "probe.c") != saved["source"]
        or saved["policy"]
        != render_native_policy(
            root / "workspace", root / "home", binary, endpoints["allowed_port"]
        ).encode()
        or _local(root, "policy.sb") != saved["policy"]
        or decode_observations(saved["control"]) != value["control"]
        or decode_observations(saved["observed"]) != value["observed"]
        or saved["preferences"] != plistlib.dumps({"Canary": PREFERENCE_CANARY})
        or _local(root, "private/prefs.plist") != saved["preferences"]
        or _local(root, "workspace/prefs.plist") != saved["preferences"]
    ):
        raise ValueError("native canary source, policy or observations changed")
    shared = value["shared_memory"]
    if (
        set(shared) != {"name", "unlinked"}
        or type(shared["name"]) is not str
        or re.fullmatch(r"apple\.cfprefs\.ae\.[0-9a-f]{8}", shared["name"]) is None
        or type(shared["unlinked"]) is not bool
    ):
        raise ValueError("invalid synthetic shared-memory binding")
    if not _SharedCanary.absent(shared["name"]):
        raise ValueError("synthetic shared-memory removal remains unverified")
    environment_probe = value["environment_probe"]
    if (
        set(environment_probe) != {"pid", "stopped"}
        or type(environment_probe["pid"]) is not int
        or environment_probe["pid"] <= 1
        or environment_probe["stopped"] is not True
    ):
        raise ValueError("invalid synthetic environment probe")
    arguments = _arguments(
        root,
        endpoints["allowed_port"],
        endpoints["forbidden_port"],
        shared["name"],
        environment_probe["pid"],
    )
    commands = {
        "compile": (compiler, "-Wall", "-Wextra", "-Werror", "-o", binary, source),
        "control": (binary, *arguments),
        "confined": ("/usr/bin/sandbox-exec", "-f", policy, binary, *arguments),
    }
    if set(value["processes"]) != set(commands):
        raise ValueError("native canary process evidence is incomplete")
    recovered = {}
    for name, command in commands.items():
        record = value["processes"][name]
        result = recover_completed_process(
            root / name, nonce=record["identity"]["nonce"], max_output_bytes=16384
        )
        recover_watchdog_stop(root / name)
        job = unique_json(confined_file(root, f"{name}/job.json").read_text())
        if (
            _metadata(result) != record
            or job["command"] != list(map(str, command))
            or job["cwd"] != str(root / "workspace")
            or job["environment"]
            != {
                "PATH": "/usr/bin:/bin",
                "LANG": "C",
                "HOME": str(root / "home"),
                "TMPDIR": str(root / "home"),
            }
            or (
                name in ("control", "confined")
                and result.stdout != saved["control" if name == "control" else "observed"]
            )
        ):
            raise ValueError("native canary process binding mismatch")
        recovered[name] = result
    counts = value["listener_connections"]
    if set(counts) != {"allowed", "forbidden_tcp", "forbidden_unix"} or any(
        type(count) is not int or count < 0 for count in counts.values()
    ):
        raise ValueError("invalid native canary listener counts")
    passed = (
        all(result.status == "completed" and result.stopped for result in recovered.values())
        and value["control"] == _control_expected()
        and all(value["observed"].values())
        and shared["unlinked"]
        and value["listener_connections"] == {"allowed": 2, "forbidden_tcp": 1, "forbidden_unix": 1}
        and all(
            value[name] is True
            for name in (
                "listeners_stopped",
                "private_canaries_unchanged",
                "private_values_absent_from_output",
            )
        )
        and not (root / "private/write-marker").exists()
        and not (root / "workspace/write-marker").exists()
    )
    if value["status"] != ("passed" if passed else "failed"):
        raise ValueError("native canary status contradicts saved evidence")
    return value
