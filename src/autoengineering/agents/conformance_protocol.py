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

# A distinct protocol prevents Codex subscription proofs from being interpreted
# as Claude/API proofs. Cases retain their outer allowances and require
# their own API proof and owner-loss implementations.
CLAUDE_VERSION = "host-conformance-preparation-1.1"
CLAUDE_POLICIES = (
    ("text", 1, 0, "Anthropic message response; resolved model and reported usage recorded"),
    ("roles", 7, 2, "all four roles; expected synthetic decision; unchanged replay"),
    ("timeout", 1, 0, "owned timeout; local stops verified; remote completion unknown"),
    ("cancel", 1, 0, "queued cancellation distinguished from local stop and remote completion"),
    (
        "owner_loss",
        1,
        0,
        "owned supervisor interruption before API lease read; no replacement call",
    ),
    ("malformed", 2, 0, "invalid typed handoff rejected before science; at most one repair"),
)
CLAUDE_PROTOCOL_DIGEST = digest({"version": CLAUDE_VERSION, "cases": CLAUDE_POLICIES})
CLAUDE_IMPLEMENTED_CASES = ("text", "roles", "timeout", "cancel", "owner_loss", "malformed")


def protocol(version):
    """Select an explicit protocol, without importing a host or starting work."""
    if version == VERSION:
        return PROTOCOL_DIGEST, POLICIES, IMPLEMENTED_CASES, ("codex", "subscription", "2.1")
    if version == CLAUDE_VERSION:
        return (
            CLAUDE_PROTOCOL_DIGEST,
            CLAUDE_POLICIES,
            CLAUDE_IMPLEMENTED_CASES,
            ("claude", "api", "3.0"),
        )
    raise ValueError("unsupported conformance preparation version")


def batch_protocol(host):
    """Recover the protocol from the complete host selection, never its model name."""
    scope = (host.kind, host.auth_mode, host.adapter_version)
    for version in (VERSION, CLAUDE_VERSION):
        if scope == protocol(version)[3]:
            return protocol(version)
    raise ValueError("unsupported conformance runtime host selection")


def runtime_version(host):
    batch_protocol(host)
    return "conformance-runtime-1.1" if host.kind == "claude" else "conformance-runtime-1.0"
