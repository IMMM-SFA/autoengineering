"""Fixed serial conformance protocol. No physical implementation imports."""

from .records import ResourceLimits
from autoengineering.campaign.serialization import digest

VERSION = "host-conformance-preparation-1.0"
POLICIES = (
    ("text", 1, 0, "structured response; resolved model and supplied usage recorded"),
    ("roles", 7, 2, "all four roles; expected synthetic decision; unchanged replay"),
    ("timeout", 1, 0, "owned timeout; stopped groups; unknown provider work retained"),
    ("cancel", 1, 0, "queued cancellation distinguished from verified stop"),
    (
        "owner_loss",
        1,
        0,
        "owned supervisor interruption before credential preflight; no replacement call",
    ),
    ("malformed", 2, 0, "invalid typed handoff rejected before science; at most one repair"),
)
PROTOCOL_DIGEST = digest({"version": VERSION, "cases": POLICIES})
LIMITS = ResourceLimits(16, 12, 2, 1, 720, 30, 1048576, 65536)
ROLE_LIMITS = ResourceLimits(7, 7, 0, 0, 720, 30, 1048576, 65536)
MALFORMED_LIMITS = ResourceLimits(2, 1, 1, 1, 720, 30, 1048576, 65536)
IMPLEMENTED_CASES = ("text", "roles", "timeout", "cancel", "owner_loss", "malformed")
