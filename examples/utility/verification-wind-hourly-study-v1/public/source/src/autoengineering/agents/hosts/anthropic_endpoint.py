"""Invocation-scoped native Claude endpoint, without upstream credentials.

The helper receives only the opaque local capability. Native authentication
headers are checked, never retained or forwarded. The upstream callback must be
separately owned and qualified. Local shutdown cannot prove remote work stopped.
"""

from __future__ import annotations

import hashlib
import hmac

from .anthropic_exchange import AnthropicExchange
from .text_endpoint import TextEndpoint


class AnthropicEndpoint(TextEndpoint):
    BOUNDARY_VERSION = AnthropicExchange.BOUNDARY_VERSION

    def _route_path(self, nonce):
        self._bootstrap_token = nonce
        # Pinned native CLI 2.1.310 uses this exact route. Unknown query flags,
        # discovery endpoints and other provider operations are not supported.
        return "/v1/messages?beta=true"

    def _bootstrap_url(self, nonce):
        return f"http://127.0.0.1:{self.port}"

    @property
    def bootstrap_token(self):
        """Private local helper capability, never a provider key or worker grant."""
        return self._bootstrap_token

    def _credential_error(self, headers):
        if any(name in headers for name in ("Proxy-Authorization", "Cookie")):
            return 400, "credential_header_forbidden"
        accepted = False
        for name, expected in (
            ("x-api-key", self._bootstrap_token),
            ("Authorization", "Bearer " + self._bootstrap_token),
        ):
            values = headers.get_all(name, [])
            if values:
                if (
                    len(values) != 1
                    or not values[0].isascii()
                    or not hmac.compare_digest(values[0], expected)
                ):
                    return 401, "invalid_invocation_capability"
                accepted = True
        if not accepted:
            return 401, "missing_invocation_capability"
        return None

    def _manifest_extra(self):
        return {
            "protocol": "anthropic-endpoint-1.0",
            "capability_sha256": hashlib.sha256(self._bootstrap_token.encode()).hexdigest(),
        }
