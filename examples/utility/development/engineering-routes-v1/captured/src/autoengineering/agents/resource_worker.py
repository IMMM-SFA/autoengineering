"""Standalone trusted resource wrapper used inside the OS boundary."""

from __future__ import annotations

import argparse
import resource
import runpy
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cpu", required=True, type=int)
    parser.add_argument("--memory", required=True, type=int)
    parser.add_argument("--file-bytes", required=True, type=int)
    parser.add_argument("entrypoint")
    args = parser.parse_args()
    resource.setrlimit(resource.RLIMIT_CPU, (args.cpu, args.cpu))
    resource.setrlimit(resource.RLIMIT_FSIZE, (args.file_bytes, args.file_bytes))
    resource.setrlimit(resource.RLIMIT_NOFILE, (32, 32))
    resource.setrlimit(resource.RLIMIT_NPROC, (1, 1))
    # Darwin's address-space limit can be below the inherited shared-cache
    # mapping. Qualify the data limit with an actual allocation probe instead.
    kind = resource.RLIMIT_DATA if sys.platform == "darwin" else resource.RLIMIT_AS
    resource.setrlimit(kind, (args.memory, args.memory))
    sys.argv = [args.entrypoint]
    runpy.run_path(args.entrypoint, run_name="__main__")


if __name__ == "__main__":
    main()
