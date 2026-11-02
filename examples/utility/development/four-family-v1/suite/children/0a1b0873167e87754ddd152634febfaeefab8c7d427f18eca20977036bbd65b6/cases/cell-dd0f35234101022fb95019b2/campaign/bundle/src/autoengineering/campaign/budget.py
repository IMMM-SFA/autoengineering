"""Reservation accounting separates capacity, physical attempts and uncertain cost."""

from __future__ import annotations

from dataclasses import dataclass, replace

from .records import AttemptRecord, identifier, unique
from .serialization import Record


class BudgetExhausted(ValueError):
    pass


@dataclass(frozen=True)
class Reservation(Record):
    id: str
    capacity: int
    terminal: bool = False

    def _validate(self):
        identifier(self.id)
        if self.capacity < 1:
            raise ValueError("reservation must be positive")


@dataclass(frozen=True)
class BudgetAccount(Record):
    max_executions: int
    active_deadline_seconds: float
    timeout_reservation_seconds: float
    reservations: tuple[Reservation, ...] = ()
    attempts: tuple[AttemptRecord, ...] = ()

    def _validate(self):
        if (
            min(self.max_executions, self.active_deadline_seconds, self.timeout_reservation_seconds)
            <= 0
        ):
            raise ValueError("budget limits must be positive")
        unique([item.id for item in self.reservations], "reservation")
        unique([item.id for item in self.attempts], "attempt")
        by_id = {item.id: item for item in self.reservations}
        if any(item.reservation_id not in by_id for item in self.attempts):
            raise ValueError("attempt references an unknown reservation")
        for reservation in self.reservations:
            charged = sum(item.reservation_id == reservation.id for item in self.attempts)
            if charged > reservation.capacity:
                raise ValueError("attempts exceed reservation")
            if reservation.terminal and any(
                item.reservation_id == reservation.id
                and item.state not in ("finished", "reconciled")
                for item in self.attempts
            ):
                raise ValueError("cannot release an uncertain or active reservation")
        if self.committed_capacity > self.max_executions:
            raise ValueError("reservations exceed campaign ceiling")

    @property
    def committed_capacity(self) -> int:
        return sum(
            sum(item.reservation_id == reservation.id for item in self.attempts)
            if reservation.terminal
            else reservation.capacity
            for reservation in self.reservations
        )

    @property
    def confirmed_attempts(self) -> int:
        return sum(
            item.state == "finished"
            or (item.state == "reconciled" and item.measured_cost is not None)
            for item in self.attempts
        )

    @property
    def unresolved_attempts(self) -> int:
        return sum(item.state not in ("finished", "reconciled") for item in self.attempts)

    @property
    def measured_cost(self) -> float:
        return sum(item.measured_cost or 0 for item in self.attempts)

    @property
    def cost_is_uncertain(self) -> bool:
        return any(item.uncertain_cost or item.measured_cost is None for item in self.attempts)

    @property
    def charged_seconds(self) -> float:
        return sum(
            self.timeout_reservation_seconds
            if item.state not in ("finished", "reconciled")
            else (
                item.elapsed_seconds
                if item.elapsed_seconds is not None
                else self.timeout_reservation_seconds
            )
            for item in self.attempts
        )

    def reserve(
        self, reservation_id: str, capacity: int, *, invocation_remaining: int | None = None
    ):
        if type(capacity) is not int or capacity < 1:
            raise ValueError("capacity must be a positive integer")
        if invocation_remaining is not None and (
            type(invocation_remaining) is not int or invocation_remaining < capacity
        ):
            raise BudgetExhausted("stage requires more starts than the invocation permits")
        if self.committed_capacity + capacity > self.max_executions:
            raise BudgetExhausted("campaign execution allowance exhausted")
        if (
            self.charged_seconds + capacity * self.timeout_reservation_seconds
            > self.active_deadline_seconds
        ):
            raise BudgetExhausted("campaign active time allowance exhausted")
        return replace(
            self, reservations=(*self.reservations, Reservation(reservation_id, capacity))
        )

    def start(self, attempt: AttemptRecord):
        reservation = next(
            (item for item in self.reservations if item.id == attempt.reservation_id), None
        )
        if reservation is None or reservation.terminal:
            raise BudgetExhausted("reservation is missing or terminal")
        if self.unresolved_attempts:
            raise BudgetExhausted("unresolved attempt requires reconciliation before a new start")
        if self.charged_seconds + self.timeout_reservation_seconds > self.active_deadline_seconds:
            raise BudgetExhausted("active time allowance exhausted")
        if attempt.state != "launched" or not attempt.uncertain_cost:
            raise ValueError("prelaunch attempt must conservatively retain uncertain cost")
        return replace(self, attempts=(*self.attempts, attempt))

    def resolve(self, attempt: AttemptRecord):
        previous = next((item for item in self.attempts if item.id == attempt.id), None)
        if previous is None:
            raise ValueError("cannot resolve an unknown attempt")
        if previous.state in ("finished", "reconciled"):
            if previous != attempt:
                raise ValueError("cannot rewrite a resolved attempt")
            return self
        if (attempt.reservation_id, attempt.child_action_id, attempt.launch_nonce) != (
            previous.reservation_id,
            previous.child_action_id,
            previous.launch_nonce,
        ):
            raise ValueError("attempt identity changed")
        if attempt.state not in ("finished", "uncertain", "reconciled"):
            raise ValueError("invalid attempt resolution")
        return replace(
            self,
            attempts=tuple(attempt if item.id == attempt.id else item for item in self.attempts),
        )

    def release(self, reservation_id: str):
        if not any(item.id == reservation_id for item in self.reservations):
            raise ValueError("unknown reservation")
        return replace(
            self,
            reservations=tuple(
                replace(item, terminal=True) if item.id == reservation_id else item
                for item in self.reservations
            ),
        )
