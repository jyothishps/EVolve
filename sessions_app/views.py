from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone

from accounts.decorators import admin_required
from bookings.models import Booking
from .models import ChargingSession


@admin_required
def session_start(request, booking_id):
    """
    Start/record a charging session for a confirmed booking.
    """
    booking = get_object_or_404(Booking, id=booking_id, status='Confirmed')
    if hasattr(booking, 'chargingsession'):
        messages.warning(request, 'A session already exists for this booking.')
        return redirect('bookings:booking_detail', booking_id=booking.id)

    if request.method == 'POST':
        actual_load = float(request.POST.get('actual_load', 50.0))
        charging_power = float(request.POST.get('charging_power_kW', booking.charger.charging_power_kW))
        duration = float(request.POST.get('duration', 1.0))
        traffic_density = int(request.POST.get('traffic_density', 0))
        weather_condition = request.POST.get('weather_condition', 'Clear')

        session = ChargingSession.objects.create(
            booking=booking,
            station=booking.station,
            charger=booking.charger,
            timestamp=timezone.now(),
            actual_load=actual_load,
            charging_power_kW=charging_power,
            energy_kWh=charging_power * duration,
            duration=duration,
            traffic_density=traffic_density,
            weather_condition=weather_condition,
        )
        messages.success(request, f'Charging session #{session.id} started.')
        return redirect('bookings:booking_detail', booking_id=booking.id)

    return render(request, 'sessions_app/session_form.html', {'booking': booking})


@admin_required
def session_complete(request, session_id):
    """
    Complete an active charging session.
    """
    session = get_object_or_404(ChargingSession, id=session_id)
    if request.method == 'POST':
        session.complete_session()
        messages.success(request, f'Session #{session.id} marked as completed.')
    return redirect('bookings:booking_detail', booking_id=session.booking.id)
