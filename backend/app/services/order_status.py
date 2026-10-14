"""The one place that says which order status may follow which.

Every write to ``Order.status`` goes through :func:`transition`. Refunds and
restocks hang off status changes (the ``trg_restore_inventory`` trigger restocks
on "cancelled"; cancelling refunds a prepaid order), so a status change that
should not happen is money or stock moving when it should not.

Who may do what:

* ``ADMIN``    — the status control on the admin order page.
* ``CUSTOMER`` — "cancel order" and "return an item" in the customer's account.
* ``SHIPMENT`` — booking a courier from the admin panel.
* ``RETURNS``  — the outcome of the returns desk closing a return.

"cancelled" and "returned" are final for everyone.
"""
from app.models.enums import OrderStatus as S

ADMIN = "admin"
CUSTOMER = "customer"
SHIPMENT = "shipment"
RETURNS = "returns"

# Fulfilment only moves forward. Steps may be skipped (a small shop often goes
# straight from "confirmed" to "shipped"), never undone.
_FULFILMENT = (S.pending, S.confirmed, S.packed, S.shipped, S.out_for_delivery, S.delivered)

_ADMIN = {
    current: set(_FULFILMENT[i + 1:]) for i, current in enumerate(_FULFILMENT)
}
# An admin can cancel until the parcel is handed over — including one already
# with the courier, which is how a refused or undeliverable parcel is closed.
for _status in _FULFILMENT[:-1]:
    _ADMIN[_status].add(S.cancelled)

_ALLOWED = {
    ADMIN: _ADMIN,
    CUSTOMER: {
        # Once it is packed the customer has to wait and return it instead.
        S.pending: {S.cancelled},
        S.confirmed: {S.cancelled},
        S.delivered: {S.return_requested},
    },
    SHIPMENT: {
        S.pending: {S.shipped},
        S.confirmed: {S.shipped},
        S.packed: {S.shipped},
    },
    RETURNS: {
        # Every item refunded -> "returned"; the last open return rejected (or
        # only some items returned) -> back to "delivered".
        S.return_requested: {S.returned, S.delivered},
    },
}

_LABELS = {status: status.value.replace("_", " ") for status in S}


class InvalidTransition(Exception):
    """The requested status change is not allowed. Routes answer 409."""

    def __init__(self, current, new, actor):
        self.current = current
        self.new = new
        self.allowed = allowed_next(current, actor)
        super().__init__(_explain(current, new, actor))


def allowed_next(current, actor):
    """Statuses ``actor`` may move an order to from ``current``, in a stable order."""
    allowed = _ALLOWED[actor].get(current, set())
    return [status for status in S if status in allowed]


def can_transition(current, new, actor):
    return new in _ALLOWED[actor].get(current, set())


def transition(order, new, actor):
    """Move ``order`` to ``new`` or raise :class:`InvalidTransition`.

    Does not commit. Setting the status it already has is not a transition and
    is rejected like any other; callers that treat a repeat as a no-op check
    for it first.
    """
    if not can_transition(order.status, new, actor):
        raise InvalidTransition(order.status, new, actor)
    order.status = new


def conflict_body(err):
    """JSON body for the 409 a route returns on :class:`InvalidTransition`."""
    return {
        "error": str(err),
        "status": err.current.value,
        "allowed": [status.value for status in err.allowed],
    }


def _explain(current, new, actor):
    here, there = _LABELS[current], _LABELS[new]
    if current in (S.cancelled, S.returned):
        return f"This order is {here}, which is final. Its status cannot change."
    if actor == CUSTOMER and new == S.cancelled:
        return (
            f"This order is already {here} and can no longer be cancelled."
            + (" You can return it once it is delivered." if current != S.delivered
               else " You can return it instead.")
        )
    if actor == CUSTOMER and new == S.return_requested:
        return "Only delivered items can be returned."
    if actor == SHIPMENT:
        return f"An order that is {here} cannot be shipped."
    if actor == ADMIN and new in (S.return_requested, S.returned):
        return (
            f"\"{there.capitalize()}\" is set by the returns process, not by hand. "
            "Handle the customer's return under Returns."
        )
    if actor == ADMIN and current == S.return_requested:
        return "This order has a return in progress. Resolve or reject it under Returns."
    if actor == ADMIN and new == S.cancelled:
        return "A delivered order cannot be cancelled. Handle it as a return instead."
    if new in _FULFILMENT and current in _FULFILMENT:
        return f"An order that is {here} cannot go back to {there}."
    return f"An order that is {here} cannot be moved to {there}."
