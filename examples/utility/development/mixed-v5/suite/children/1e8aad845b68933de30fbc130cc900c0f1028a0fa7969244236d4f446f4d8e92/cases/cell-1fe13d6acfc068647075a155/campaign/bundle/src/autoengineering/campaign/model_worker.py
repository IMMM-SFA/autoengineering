"""Private numerical worker, launched only from a broker-owned job artifact."""

from __future__ import annotations

import json
import hashlib
from pathlib import Path
import sys

import numpy as np

from autoengineering.adapters.contracts import PrepareContext
from autoengineering.adapters.python import run_lifecycle

from .artifacts import read_arrays, read_bytes
from .records import ArtifactRef
from .runtime import registry
from .serialization import canonical_json
from .store import durable_write


def main(job_path: Path):
    job = json.loads(job_path.read_text())
    context = PrepareContext.from_dict(job["context"])
    root = Path(job["bundle_root"])
    forcing_root = Path(job.get("forcing_root", job["bundle_root"]))
    forcing_ref = ArtifactRef.from_dict(job["forcing"])
    if forcing_ref.media_type == "application/json":
        # The scalar fixture deliberately has separate permitted forcing/label files.
        forcing = {
            name: np.asarray(value)
            for name, value in json.loads(read_bytes(forcing_root, forcing_ref)).items()
        }
    else:
        forcing = read_arrays(forcing_root, forcing_ref)
    if job["adapter_id"].startswith("generated-"):
        from .spec import CampaignSpec

        spec = CampaignSpec.from_yaml(job_path.parent.parent / "campaign.yaml")
        adapters = registry(spec=spec, root=root)
    else:
        adapters = registry()
    adapters.validate(job["adapter_id"], context.model, root)
    adapter = adapters.create(job["adapter_id"])
    if job["adapter_id"].startswith("generated-"):
        from autoengineering.adapters.isolated import IsolatedAdapter
        from .container_execution import launch_observer

        if not isinstance(adapter, IsolatedAdapter):
            raise ValueError("generated ID requires the fixed isolated adapter factory")
        adapter.launch_observer = launch_observer(
            job_path.parent.parent, job, attempt_id=job["attempt_id"], nonce=job["nonce"]
        )
    result = run_lifecycle(adapter, context, forcing, context.model.inputs, context.model.outputs)
    output_path = Path(job["output_path"])
    # Scratch is owner-private. Campaign commit hashes/copies these bytes before use.
    with output_path.open("xb") as stream:
        np.savez(stream, **result.outputs)
    durable_write(
        output_path.with_suffix(".metadata.json"),
        canonical_json(
            {
                "training": result.training.to_dict(),
                "elapsed_seconds": result.elapsed_seconds,
                "output_sha256": hashlib.sha256(output_path.read_bytes()).hexdigest(),
            }
        ).encode(),
    )


if __name__ == "__main__":
    main(Path(sys.argv[1]))
