import uuid
from typing import Any

from django.utils import timezone

from reservations.models import Guest, Reservation
from reservations.payments.models import Payment


def _payment_error(reservation: Reservation) -> str | None:
    """Return an error message if the reservation's payment state forbids check-in.

    Reservations without any Payment rows (e.g. comps added in the admin) are allowed.
    Reservations that went through the online flow must have a completed payment: an
    abandoned or pending attempt must never let anyone in, even if a confirmation mail
    with QR codes was sent for it by mistake.
    """
    payments = list(reservation.payment_set.order_by("-created_at"))
    if not payments:
        return None
    if payments[0].status in (Payment.Status.FAILED, Payment.Status.REFUNDED):
        return "Payment failed or refunded"
    if not any(p.status == Payment.Status.COMPLETED for p in payments):
        return "Payment not completed"
    return None


def _validate_check_in(
    entity: Reservation | Guest,
    reservation: Reservation,
    event_id: int | None,
    ticket_id: uuid.UUID | None,
    names: list[str],
) -> tuple[dict[str, Any], int] | None:
    """Run all validations. Returns error tuple if validation fails, None if all checks pass."""
    # Check if ticket is for the correct event
    if event_id is not None and reservation.event_id != event_id:
        return {
            "error": "Ticket is for a different event",
            "reservation_number": str(ticket_id),
            "guests": names,
        }, 409

    # Check if payment is invalid (failed, refunded, or never completed)
    payment_error = _payment_error(reservation)
    if payment_error:
        return {
            "error": payment_error,
            "reservation_number": str(ticket_id),
            "guests": names,
        }, 402

    # Check if already checked in
    if entity.checked_in:
        return {
            "error": "Ticket already checked in",
            "reservation_number": str(ticket_id),
            "guests": names,
        }, 400

    return None


def _do_check_in(
    entity: Reservation | Guest,
    ticket_id: uuid.UUID | None,
    names: list[str],
    **extra: Any,
) -> tuple[dict[str, Any], int]:
    """Perform the check-in action. Assumes all validations have passed."""
    entity.checked_in = True
    entity.save()
    return {"success": True, "reservation_number": str(ticket_id), "guests": names, **extra}, 200


def check_in_ticket(
    ticket_id: uuid.UUID, event_id: int | None = None
) -> tuple[dict[str, Any], int]:
    """Returns (response_dict, http_status_code)."""
    try:
        reservation = Reservation.objects.get(id=ticket_id)
        names = [f"{reservation.first_name} {reservation.last_name}"]
        names.extend(str(g) for g in reservation.guests.all())

        validation_error = _validate_check_in(
            reservation, reservation, event_id, reservation.id, names
        )
        if validation_error:
            return validation_error

        return _do_check_in(reservation, reservation.id, names, is_group=True)
    except Reservation.DoesNotExist:
        pass

    try:
        guest = Guest.objects.get(ticket_id=ticket_id)
        names = [str(guest)]

        validation_error = _validate_check_in(
            guest, guest.reservation, event_id, guest.ticket_id, names
        )
        if validation_error:
            return validation_error

        return _do_check_in(guest, guest.ticket_id, names)
    except Guest.DoesNotExist:
        return {"error": "Ticket not found"}, 404


def get_upcoming_events():
    from events.models import Event

    today = timezone.now().date()
    return (
        Event.objects.filter(begin__date__gte=today)
        .select_related("show")
        .order_by("begin")
        .values("id", "begin", "show__title")
    )
