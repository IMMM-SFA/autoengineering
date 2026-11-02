"""Measure a candidate macOS policy with synthetic syscalls and CLI help only."""

from __future__ import annotations

import argparse
from contextlib import ExitStack
from dataclasses import replace
import hashlib
import json
import platform
import shlex
from pathlib import Path
import socket
import subprocess
import sys
import threading

from autoengineering.agents.hosts.claude import inspect_claude, execute_claude_transport
from autoengineering.agents.hosts.claude_policy import (
    ClaudeEgress,
    ClaudePolicy,
    VERSION,
    render_claude_policy,
)
from autoengineering.agents.identity import host_source_identity
from autoengineering.agents.process import supervise_process
from autoengineering.campaign.serialization import unique_json

FIELDS = (
    "allowed_read",
    "private_read_denied",
    "credential_read",
    "outside_write_denied",
    "home_write",
    "workspace_write_denied",
    "symlink_read_denied",
    "symlink_write_denied",
    "hardlink_read_denied",
    "endpoint_allowed",
    "other_tcp_denied",
    "unix_denied",
    "exec_denied",
    "checkout_read_denied",
)

SOURCE = r"""
#include <arpa/inet.h>
#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <sys/wait.h>
#include <unistd.h>
static int read_ok(const char *p) { int f=open(p,O_RDONLY); if(f<0)return 0;close(f);return 1; }
static int read_denied(const char *p) { int f=open(p,O_RDONLY);int e=errno;if(f>=0)close(f);return f<0&&(e==EPERM||e==EACCES); }
static int write_ok(const char *p) {int f=open(p,O_WRONLY|O_CREAT,0600);if(f<0)return 0;close(f);return 1;}
static int write_denied(const char *p) {int f=open(p,O_WRONLY|O_CREAT,0600);int e=errno;if(f>=0)close(f);return f<0&&(e==EPERM||e==EACCES);}
static int connect_result(int family,int port,const char *path) {
 int f=socket(family,SOCK_STREAM,0);if(f<0)return -1;fcntl(f,F_SETFL,O_NONBLOCK);int r;
 if(family==AF_INET){struct sockaddr_in a={0};a.sin_family=family;a.sin_port=htons(port);a.sin_addr.s_addr=htonl(INADDR_LOOPBACK);r=connect(f,(struct sockaddr*)&a,sizeof(a));}
 else {struct sockaddr_un a={0};a.sun_family=family;if(strlen(path)>=sizeof(a.sun_path)){close(f);return -1;}strcpy(a.sun_path,path);r=connect(f,(struct sockaddr*)&a,sizeof(a));}
 int e=errno;if(r<0&&e==EINPROGRESS){struct pollfd p={f,POLLOUT,0};if(poll(&p,1,1000)!=1){close(f);return -1;}socklen_t z=sizeof(e);if(getsockopt(f,SOL_SOCKET,SO_ERROR,&e,&z)){close(f);return -1;}r=e==0?0:-1;}
 close(f);return r==0?1:(e==EPERM||e==EACCES?0:-1);
}
static int exec_denied(void){pid_t p=fork();if(p<0)return -1;if(!p){execl("/usr/bin/true","true",NULL);_exit(errno==EPERM||errno==EACCES?77:78);}int s;if(waitpid(p,&s,0)<0)return -1;return WIFEXITED(s)&&WEXITSTATUS(s)==77;}
int main(int n,char **a){if(n!=14)return 2;
 int linked=link(a[2],a[9]);int saved=errno;
 int hardlink_denied=linked<0&&(saved==EPERM||saved==EACCES);
 if(linked==0)hardlink_denied=read_denied(a[9]);
 printf("{\"allowed_read\":%d,\"private_read_denied\":%d,\"credential_read\":%d,\"outside_write_denied\":%d,\"home_write\":%d,\"workspace_write_denied\":%d,\"symlink_read_denied\":%d,\"symlink_write_denied\":%d,\"hardlink_read_denied\":%d,\"endpoint_allowed\":%d,\"other_tcp_denied\":%d,\"unix_denied\":%d,\"exec_denied\":%d,\"checkout_read_denied\":%d}\n",
 read_ok(a[1]),read_denied(a[2]),read_ok(a[3]),write_denied(a[4]),write_ok(a[5]),write_denied(a[6]),read_denied(a[7]),write_denied(a[8]),hardlink_denied,connect_result(AF_INET,atoi(a[10]),"")==1,connect_result(AF_INET,atoi(a[11]),"")==0,connect_result(AF_UNIX,0,a[12])==0,exec_denied(),read_denied(a[13]));return 0;}
"""


class Listener:
    def __init__(self, path=None):
        self.socket = socket.socket(socket.AF_UNIX if path else socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind(str(path) if path else ("127.0.0.1", 0))
        self.socket.listen(4)
        self.socket.settimeout(0.1)
        self.port = None if path else self.socket.getsockname()[1]
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self.serve, daemon=True)
        self.thread.start()

    def serve(self):
        while not self.stop.is_set():
            try:
                connection, _ = self.socket.accept()
                connection.close()
            except socket.timeout:
                pass
            except OSError:
                break

    def close(self):
        self.stop.set()
        self.socket.close()
        self.thread.join(2)
        assert not self.thread.is_alive()


def probe(output: Path, executable: Path):
    output = output.absolute()
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    for name in ("workspace", "home", "private", "auth", "code"):
        (output / name).mkdir(mode=0o700)
    brief = output / "workspace/brief.txt"
    brief.write_text("synthetic approved packet\n")
    private = output / "private/labels.txt"
    private.write_text("synthetic private label\n")
    key = output / "auth/key.txt"
    key.write_text("synthetic authentication fixture\n")
    key.chmod(0o600)
    helper = output / "auth/helper"
    helper.write_text(
        f"#!{Path(sys.executable).resolve()}\nfrom pathlib import Path\nprint(Path({str(key)!r}).read_text().strip())\n"
    )
    helper.chmod(0o700)
    outside = output / "private/outside.txt"
    outside.write_text("synthetic outside write target\n")
    (output / "workspace/read-link").symlink_to(private)
    (output / "home/write-link").symlink_to(outside)
    source = output / "code/probe.c"
    source.write_text(SOURCE)
    binary = output / "code/probe"
    compiler = Path("/usr/bin/clang")
    compiled = subprocess.run(
        (str(compiler), "-std=c11", "-O0", str(source), "-o", str(binary)),
        capture_output=True,
        timeout=30,
    )
    (output / "compile.stdout").write_bytes(compiled.stdout)
    (output / "compile.stderr").write_bytes(compiled.stderr)
    if compiled.returncode:
        raise ValueError("synthetic canary compilation failed")
    inventory = inspect_claude(executable)
    results = {}
    with ExitStack() as stack:
        allowed, other, unix = Listener(), Listener(), Listener(output / "private/socket")
        for listener in (allowed, other, unix):
            stack.callback(listener.close)
        python = Path(sys.executable).resolve()
        spec = ClaudePolicy(
            VERSION,
            str(output / "workspace"),
            str(output / "home"),
            str(binary),
            str(helper),
            str(python),
            str(Path(sys.prefix).resolve()),
            (str(key),),
            (ClaudeEgress("localhost", allowed.port),),
            (str(output / "private"), str(Path.cwd().resolve())),
        )
        policy = output / "canary.sb"
        policy.write_text(render_claude_policy(spec))
        args = tuple(
            map(
                str,
                (
                    brief,
                    private,
                    key,
                    outside,
                    output / "home/allowed.txt",
                    output / "workspace/forbidden.txt",
                    output / "workspace/read-link",
                    output / "home/write-link",
                    output / "home/hardlink",
                    allowed.port,
                    other.port,
                    output / "private/socket",
                    Path.cwd() / "README.md",
                ),
            )
        )
        for name, command in (
            ("control", (str(binary), *args)),
            ("sandbox", ("/usr/bin/sandbox-exec", "-f", str(policy), str(binary), *args)),
        ):
            if name == "sandbox":
                (output / "home/hardlink").unlink(missing_ok=True)
                (output / "workspace/forbidden.txt").unlink(missing_ok=True)
            value = supervise_process(
                command,
                directory=output / name,
                cwd=output / "workspace",
                environment={"PATH": "/usr/bin:/bin"},
                nonce="claude-policy-" + name,
                stdin=b"",
                timeout_seconds=5,
                max_output_bytes=8192,
                on_launch=lambda _: None,
                parent_watchdog=True,
            )
            if value.status != "completed" or value.returncode != 0 or not value.stopped:
                raise ValueError("canary process failed; raw evidence retained")
            observed = unique_json(value.stdout.decode())
            if (
                not isinstance(observed, dict)
                or set(observed) != set(FIELDS)
                or any(type(v) is not int or v not in (0, 1) for v in observed.values())
            ):
                raise ValueError("canary output differs from fixed observation contract")
            results[name] = observed
        expected = {name: 1 for name in FIELDS}
        control = {name: (0 if name.endswith("_denied") else 1) for name in expected}
        assert results["control"] == control, "invalid unsandboxed control"
        assert results["sandbox"] == expected, "candidate policy canary failed"
        actual = replace(spec, executable=inventory.executable)
        actual_policy = output / "client.sb"
        actual_policy.write_text(render_claude_policy(actual))
        command = (
            "/usr/bin/sandbox-exec",
            "-f",
            str(actual_policy),
            inventory.executable,
            "--bare",
            "--tools=",
            "--setting-sources=",
            "--help",
        )
        value = supervise_process(
            command,
            directory=output / "client-help",
            cwd=output / "workspace",
            environment={"PATH": "/usr/bin:/bin", "HOME": str(output / "home"), "LANG": "C.UTF-8"},
            nonce="claude-policy-help",
            stdin=b"",
            timeout_seconds=10,
            max_output_bytes=65536,
            on_launch=lambda _: None,
            parent_watchdog=True,
        )
        results["actual_cli_help"] = {
            "status": value.status,
            "returncode": value.returncode,
            "stopped": value.stopped,
            "help_returned": b"Usage: claude" in value.stdout,
        }
        help_passed = (
            value.status == "completed"
            and value.returncode == 0
            and value.stopped
            and results["actual_cli_help"]["help_returned"]
        )

        # Ask the trusted builder for its exact non-secret helper verifier. The
        # wrapper aborts preparation before any Claude command is launched.
        class Prepared(Exception):
            pass

        captured = {}

        def prepare_only(command):
            captured["settings"] = unique_json(command[command.index("--settings") + 1])
            raise Prepared()

        schema = output / "workspace/helper-schema.json"
        schema.write_text('{"type":"object"}')
        try:
            execute_claude_transport(
                inventory,
                model="claude-fixture-1",
                schema=schema,
                helper=helper,
                helper_sha256=hashlib.sha256(helper.read_bytes()).hexdigest(),
                directory=output / "not-launched",
                workspace=output / "workspace",
                home=output / "home",
                nonce="prepare-helper-only",
                prompt=b"",
                timeout_seconds=1,
                max_output_bytes=1024,
                max_budget_usd=0.01,
                on_launch=lambda _: None,
                wrap_command=prepare_only,
            )
        except Prepared:
            pass
        assert not (output / "not-launched").exists()
        helper_command = tuple(shlex.split(captured["settings"]["apiKeyHelper"]))
        helper_result = supervise_process(
            ("/usr/bin/sandbox-exec", "-f", str(actual_policy), *helper_command),
            directory=output / "helper-proof",
            cwd=output / "workspace",
            environment={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "HOME": str(output / "home")},
            nonce="claude-policy-helper",
            stdin=b"",
            timeout_seconds=5,
            max_output_bytes=4096,
            on_launch=lambda _: None,
            parent_watchdog=True,
        )
        helper_passed = (
            helper_result.status == "completed"
            and helper_result.returncode == 0
            and helper_result.stopped
            and helper_result.stdout == b"synthetic authentication fixture\n"
        )
        results["synthetic_helper_bootstrap"] = {
            "status": helper_result.status,
            "returncode": helper_result.returncode,
            "stopped": helper_result.stopped,
            "expected_synthetic_output": helper_result.stdout
            == b"synthetic authentication fixture\n",
            "native_CLI_helper_hook_exercised": False,
        }
        passed = help_passed and helper_passed

    report = {
        "version": "claude-policy-probe-1.3",
        "status": "passed_limited_scope" if passed else "client_startup_failed",
        "source_identity": host_source_identity(),
        "runtime": {
            "platform": sys.platform,
            "machine": platform.machine(),
            "os_release": platform.release(),
            "os_version": platform.version(),
            "python": platform.python_version(),
        },
        "public_icu_files": {
            str(p): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in Path("/usr/share/icu").glob("*")
            if p.is_file()
        },
        "policy_specification": spec.to_dict(),
        "actual_cli_policy_specification": actual.to_dict(),
        "inventory": inventory.__dict__,
        "observed": results,
        "raw_source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "provider_calls": 0,
        "scientific_calls": 0,
        "production_admission": False,
        "unqualified": [
            "actual_inference_and_role_conformance",
            "real_credentials_and_authentication",
            "native_cli_helper_hook",
            "IPv6_and_UDP",
            "DNS_TLS_and_external_egress",
            "preference_service_and_shared_memory",
            "process_environment_privacy",
            "resource_and_workspace_limits",
            "complete_lifecycle_matrix",
            "Linux_x86_64",
        ],
    }
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        json.dumps({"status": report["status"], "observed": results, "production_admission": False})
    )
    if not passed:
        raise ValueError("actual CLI help startup failed; no production qualification")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--executable", type=Path, default=Path("/Users/cam/.local/bin/claude"))
    args = parser.parse_args()
    probe(args.output, args.executable)
