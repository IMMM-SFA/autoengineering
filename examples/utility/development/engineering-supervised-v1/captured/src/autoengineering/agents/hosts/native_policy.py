"""Fixed macOS boundary for the credentialless, tool-free native client."""

from __future__ import annotations

import json
from pathlib import Path
import sys

from autoengineering.campaign.artifacts import confined_file
from autoengineering.campaign.store import checked_directory


def render_native_policy(workspace: Path, home: Path, executable: Path, port: int) -> str:
    if sys.platform != "darwin" or type(port) is not int or not 0 < port < 65536:
        raise ValueError("unsupported native boundary platform or endpoint")
    workspace, home = checked_directory(workspace), checked_directory(home)
    executable = confined_file(executable.parent, executable.name)
    requirements = Path("/etc/codex/requirements.toml").resolve()
    if requirements.exists() or requirements.is_symlink():
        raise ValueError("native profile requires absent system requirements")
    trees = (Path("/usr/lib"), Path("/System/Library"), workspace, home)
    literals = (
        executable,
        Path("/"),
        Path("/dev/null"),
        Path("/dev/random"),
        Path("/dev/urandom"),
        Path("/private/etc/ssl/openssl.cnf"),
        Path("/etc"),
        requirements,
    )
    metadata = sorted({str(parent) for path in (*trees, *literals) for parent in path.parents})

    def quote(path):
        return json.dumps(str(path), ensure_ascii=True)

    return (
        "\n".join(
            (
                "(version 1)",
                "(deny default)",
                "(deny process-info*)",
                "(allow process-info* (target self))",
                '(allow sysctl-read (sysctl-name-prefix "hw.") (sysctl-name "kern.osrelease") (sysctl-name "kern.osversion") (sysctl-name "kern.ostype") (sysctl-name "kern.osproductversion"))',
                "(allow process-fork)",
                f"(allow process-exec (literal {quote(executable)}))",
                "(allow file-read* "
                + " ".join(f"(subpath {quote(p)})" for p in trees)
                + " "
                + " ".join(f"(literal {quote(p)})" for p in literals)
                + ")",
                "(allow file-read-metadata "
                + " ".join(f"(literal {quote(p)})" for p in metadata)
                + ")",
                f'(allow file-write* (subpath {quote(home)}) (literal "/dev/null"))',
                f'(allow network-outbound (remote ip "localhost:{port}"))',
            )
        )
        + "\n"
    )
