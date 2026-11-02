"""Development-only supervised routing with explicit conservative stores.

The release fraction is logistic(b0 + b1 * log1p(available_store / 100 mm)).
Nonnegative b1 makes the fraction nondecreasing with storage. Supervised fitting
uses only declared fitting observations, with no autoregressive discharge inputs.
Local trusted execution requires a declared runtime profile and fitting grant or
frozen selected state. Independent utility and private execution remain unadmitted.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
import math
from pathlib import Path
import time
from uuid import uuid4

import numpy as np

from autoengineering.adapters.contracts import (
    PrepareContext,
    TrainingResult,
    TrainingArtifactBundle,
    validate_arrays,
)
from autoengineering.campaign.artifacts import put_bytes, read_bytes, reference
from autoengineering.campaign.records import ArtifactRef
from autoengineering.campaign.serialization import digest
from autoengineering.campaign.store import checked_directory, durable_write
from autoengineering.utility.exposure import iso_date
from autoengineering.utility.hydrology_training import (
    RoutingTrainingProfile,
    RoutingFit,
    TrainingIntent,
    TrainingWork,
    routing_training_identity,
)
from examples.utility.hydrology_site import (
    HydrologySite,
    INPUTS,
    SiteHydrologyAdapter,
    _graph,
    context as site_context,
    prepared_development,
)

SOURCE = "examples/utility/hydrology_learned.py"
ROUTING = "logistic-storage-release-v1"


@dataclass(frozen=True)
class FrozenRouting:
    artifact: ArtifactRef
    fit: RoutingFit

    def __post_init__(self):
        import hashlib

        raw = self.fit.to_json().encode()
        if self.artifact.sha256 != hashlib.sha256(
            raw
        ).hexdigest() or self.artifact.size_bytes != len(raw):
            raise ValueError("trained artifact differs from its immutable fit")


def load_training(root: Path, artifact: ArtifactRef) -> FrozenRouting:
    """Read only a digest-verified JSON fit, without pickle or executable loading."""
    raw = read_bytes(root, artifact, max_bytes=65536)
    return FrozenRouting(artifact, RoutingFit.from_json(raw.decode("utf-8")))


def prepared_training(
    plan, document, fitting_document, parameters, scratch, *, max_rollouts, source_root=None
):
    """Bridge already hash-verified public preparation documents, without training.

    Selection labels are never accepted. Only the driver/label prefix through
    fitting enters the training mapping. Full development drivers support later
    selection evaluation. Caller authorization and artifact verification remain
    separate from these structural checks.
    """
    if set(parameters) != {"capacity", "pet"}:
        raise ValueError("learned routing parameters are capacity and PET family only")
    site, base, forcing = prepared_development(
        plan,
        document,
        dict(parameters) | {"recession": 0.7},
        scratch,
        role="selection",
        source_root=source_root,
    )
    if not isinstance(fitting_document, dict) or set(fitting_document) != {"labels", "mask"}:
        raise ValueError("training bridge requires only fitting labels and mask")
    labels, mask = np.asarray(fitting_document["labels"]), np.asarray(fitting_document["mask"])
    dates = base.model.inputs[0].time.dates
    roles = np.asarray([plan.windows[1].start <= day <= plan.windows[1].end for day in dates])
    if (
        mask.dtype.kind != "b"
        or mask.shape != (len(dates),)
        or labels.shape != mask.shape
        or labels.dtype.kind not in "fiu"
        or not np.isfinite(labels).all()
        or (labels < 0).any()
        or (mask & ~roles).any()
        or (labels[~mask] != 0).any()
    ):
        raise ValueError("training bridge received labels outside its fitting scope")
    n = (iso_date(plan.windows[1].end) - iso_date(dates[0])).days + 1
    warmup = (iso_date(plan.windows[0].end) - iso_date(dates[0])).days + 1
    profile = RoutingTrainingProfile(
        dates[:n], warmup, tuple(bool(v) for v in mask[:n]), max_rollouts
    )
    ctx = context(
        site,
        profile,
        dates,
        parameters,
        scratch,
        warmup_mask=base.model.inputs[0].time.warmup_mask,
        scoring_mask=base.model.inputs[0].time.scoring_mask,
        source_root=source_root,
    )
    training = {k: v[:n].copy() for k, v in forcing.items()} | {
        "labels": labels[:n].copy(),
        "mask": mask[:n].copy(),
    }
    for value in training.values():
        value.setflags(write=False)
    return site, profile, ctx, forcing, training


def context(
    site, profile, dates, parameters, scratch, *, warmup_mask, scoring_mask, source_root=None
):
    if set(parameters) != {"capacity", "pet"}:
        raise ValueError("learned routing parameters are capacity and PET family only")
    base = site_context(
        site,
        dates,
        dict(parameters) | {"recession": 0.7},
        scratch,
        warmup_mask=warmup_mask,
        scoring_mask=scoring_mask,
        source_root=source_root,
    )
    root = Path(source_root) if source_root is not None else Path(__file__).resolve().parents[2]
    sources = tuple(
        reference(root, path, media_type="text/plain", producer="learned-hydrology")
        for path in (
            SOURCE, "examples/utility/hydrology_runtime.py",
            "src/autoengineering/utility/hydrology_training.py",
        )
    )
    model = replace(
        base.model,
        graph_digest=digest({"site": site.digest, "routing": ROUTING, "training": profile.digest}),
        implementations=dict(base.model.implementations)
        | {"routing": ROUTING, "training": profile.digest},
        source_bundle=(*base.model.source_bundle, *sources),
    )
    return replace(base, model=model, parameters=parameters)


def _base(ctx, site, size=None):
    model = replace(
        ctx.model,
        graph_digest=_graph(site),
        implementations={
            "pet": ctx.parameters["pet"],
            "soil": "bucket-v1",
            "routing": "linear-v1",
            "site": site.digest,
        },
        source_bundle=tuple(r for r in ctx.model.source_bundle if r.path != SOURCE),
    )
    if size is not None:

        def crop(port):
            t = port.time
            return (
                port
                if t is None
                else replace(
                    port,
                    time=replace(
                        t,
                        dates=t.dates[:size],
                        warmup_mask=t.warmup_mask[:size],
                        scoring_mask=t.scoring_mask[:size],
                    ),
                )
            )

        model = replace(
            model, inputs=tuple(map(crop, model.inputs)), outputs=tuple(map(crop, model.outputs))
        )
    return replace(ctx, model=model, parameters=dict(ctx.parameters) | {"recession": 0.7})


def _identity(ctx, site, profile):
    # Inference can extend the daily axis, but cannot change the learned object,
    # parameters, initialization, fitting prefix, sources, seed or environment.
    if ctx.model.implementations.get("site") != site.digest:
        raise ValueError("learned routing site identity differs")
    return routing_training_identity(ctx.model, ctx.parameters, ctx.seed, profile)


def _forcing_digest(values):
    return digest({name: np.asarray(values[name], dtype=float).tolist() for name in INPUTS})


def _fluxes(ctx, site, forcing):
    adapter = SiteHydrologyAdapter(site)
    handle = adapter.prepare(_base(ctx, site))
    try:
        result = adapter.run(handle, forcing)
    finally:
        adapter.cleanup(handle)
    soil = result["soil"]
    excess = (
        np.r_[float(result["initial_soil"]), soil[:-1]]
        + forcing["precip_mm"]
        - result["aet"]
        - soil
    )
    if not np.isfinite(excess).all() or (excess < -1e-10).any():
        raise ValueError("invalid conservative soil excess")
    return result, np.maximum(excess, 0.0)


def _route(excess, coefficients):
    reservoir = 0.0
    flow, stores = [], []
    for value in excess:
        reservoir += value
        score = coefficients[0] + coefficients[1] * math.log1p(reservoir / 100.0)
        fraction = (
            1 / (1 + math.exp(-score)) if score >= 0 else math.exp(score) / (1 + math.exp(score))
        )
        q = fraction * reservoir
        reservoir -= q
        flow.append(q)
        stores.append(reservoir)
    return np.asarray(flow), np.asarray(stores)


@dataclass
class Handle:
    context: PrepareContext
    frozen: FrozenRouting | None
    closed: bool = False
    consumed: bool = False
    training_attempted: bool = False
    routing_rollouts: int = 0
    flux_preparation_runs: int = 0
    completed_routing_rollouts: int = 0
    completed_flux_preparation_runs: int = 0


class LearnedRoutingAdapter:
    def __init__(
        self,
        site: HydrologySite,
        profile: RoutingTrainingProfile,
        frozen: FrozenRouting | None = None,
    ):
        if not isinstance(site, HydrologySite) or not isinstance(profile, RoutingTrainingProfile):
            raise ValueError("learned routing requires immutable site and training profile")
        self.site, self.profile, self.frozen = site, profile, frozen

    def prepare(self, ctx):
        return Handle(ctx, self.frozen)

    def validate(self, handle):
        if handle.closed:
            raise ValueError("learned routing handle is closed")
        ctx, profile = handle.context, self.profile
        if set(ctx.parameters) != {"capacity", "pet"}:
            raise ValueError("learned routing parameters differ")
        parent = SiteHydrologyAdapter(self.site)
        temporary = parent.prepare(_base(ctx, self.site))
        try:
            parent.validate(temporary)
        finally:
            parent.cleanup(temporary)
        expected = {
            "pet": ctx.parameters["pet"],
            "soil": "bucket-v1",
            "routing": ROUTING,
            "site": self.site.digest,
            "training": profile.digest,
        }
        if (
            dict(ctx.model.implementations) != expected
            or ctx.model.graph_digest
            != digest({"site": self.site.digest, "routing": ROUTING, "training": profile.digest})
            or SOURCE not in {r.path for r in ctx.model.source_bundle}
        ):
            raise ValueError("learned routing model identity differs")
        clock = ctx.model.inputs[0].time
        n = len(profile.fitting_dates)
        if clock.dates[:n] != profile.fitting_dates or clock.warmup_mask != (
            True,
        ) * profile.warmup_rows + (False,) * (len(clock.dates) - profile.warmup_rows):
            raise ValueError("learned routing needs its complete fitting prefix and initialization")
        if handle.frozen is not None and (
            handle.frozen.fit.identity != _identity(ctx, self.site, profile)
            or handle.frozen.fit.seed != ctx.seed
        ):
            raise ValueError("trained artifact belongs to another model or profile")
        if handle.frozen is not None and (
            handle.frozen.fit.routing_rollouts > profile.max_rollouts
            or handle.frozen.fit.simulated_days != handle.frozen.fit.routing_rollouts * n
        ):
            raise ValueError("trained artifact work differs from its profile")

    def train(self, handle, fitting_data):
        self.validate(handle)
        if handle.frozen is not None:
            if fitting_data:
                raise ValueError("frozen inference cannot consume training data")
            return TrainingResult("not_applicable", handle.frozen.artifact, None)
        if handle.training_attempted or handle.consumed:
            raise ValueError("training cannot be retried in the same attempt")
        handle.training_attempted = True
        root = checked_directory(Path(handle.context.scratch_path))
        (root / "artifacts").mkdir(mode=0o700, exist_ok=True)
        checked_directory(root / "artifacts")
        identity = _identity(handle.context, self.site, self.profile)
        training_id = "training-" + uuid4().hex
        # Fixed create-only intent refuses a second training start in this scope.
        # An interrupted intent without a result stays unresolved, never retried.
        durable_write(
            root / "training-intent.json",
            TrainingIntent.from_dict(
                {
                    "schema": "learned-routing-training-intent-v2",
                    "training_id": training_id,
                    "identity": identity,
                    "seed": handle.context.seed,
                    "max_rollouts": self.profile.max_rollouts,
                    "fitting_days": len(self.profile.fitting_dates),
                }
            )
            .to_json()
            .encode(),
        )
        started = time.monotonic()
        result = None
        try:
            result = self._fit(handle, fitting_data, started)
        except Exception:
            raise ValueError("learned routing training failed") from None
        finally:
            receipt = {
                "schema": "learned-routing-training-result-v2",
                "training_id": training_id,
                "identity": identity,
                "status": "trained" if result is not None else "failed",
                "training_seconds": time.monotonic() - started,
                "routing_rollouts": handle.routing_rollouts,
                "reserved_routing_days": handle.routing_rollouts * len(self.profile.fitting_dates),
                "completed_routing_rollouts": handle.completed_routing_rollouts,
                "completed_routing_days": handle.completed_routing_rollouts
                * len(self.profile.fitting_dates),
                "partial_routing_work_unknown": handle.routing_rollouts
                != handle.completed_routing_rollouts,
                "flux_preparation_runs": handle.flux_preparation_runs,
                "completed_flux_preparation_runs": handle.completed_flux_preparation_runs,
                "partial_flux_work_unknown": handle.flux_preparation_runs
                != handle.completed_flux_preparation_runs,
                "trained_artifact": None if result is None else result.artifact.to_dict(),
            }
            durable_write(
                root / "training-result.json", TrainingWork.from_dict(receipt).to_json().encode()
            )
        companions = [
            put_bytes(
                root,
                self.profile.to_json().encode(),
                name="training-profile.json",
                media_type="application/json",
                producer="learned-hydrology",
            )
        ]
        for name in ("training-intent.json", "training-result.json"):
            companions.append(
                put_bytes(
                    root,
                    (root / name).read_bytes(),
                    name=name,
                    media_type="application/json",
                    producer="learned-hydrology",
                )
            )
        bundle = TrainingArtifactBundle(
            "training-artifact-bundle-v1", result.artifact, tuple(companions)
        )
        bundle_ref = put_bytes(
            root,
            bundle.to_json().encode(),
            name="training-bundle.json",
            media_type="application/json",
            producer="learned-hydrology",
        )
        result = replace(
            result,
            artifact=replace(
                result.artifact,
                metadata=dict(result.artifact.metadata, training_bundle=bundle_ref.to_json()),
            ),
        )
        return result

    def _fit(self, handle, fitting_data, started):
        profile, ctx = self.profile, handle.context
        n = len(profile.fitting_dates)
        if set(fitting_data) != {*INPUTS, "labels", "mask"}:
            raise ValueError("training requires only its fitting drivers, labels and mask")
        training_ctx = _base(ctx, self.site, n)
        forcing = validate_arrays(
            {k: fitting_data[k] for k in INPUTS},
            training_ctx.model.inputs,
            training_ctx.model.inputs,
        )
        labels, mask = np.asarray(fitting_data["labels"]), np.asarray(fitting_data["mask"])
        if (
            labels.shape != (n,)
            or labels.dtype.kind not in "fiu"
            or not np.isfinite(labels).all()
            or (labels < 0).any()
            or mask.dtype.kind != "b"
            or mask.shape != (n,)
            or not np.array_equal(mask, profile.valid_mask)
            or (labels[~mask] != 0).any()
        ):
            raise ValueError("training labels or mask differ from the fitting profile")
        handle.flux_preparation_runs += 1
        _, excess = _fluxes(training_ctx, self.site, forcing)
        handle.completed_flux_preparation_runs += 1
        from scipy.optimize import least_squares
        import scipy

        def residual(coefficients):
            if handle.routing_rollouts >= profile.max_rollouts:
                raise ValueError("training routing rollout budget exhausted")
            handle.routing_rollouts += 1
            prediction, _ = _route(excess, coefficients)
            handle.completed_routing_rollouts += 1
            return prediction[mask] - labels[mask]

        fitted = least_squares(
            residual,
            [math.log(0.3 / 0.7), 0.1],
            bounds=([-6.0, 0.0], [6.0, 3.0]),
            jac="2-point",
            method="trf",
            ftol=1e-8,
            xtol=1e-8,
            gtol=1e-8,
            max_nfev=profile.max_rollouts,
        )
        if not fitted.success or np.linalg.matrix_rank(fitted.jac) < 2:
            raise ValueError("training failed or routing coefficients are unidentified")
        fit = RoutingFit(
            _identity(ctx, self.site, profile),
            digest(
                {
                    "forcing": _forcing_digest(forcing),
                    "labels": labels.tolist(),
                    "mask": mask.tolist(),
                }
            ),
            _forcing_digest(forcing),
            tuple(float(v) for v in fitted.x),
            ctx.seed,
            handle.routing_rollouts,
            handle.routing_rollouts * n,
            1,
            time.monotonic() - started,
            scipy.__version__,
        )
        artifact = put_bytes(
            Path(ctx.scratch_path),
            fit.to_json().encode(),
            name="routing-fit.json",
            media_type="application/json",
            producer="learned-hydrology",
        )
        handle.frozen = FrozenRouting(artifact, fit)
        return TrainingResult("trained", artifact, float(handle.routing_rollouts))

    def run(self, handle, forcing):
        self.validate(handle)
        if handle.frozen is None or handle.consumed:
            raise ValueError("inference needs a frozen fit and a fresh handle")
        inputs = validate_arrays(forcing, handle.context.model.inputs, handle.context.model.inputs)
        prefix = {k: v[: len(self.profile.fitting_dates)] for k, v in inputs.items()}
        if _forcing_digest(prefix) != handle.frozen.fit.fitting_forcing_digest:
            raise ValueError("inference fitting-prefix drivers differ from training")
        handle.consumed = True
        outputs, excess = _fluxes(handle.context, self.site, inputs)
        prediction, reservoir = _route(excess, handle.frozen.fit.coefficients)
        return outputs | {"prediction": prediction, "reservoir": reservoir}

    def inspect(self, handle, outputs):
        return {
            "final_stores": np.asarray([outputs["soil"][-1], outputs["reservoir"][-1]]),
            "routing_coefficients": np.asarray(handle.frozen.fit.coefficients),
        }

    def cleanup(self, handle):
        if handle is not None:
            handle.closed = True
