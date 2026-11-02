"""CLI dispatch through application-owned, explicitly admitted scorer registrations.

Registrations are trusted Python objects, never import strings or user JSON.
Admission remains the application's responsibility. No built-in private scorer
is admitted by this module, and no factory is loaded from a command-line path.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import click

from autoengineering.campaign.artifacts import confined_file
from autoengineering.campaign.serialization import Record, canonical_json
from autoengineering.campaign.store import StoreError, checked_directory, durable_write
from .contracts import identifier, sha256
from .outcomes import OutcomeSpec
from .scoring import ConfirmationGrant, ConfirmationService, validate_grant
from .store import SuiteStore


@dataclass(frozen=True)
class ConfirmationRegistration:
    """Trusted application assertion, scoped to one suite, partition and scorer.

    A digest identifies the application's reviewed qualification evidence. This
    record does not itself verify or grant OS isolation or scientific admission.
    """

    profile_id: str
    suite_digest: str
    partition_digest: str
    scorer_digest: str
    qualification_digest: str
    outcome: OutcomeSpec
    scorer: Callable = field(repr=False, compare=False)
    admitted: bool

    def __post_init__(self):
        identifier(self.profile_id)
        for value in (
            self.suite_digest,
            self.partition_digest,
            self.scorer_digest,
            self.qualification_digest,
        ):
            sha256(value)
        if not isinstance(self.outcome, OutcomeSpec) or not callable(self.scorer):
            raise ValueError("confirmation registration requires a trusted scorer and outcome")
        if type(self.admitted) is not bool:
            raise ValueError("confirmation admission must be explicit")


@dataclass(frozen=True)
class ConfirmationRegistrationBinding(Record):
    grant_digest: str
    profile_id: str
    qualification_digest: str
    suite_digest: str
    partition_digest: str
    scorer_digest: str
    outcome_digest: str

    def _validate(self):
        identifier(self.profile_id)
        for name in (
            "grant_digest",
            "qualification_digest",
            "suite_digest",
            "partition_digest",
            "scorer_digest",
            "outcome_digest",
        ):
            sha256(getattr(self, name))


def _load(path, kind):
    path = Path(path).absolute()
    checked = confined_file(path.parent, path.name)
    if checked.stat().st_size > 1048576:
        raise StoreError("confirmation metadata exceeds its bound")
    return kind.from_json(checked.read_text())


def dispatch_confirmation(store, grant, registration, *, recover=False):
    """Pin trusted registration metadata, then use the original suite service.

    The pin is control evidence, not another scientific ledger. It cannot reserve
    work, grant private access, settle a charge or supply a score. Those decisions
    remain exclusively in ConfirmationService and the suite journal.
    """
    if (
        not registration.admitted
        or registration.suite_digest != store.spec.digest
        or registration.partition_digest != grant.partition_digest
        or registration.scorer_digest != grant.scorer_digest
        or registration.outcome.digest != grant.outcome_digest
        or getattr(registration.scorer, "identity", None) != registration.scorer_digest
        or type(recover) is not bool
    ):
        raise StoreError("confirmation registration is not admitted or differs from its grant")
    binding = ConfirmationRegistrationBinding(
        grant.digest,
        registration.profile_id,
        registration.qualification_digest,
        registration.suite_digest,
        registration.partition_digest,
        registration.scorer_digest,
        registration.outcome.digest,
    )
    with store.writer():
        state = store.replay()
        validate_grant(store, grant, state["frozen"])
        folder = checked_directory(store.root / "control") / "confirmation-registrations"
        folder.mkdir(mode=0o700, exist_ok=True)
        checked_directory(folder)
        path = folder / (grant.digest + ".json")
        if path.exists() or path.is_symlink():
            if _load(path, ConfirmationRegistrationBinding) != binding:
                raise StoreError("original confirmation registration changed")
        else:
            durable_write(path, (binding.to_json() + "\n").encode())
    service = ConfirmationService(
        store,
        registration.scorer,
        scorer_digest=registration.scorer_digest,
        outcome_contract=registration.outcome,
    )
    receipt = service.recover(grant) if recover else service.confirm(grant)
    return {
        "status": "confirmation_committed",
        "profile_id": registration.profile_id,
        "qualification_digest": registration.qualification_digest,
        "registration_binding_digest": binding.digest,
        "recovery_requested": recover,
        "receipt": receipt.to_dict(),
    }


def build_confirmation_command(registrations=()):
    """Build the same command for the base CLI or a trusted application wrapper.

    The default has no admitted registrations. Applications pass reviewed objects
    in trusted Python when constructing their CLI. The command never treats an
    input record, module string, environment variable or flag as admission.
    """
    entries = tuple(registrations)
    if any(not isinstance(item, ConfirmationRegistration) for item in entries):
        raise ValueError("invalid trusted confirmation registration")
    registry = {item.profile_id: item for item in entries}
    if len(registry) != len(entries):
        raise ValueError("duplicate confirmation registration")

    @click.command("confirm")
    @click.argument("workdir", type=click.Path(exists=True, path_type=Path))
    @click.argument("grant", type=click.Path(exists=True, path_type=Path))
    @click.option("--registration", "profile_id", required=True)
    @click.option(
        "--recover", is_flag=True, help="Publish only a verified original attempt result."
    )
    def confirm(workdir, grant, profile_id, recover):
        """Confirm sealed selections using a trusted application's admitted scorer."""
        try:
            registration = registry.get(profile_id)
            if registration is None or not registration.admitted:
                raise StoreError("confirmation registration is unavailable")
            document = dispatch_confirmation(
                SuiteStore(workdir),
                _load(grant, ConfirmationGrant),
                registration,
                recover=recover,
            )
        except Exception:
            # Trusted scorer failures can still contain private paths or values.
            click.echo(
                canonical_json(
                    {
                        "status": "error",
                        "error": "confirmation_not_admitted_or_invalid",
                    }
                )
            )
            raise click.exceptions.Exit(2) from None
        click.echo(canonical_json(document))

    return confirm
