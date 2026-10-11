from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from accounts.decorators import admin_required
from .models import Station, Charger, ChargingSlot
from .forms import StationForm, ChargerForm, ChargingSlotForm
from bookings.utils import expire_overdue_bookings
from django.utils import timezone
from bookings.models import Booking
from ml_prediction.predictor import predict_slots
from django.utils import timezone
from ml_prediction.config import VEHICLE_TYPES, BATTERY_RANGE_KWH, INITIAL_SOC_RANGE, DEFAULT_BATTERY_KWH, DEFAULT_INITIAL_SOC
from ml_prediction.recommender import rank_slots

# ---------- STATION MANAGEMENT (ADMIN) ----------

@admin_required
def station_add(request):
    """
    Admin view: register a new charging station into the network.
    """
    form = StationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Station added successfully.')
        return redirect('accounts:admin_dashboard')
    return render(request, 'stations/admin_station_form.html', {'form': form, 'action': 'Add'})


@admin_required
def station_list(request):
    stations = Station.objects.all().order_by('station_code')
    return render(request, 'stations/admin_station_list.html', {'stations': stations})


@admin_required
def station_edit(request, station_id):
    station = get_object_or_404(Station, id=station_id)
    form = StationForm(request.POST or None, instance=station)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Station updated successfully.')
        return redirect('stations:station_list')
    return render(request, 'stations/admin_station_form.html', {'form': form, 'action': 'Edit'})


@admin_required
def station_delete(request, station_id):
    station = get_object_or_404(Station, id=station_id)
    if request.method == 'POST':
        station.delete()
        messages.success(request, 'Station deleted.')
        return redirect('stations:station_list')
    return render(request, 'stations/admin_station_confirm_delete.html', {'station': station})


# ---------- CHARGER MANAGEMENT (ADMIN) ----------

@admin_required
def charger_list(request):
    chargers = Charger.objects.select_related('station').order_by('station__station_code')
    return render(request, 'stations/admin_charger_list.html', {'chargers': chargers})


@admin_required
def charger_add(request):
    form = ChargerForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Charger added successfully.')
        return redirect('stations:charger_list')
    return render(request, 'stations/admin_charger_form.html', {'form': form, 'action': 'Add'})


@admin_required
def charger_edit(request, charger_id):
    charger = get_object_or_404(Charger, id=charger_id)
    form = ChargerForm(request.POST or None, instance=charger)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Charger updated successfully.')
        return redirect('stations:charger_list')
    return render(request, 'stations/admin_charger_form.html', {'form': form, 'action': 'Edit'})


@admin_required
def charger_delete(request, charger_id):
    charger = get_object_or_404(Charger, id=charger_id)
    if request.method == 'POST':
        charger.delete()
        messages.success(request, 'Charger deleted.')
        return redirect('stations:charger_list')
    return redirect('stations:charger_list')


# ---------- SLOT MANAGEMENT (ADMIN) ----------

@admin_required
def slot_list(request):
    expire_overdue_bookings()
    slots = ChargingSlot.objects.select_related('station', 'charger').order_by('-date')
    return render(request, 'stations/admin_slot_list.html', {'slots': slots})


@admin_required
def slot_add(request):
    form = ChargingSlotForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Slot created successfully.')
        return redirect('stations:slot_list')
    return render(request, 'stations/admin_slot_form.html', {'form': form, 'action': 'Add'})


@admin_required
def slot_edit(request, slot_id):
    slot = get_object_or_404(ChargingSlot, id=slot_id)
    form = ChargingSlotForm(request.POST or None, instance=slot)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Slot updated successfully.')
        return redirect('stations:slot_list')
    return render(request, 'stations/admin_slot_form.html', {'form': form, 'action': 'Edit'})


@admin_required
def slot_delete(request, slot_id):
    slot = get_object_or_404(ChargingSlot, id=slot_id)
    if request.method == 'POST':
        slot.delete()
        messages.success(request, 'Slot deleted.')
        return redirect('stations:slot_list')
    return redirect('stations:slot_list')


# ---------- DRIVER STATION BROWSING & MAP ----------

@login_required
def driver_station_map(request):
    """
    Driver view: map of all active stations using Leaflet + OpenStreetMap.
    """
    stations = Station.objects.filter(status='Active')
    return render(request, 'stations/station_map.html', {'stations': stations})


@login_required
def driver_station_list(request):
    expire_overdue_bookings()
    stations = Station.objects.filter(status='Active').order_by('station_code')
    return render(request, 'stations/station_list.html', {'stations': stations})

def _read_vehicle_inputs(request):
    """Read optional vehicle inputs from the query string; clamp to training ranges."""
    vehicle_type = request.GET.get('vehicle_type', 'Car')
    if vehicle_type not in VEHICLE_TYPES:
        vehicle_type = 'Car'

    def number(name, default, low, high):
        try:
            value = float(request.GET.get(name, default))
        except (TypeError, ValueError):
            value = default
        return max(low, min(high, value))

    return {
        'vehicle_type': vehicle_type,
        'battery_kwh': number('battery_kwh', DEFAULT_BATTERY_KWH, *BATTERY_RANGE_KWH),
        'initial_soc': number('initial_soc', DEFAULT_INITIAL_SOC, *INITIAL_SOC_RANGE),
    }


@login_required
def driver_station_detail(request, station_id):
    expire_overdue_bookings()
    station = get_object_or_404(Station, id=station_id)
    chargers = Charger.objects.filter(station=station)

    # Only future slots are worth recommending
    available_slots = list(
        ChargingSlot.objects.filter(
            station=station, status='Available', date__gte=timezone.localdate()
        ).select_related('station', 'charger').order_by('date', 'start_time')
    )

    vehicle = _read_vehicle_inputs(request)
    predictions = predict_slots(available_slots, vehicle)
    for slot in available_slots:
        slot.prediction = predictions[slot.id]

    ranked_slots, best_slot = rank_slots(available_slots)

    context = {
        'station': station,
        'chargers': chargers,
        'available_slots': ranked_slots,
        'best_slot': best_slot,
        'vehicle': vehicle,
        'vehicle_types': VEHICLE_TYPES,
        'battery_min': BATTERY_RANGE_KWH[0],
        'battery_max': BATTERY_RANGE_KWH[1],
        'soc_min': INITIAL_SOC_RANGE[0],
        'soc_max': INITIAL_SOC_RANGE[1],
    }
    return render(request, 'stations/station_detail.html', context)

@admin_required
def slot_reopen(request, slot_id):
    """
    Admin reopens a Completed/Cancelled slot so it can be booked again.
    Refused if the slot still has an active (Pending/Confirmed) booking.
    """
    slot = get_object_or_404(ChargingSlot, id=slot_id)

    if request.method != 'POST':
        return redirect('stations:slot_list')

    if slot.status not in ['Completed', 'Cancelled']:
        messages.error(request, 'Only Completed or Cancelled slots can be reopened.')
        return redirect('stations:slot_list')

    if Booking.objects.filter(slot=slot, status__in=['Pending', 'Confirmed']).exists():
        messages.error(request, 'This slot still has an active booking. Cancel that booking first.')
        return redirect('stations:slot_list')

    slot.status = 'Available'
    slot.save()

    if slot.date < timezone.localdate():
        messages.warning(request, 'Slot reopened, but its date is in the past so drivers cannot book it.')
    else:
        messages.success(request, 'Slot reopened and available for booking.')
    return redirect('stations:slot_list')

