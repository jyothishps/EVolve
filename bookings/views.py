from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction, IntegrityError
from django.utils import timezone

from stations.models import ChargingSlot
from accounts.decorators import admin_required
from .models import Booking
from .utils import expire_overdue_bookings

@login_required
def booking_create(request, slot_id):
    slot = get_object_or_404(ChargingSlot, id=slot_id)

    if request.user.is_admin():
        messages.error(request, 'Admins cannot make bookings.')
        return redirect('accounts:admin_dashboard')

    if slot.date < timezone.localdate():
        messages.error(request, 'Cannot book a slot in the past.')
        return redirect('stations:driver_station_detail', station_id=slot.station.id)

    if slot.station.status != 'Active':
        messages.error(request, 'This station is not currently active.')
        return redirect('stations:driver_station_list')

    if slot.charger.status != 'Available':
        messages.error(request, 'Selected charger is not available.')
        return redirect('stations:driver_station_detail', station_id=slot.station.id)

    # NEW: check for overlapping active bookings by the same driver on the same date
    overlapping = Booking.objects.filter(
        user=request.user,
        status__in=['Pending', 'Confirmed'],
        slot__date=slot.date,
    ).filter(
        slot__start_time__lt=slot.end_time,
        slot__end_time__gt=slot.start_time,
    )

    if overlapping.exists():
        clash = overlapping.first()
        messages.error(
            request,
            f'This overlaps with your existing booking at {clash.station.name} '
            f'({clash.slot.start_time} - {clash.slot.end_time}). Please choose a different time.'
        )
        return redirect('stations:driver_station_detail', station_id=slot.station.id)

    if request.method == 'POST':
        try:
            with transaction.atomic():
                locked_slot = ChargingSlot.objects.select_for_update().get(id=slot.id)

                if locked_slot.status != 'Available':
                    messages.error(request, 'Sorry, this slot is no longer available.')
                    return redirect('stations:driver_station_detail', station_id=slot.station.id)

                booking = Booking.objects.create(
                    user=request.user,
                    station=locked_slot.station,
                    charger=locked_slot.charger,
                    slot=locked_slot,
                    booking_date=locked_slot.date,
                    booking_time=locked_slot.start_time,
                    status='Confirmed',
                )

                locked_slot.status = 'Reserved'
                locked_slot.save()

            messages.success(request, 'Booking confirmed successfully.')
            return redirect('bookings:booking_detail', booking_id=booking.id)

        except IntegrityError:
            messages.error(request, 'This slot was already booked. Please choose another.')
            return redirect('stations:driver_station_detail', station_id=slot.station.id)

    return render(request, 'bookings/booking_confirm.html', {'slot': slot})


@login_required
def booking_list(request):
    """
    Driver sees only their own bookings, newest first.
    select_related pulls station/charger/slot data in same query.
    """
    expire_overdue_bookings()
    bookings = Booking.objects.filter(user=request.user).select_related(
        'station', 'charger', 'slot'
    ).order_by('-created_at')
    return render(request, 'bookings/booking_list.html', {'bookings': bookings})


@login_required
def booking_detail(request, booking_id):
    """
    Show one booking's full details. Ownership check: a driver
    can only view their own booking, not someone else's by guessing the URL id.
    """
    expire_overdue_bookings()
    booking = get_object_or_404(Booking, id=booking_id)

    if booking.user != request.user and not request.user.is_admin():
        messages.error(request, 'You are not authorized to view this booking.')
        return redirect('bookings:booking_list')

    return render(request, 'bookings/booking_detail.html', {'booking': booking})


@login_required
def booking_cancel(request, booking_id):
    """
    GET: show confirmation prompt ("are you sure?").
    POST: actually cancel - booking status becomes Cancelled,
    slot status reverts to Available so someone else can book it.
    Booking record itself is NEVER deleted - history preserved.
    """
    booking = get_object_or_404(Booking, id=booking_id)

    if booking.user != request.user:
        messages.error(request, 'You are not authorized to cancel this booking.')
        return redirect('bookings:booking_list')

    # can't cancel something already cancelled or already completed
    if booking.status in ['Cancelled', 'Completed']:
        messages.error(request, f'Booking already {booking.status.lower()}, cannot cancel.')
        return redirect('bookings:booking_detail', booking_id=booking.id)

    if request.method == 'POST':
        with transaction.atomic():
            booking.cancel_booking()  # model method - sets Cancelled + slot Available together
        messages.success(request, 'Booking cancelled successfully.')
        return redirect('bookings:booking_list')

    return render(request, 'bookings/booking_detail.html', {'booking': booking, 'confirm_cancel': True})


@admin_required
def admin_booking_list(request):
    expire_overdue_bookings()
    bookings = Booking.objects.select_related('user', 'station', 'charger', 'slot').order_by('-created_at')
    return render(request, 'bookings/admin_booking_list.html', {'bookings': bookings})


@login_required
def booking_checkin(request, booking_id):
    """
    Driver confirms physical arrival at the station.
    Does NOT create a charging session - just a presence signal that
    protects the booking from no-show auto-expiry and gives admin visibility.
    """
    booking = get_object_or_404(Booking, id=booking_id)

    if booking.user != request.user:
        messages.error(request, 'You are not authorized to check in for this booking.')
        return redirect('bookings:booking_list')

    if booking.status not in ['Pending', 'Confirmed']:
        messages.error(request, 'Check-in is only available for active bookings.')
        return redirect('bookings:booking_detail', booking_id=booking.id)

    if booking.checked_in_at:
        messages.info(request, 'You have already checked in for this booking.')
        return redirect('bookings:booking_detail', booking_id=booking.id)

    if request.method == 'POST':
        booking.check_in()
        messages.success(request, 'Checked in successfully. The station has been notified of your arrival.')
        return redirect('bookings:booking_detail', booking_id=booking.id)

    return redirect('bookings:booking_detail', booking_id=booking.id)