from django.utils import timezone
from django.db import transaction
from datetime import timedelta, datetime
from .models import Booking

GRACE_PERIOD_MINUTES = 15


def expire_overdue_bookings():
    """
    Auto-cancel bookings whose slot start_time + grace period has passed
    and no charging session was started (driver no-show).
    Frees the slot for other drivers. Runs lazily on relevant page loads,
    not as a background job - acceptable for this project's scale.
    """
    now = timezone.localtime()
    overdue_bookings = Booking.objects.filter(
        status__in=['Pending', 'Confirmed']
    ).select_related('slot')

    for booking in overdue_bookings:
        slot = booking.slot
        combined_dt = datetime.combine(slot.date, slot.start_time)
        if timezone.is_naive(combined_dt):
            slot_start_dt = timezone.make_aware(combined_dt)
        else:
            slot_start_dt = combined_dt

        deadline = slot_start_dt + timedelta(minutes=GRACE_PERIOD_MINUTES)

        # Skip if a session already started (driver did show up)
        has_session = hasattr(booking, 'chargingsession')

        if now > deadline and not has_session:
            with transaction.atomic():
                booking.status = 'Cancelled'
                booking.save()
                slot.status = 'Available'
                slot.save()