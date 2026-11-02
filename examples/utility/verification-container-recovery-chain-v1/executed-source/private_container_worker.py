"""Fixed Linux scorer output boundary, staged as a standalone stdlib worker.

Only the hash-pinned RMSE worker or two fixed public output probes can run.
Both child output descriptors share one regular file with a hard file-size
limit. The parent exports bounded metadata, never a truncated child response.
This worker alone does not qualify a container or authorize private access.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import signal
import stat
import sys
import tempfile

OUTPUT_BYTES = 16384
WORKER_SHA256 = "6cd9d35cd7f0ce64c4ade853fb151566bae526f54628ac59beaef704a27d187d"
MODES = ("score", "output-small", "output-overrun")


def capture_fixed_worker(root: Path, mode: str) -> dict:
    if mode not in MODES:
        raise ValueError("unsupported fixed worker mode")
    worker = None
    if mode == "score":
        descriptor = os.open(
            root / "private_score_worker.py", os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
        )
        try:
            info = os.fstat(descriptor)
            if not stat.S_ISREG(info.st_mode) or info.st_size > 65536:
                raise ValueError("invalid fixed worker")
            worker = os.read(descriptor, 65537)
        finally:
            os.close(descriptor)
        if hashlib.sha256(worker).hexdigest() != WORKER_SHA256:
            raise ValueError("fixed worker hash differs")
    # The fd is never exposed to the model worker. This is an internal trusted
    # scorer process boundary, not a sandbox for arbitrary generated code.
    with tempfile.TemporaryFile(dir="/tmp") as output:
        pid = os.fork()
        if pid == 0:
            try:
                import resource

                resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
                resource.setrlimit(resource.RLIMIT_FSIZE, (OUTPUT_BYTES, OUTPUT_BYTES))
                signal.signal(signal.SIGXFSZ, signal.SIG_DFL)
                os.dup2(output.fileno(), 1)
                os.dup2(output.fileno(), 2)
                # Replace Python's inherited capture/buffering objects as well
                # as OS descriptors. The worker cannot retain a StringIO route.
                _previous_output = (sys.stdout, sys.stderr)
                sys.stdout = io.TextIOWrapper(io.FileIO(1, "w", closefd=False), write_through=True)
                sys.stderr = io.TextIOWrapper(io.FileIO(2, "w", closefd=False), write_through=True)
                null = os.open("/dev/null", os.O_RDONLY)
                os.dup2(null, 0)
                max_fds = resource.getrlimit(resource.RLIMIT_NOFILE)[0]
                if not 3 <= max_fds <= 1048576:
                    os._exit(70)
                os.closerange(3, max_fds)
                os.environ.clear()
                if mode == "output-small":
                    os.write(1, b"x" * 4096)
                elif mode == "output-overrun":
                    # Exercise both descriptors against the same aggregate cap.
                    os.write(1, b"x" * OUTPUT_BYTES)
                    os.write(2, b"y")
                else:
                    sys.argv = ["private_score_worker.py"]
                    exec(
                        compile(worker, "fixed-private-rmse-worker", "exec"),
                        {
                            "__name__": "__main__",
                            "__file__": str(root / "private_score_worker.py"),
                        },
                    )
                    sys.stdout.flush()
                    sys.stderr.flush()
                os._exit(0)
            except BaseException:
                os._exit(70)  # No exception, path or private value is exported.
        _, status = os.waitpid(pid, 0)
        output.seek(0)
        raw = output.read(OUTPUT_BYTES + 1)
    signum = os.WTERMSIG(status) if os.WIFSIGNALED(status) else None
    exit_code = os.WEXITSTATUS(status) if os.WIFEXITED(status) else None
    limited = len(raw) >= OUTPUT_BYTES or signum == signal.SIGXFSZ
    result = {
        "schema": "private-container-output-v1",
        "mode": mode,
        "output_limit_bytes": OUTPUT_BYTES,
        "captured_bytes": len(raw),
        "child_signal": signum,
        "child_exit_code": exit_code,
        "output_limited": limited,
        "private_scoring_qualified": False,
    }
    if mode == "score":
        # A limit hit never becomes a score, even if its prefix is valid JSON.
        result["score"] = json.loads(raw) if exit_code == 0 and not limited else None
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=MODES)
    args = parser.parse_args(argv)
    if sys.platform != "linux" or (os.geteuid(), os.getegid()) != (65534, 65534):
        print('{"status":"refused","private_scoring_qualified":false}')
        return 2
    signal.signal(signal.SIGALRM, lambda *_: os._exit(124))
    signal.alarm(10)
    try:
        result = capture_fixed_worker(Path(__file__).parent, args.mode)
        print(json.dumps(result, allow_nan=False, sort_keys=True), flush=True)
        return 0
    except Exception:
        print('{"status":"refused","private_scoring_qualified":false}', flush=True)
        return 2
    finally:
        signal.alarm(0)


if __name__ == "__main__":
    raise SystemExit(main())
