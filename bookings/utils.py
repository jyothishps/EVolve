from django.utils import timezone
from datetime import timedelta, datetime
from .models import Booking

GRACE_PERIOD_MINUTES = 15


def expire_overdue_bookings():
    """
    Auto-cancel bookings whose slot start_time + grace period has passed,
    no charging session was started, AND the driver never checked in.
    Checking in protects a booking from auto-expiry even if admin hasn't
    started the session yet - gives real signal instead of guessing.
    """
    now = timezone.localtime()
    overdue_bookings = Booking.objects.filter(
        status__in=['Pending', 'Confirmed']
    ).select_related('slot')

    for booking in overdue_bookings:
        slot = booking.slot
        slot_start_dt = timezone.make_aware(
            datetime.combine(slot.date, slot.start_time)
        )
        deadline = slot_start_dt + timedelta(minutes=GRACE_PERIOD_MINUTES)

        has_session = hasattr(booking, 'chargingsession')
        has_checked_in = booking.checked_in_at is not None

        if now > deadline and not has_session and not has_checked_in:
            booking.status = 'Cancelled'
            booking.save()
            slot.status = 'Available'
            slot.save()