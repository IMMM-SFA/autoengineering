"""Local qualification policy; not an OS privacy boundary for untrusted code."""

import os
import sys

FORBIDDEN = "/Users/cam/projects/autoengineering"


def guard(event, args):
    if event == "open" and isinstance(args[0], (str, bytes)):
        path = os.path.abspath(os.fsdecode(args[0]))
        if path == FORBIDDEN or path.startswith(FORBIDDEN + os.sep):
            raise PermissionError("installed qualification denies original checkout access")
    if event in ("socket.__new__", "socket.connect"):
        raise PermissionError("installed qualification denies network sockets")


sys.addaudithook(guard)
