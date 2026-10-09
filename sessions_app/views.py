from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from accounts.decorators import admin_required
from bookings.models import Booking
from .models import ChargingSession
from .forms import ChargingSessionForm
import random
from datetime import datetime, timedelta
from django.utils import timezone
from bookings.utils import get_slot_datetimes

@admin_required
def session_list(request):
    """
    Admin: view all charging sessions, newest first.
    """
    sessions = ChargingSession.objects.select_related(
        'booking', 'station', 'charger'
    ).order_by('-timestamp')
    return render(request, 'sessions_app/session_list.html', {'sessions': sessions})


@admin_required
def session_start(request, booking_id):
    """
    Admin starts a session for a Confirmed booking.
    Since there's no IoT hardware, values are auto-simulated:
    - charging_power_kW: pulled directly from the charger's rated power (real data, not guessed)
    - duration: calculated from the slot's start/end time (real data)
    - actual_load: simulated as rated power +/- 10% random variance (no sensor exists)
    - traffic_density / weather_condition: randomly pre-filled, admin can override before saving
    All simulated fields remain editable - admin confirms rather than blindly types numbers.
    """
    booking = get_object_or_404(Booking, id=booking_id)

    if booking.status != 'Confirmed':
        messages.error(request, 'Only Confirmed bookings can start a session.')
        return redirect('bookings:admin_booking_list')

    if hasattr(booking, 'chargingsession'):
        messages.error(request, 'A session already exists for this booking.')
        return redirect('sessions_app:session_detail', session_id=booking.chargingsession.id)

    # Guard: session can start only if driver checked in, or slot start time has arrived
    slot_start, _ = get_slot_datetimes(booking.slot)
    if not booking.checked_in_at and timezone.localtime() < slot_start:
        messages.error(
            request,
            'Cannot start session yet. The driver has not checked in and the slot '
            'has not started.'
        )
        return redirect('bookings:admin_booking_list')

    slot = booking.slot
    charger = booking.charger

    # Real, derivable values - not guessed
    rated_power = charger.charging_power_kW

    start_dt = datetime.combine(slot.date, slot.start_time)
    end_dt = datetime.combine(slot.date, slot.end_time)
    if end_dt <= start_dt:
        end_dt += timedelta(days=1)  # handles slots crossing midnight
    duration_hours = round((end_dt - start_dt).total_seconds() / 3600, 2)

    # Simulated values - no sensor hardware exists, clearly labeled in UI
    simulated_load = round(rated_power * random.uniform(0.85, 1.10), 2)
    simulated_traffic = random.choice([0, 1, 2])
    simulated_weather = random.choice(['Clear', 'Cloudy', 'Rainy'])

    initial_data = {
        'timestamp': timezone.localtime(),
        'actual_load': simulated_load,
        'charging_power_kW': rated_power,
        'duration': duration_hours,
        'traffic_density': simulated_traffic,
        'weather_condition': simulated_weather,
    }

    if request.method == 'POST':
        form = ChargingSessionForm(request.POST)
        if form.is_valid():
            session = form.save(commit=False)
            session.booking = booking
            session.station = booking.station
            session.charger = booking.charger
            session.calculate_energy()
            session.save()
            messages.success(request, 'Charging session started and recorded.')
            return redirect('sessions_app:session_detail', session_id=session.id)
    else:
        form = ChargingSessionForm(initial=initial_data)

    return render(request, 'sessions_app/session_start_form.html', {
        'form': form,
        'booking': booking,
        'rated_power': rated_power,
        'duration_hours': duration_hours,
    })


@admin_required
def session_detail(request, session_id):
    """
    Admin: view session details, option to mark as complete.
    """
    session = get_object_or_404(ChargingSession, id=session_id)
    return render(request, 'sessions_app/session_detail.html', {'session': session})


@admin_required
def session_complete(request, session_id):
    """
    Admin marks session as complete:
    - Booking status -> Completed
    - ChargingSlot status -> Completed
    """
    session = get_object_or_404(ChargingSession, id=session_id)

    if session.booking.status == 'Completed':
        messages.info(request, 'This session is already marked complete.')
        return redirect('sessions_app:session_detail', session_id=session.id)

    if request.method == 'POST':
        with transaction.atomic():
            session.complete_session()  # model method: updates booking + slot status
        messages.success(request, 'Session completed. Booking and slot marked Completed.')
        return redirect('sessions_app:session_detail', session_id=session.id)

    return redirect('sessions_app:session_detail', session_id=session.id)