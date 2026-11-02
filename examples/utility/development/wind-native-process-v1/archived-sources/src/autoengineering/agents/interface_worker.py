"""Fixed interface driver, copied into a qualified container as driver.py.

Never run this file on the host with candidate code. The source path below is
the exact read-only container mount, not a worker-selected host path.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
import sys


def main():
    payload = json.loads(sys.stdin.buffer.read(65537))
    if set(payload) != {"schema_version", "inputs"} or payload["schema_version"] != "1.0":
        raise ValueError("invalid interface input envelope")
    namespace = {"__builtins__": __builtins__}
    source = Path("/work/adapter.py").read_bytes()
    exec(compile(source, "/work/adapter.py", "exec"), namespace)
    supplied = payload["inputs"]
    saved = copy.deepcopy(supplied)
    outputs = namespace["predict"](supplied)
    result = {"schema_version": "1.0", "outputs": outputs, "inputs_unchanged": supplied == saved}
    sys.stdout.write(json.dumps(result, allow_nan=False, separators=(",", ":")))


if __name__ == "__main__":
    main()
