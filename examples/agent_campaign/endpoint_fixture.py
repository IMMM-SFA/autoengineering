"""Authored upstream for exercising the package endpoint with an installed CLI.

This returns fixed bytes locally. It supplies neither real authentication nor
provider transport and cannot qualify a production host.
"""

from __future__ import annotations

from dataclasses import asdict
import hashlib
from pathlib import Path

from autoengineering.agents.hosts.response_boundary import VERSION
from autoengineering.agents.hosts.text_endpoint import TextEndpoint
from autoengineering.agents.hosts.text_exchange import TextExchange
from autoengineering.campaign.artifacts import read_bytes
from autoengineering.campaign.records import ArtifactRef
from autoengineering.campaign.serialization import canonical_json, unique_json
from autoengineering.campaign.store import durable_write


class AuthoredTextEndpoint:
    def __init__(self, output: Path, *, body: bytes, model: str, prompt: str, schema: dict):
        self.output = output
        self.body = body
        self.requests, self.errors = [], []
        self.attempts = 0
        self.boundary = self.stop_receipt = None
        self.exchange = TextExchange.create(
            output / "exchange",
            invocation_id="offline-client",
            requested_model=model,
            approved_prompt=prompt,
            output_schema=schema,
        )

        def authored(request):
            durable_write(output / "upstream-request.bin", request)
            durable_write(output / "upstream-response.bin", body)
            return body

        self.endpoint = TextEndpoint(self.exchange, authored, directory=output / "endpoint")
        self._closed = False

    @property
    def port(self):
        return self.endpoint.port

    @property
    def base_url(self):
        return self.endpoint.base_url

    def close(self):
        stop = self.endpoint.close()
        self.stop_receipt = asdict(stop)
        self.attempts = stop.request_attempts
        if not (stop.listener_closed and stop.handler_stopped and stop.upstream_callback_stopped):
            raise RuntimeError("offline endpoint stop is unverified")
        if self._closed:
            return
        self._closed = True
        result = self.exchange.recover()
        client_path = self.exchange.root / "client.json"
        if client_path.exists():
            reference = ArtifactRef.from_dict(unique_json(client_path.read_text()))
            raw = read_bytes(self.exchange.root, reference)
            durable_write(self.output / "request.bin", raw)
            self.requests.append(
                {"path": "invocation_response", "bytes": len(raw), "sha256": reference.sha256}
            )
        response = result.response
        if response is None:
            self.errors.append("TextExchange: " + str(result.reason))
            self.boundary = {
                "version": VERSION,
                "status": "rejected" if result.status == "rejected" else "reconciliation_required",
                "reason": result.reason,
                "client_response_bytes": 0,
                "provider_requests_reserved": result.provider_requests_reserved,
            }
        else:
            durable_write(self.output / "client-response.bin", response.normalized_sse)
            self.boundary = {
                "version": VERSION,
                "status": "validated",
                "reported_model": response.reported_model,
                "usage": dict(response.usage),
                "raw_sha256": response.raw_sha256,
                "client_response_sha256": hashlib.sha256(response.normalized_sse).hexdigest(),
                "client_response_bytes": len(response.normalized_sse),
                "provider_requests_reserved": result.provider_requests_reserved,
            }
        durable_write(self.output / "boundary.json", canonical_json(self.boundary).encode())
