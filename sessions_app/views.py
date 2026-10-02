from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from accounts.decorators import admin_required
from bookings.models import Booking
from .models import ChargingSession
from .forms import ChargingSessionForm


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
    Creates a ChargingSession record with entered data.
    Note: no IoT hardware - traffic/weather values here are
    estimated/simulated for demonstration, labeled as such in template.
    """
    booking = get_object_or_404(Booking, id=booking_id)

    if booking.status != 'Confirmed':
        messages.error(request, 'Only Confirmed bookings can start a session.')
        return redirect('bookings:admin_booking_list')

    if hasattr(booking, 'chargingsession'):
        messages.error(request, 'A session already exists for this booking.')
        return redirect('sessions_app:session_detail', session_id=booking.chargingsession.id)

    if request.method == 'POST':
        form = ChargingSessionForm(request.POST)
        if form.is_valid():
            session = form.save(commit=False)
            session.booking = booking
            session.station = booking.station
            session.charger = booking.charger
            session.calculate_energy()  # energy_kWh = power * duration
            session.save()
            messages.success(request, 'Charging session started and recorded.')
            return redirect('sessions_app:session_detail', session_id=session.id)
    else:
        form = ChargingSessionForm()

    return render(request, 'sessions_app/session_start_form.html', {'form': form, 'booking': booking})


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