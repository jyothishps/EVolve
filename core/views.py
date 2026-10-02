from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.contrib import messages
from django.urls import reverse_lazy

from .decorators import admin_required
from .forms import StationForm, DriverRegisterForm, StyledAuthenticationForm
from .models import Station

from django.shortcuts import get_object_or_404
from .decorators import admin_required
from .models import Station, Charger
from .forms import StationForm, ChargerForm
from .models import ChargingSlot
from .forms import ChargingSlotForm

from django.db import transaction, IntegrityError
from django.utils import timezone
from .models import Booking


def home(request):
    context = {
        'page_title': 'EV Charging Slot Booking System',
    }
    return render(request, 'home.html', context)


def register_view(request):
    """
    Public registration - creates DRIVER accounts only.
    """
    if request.user.is_authenticated:
        return redirect('core:home')

    if request.method == 'POST':
        form = DriverRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Registration successful. Welcome!')
            return redirect('core:driver_dashboard')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = DriverRegisterForm()

    return render(request, 'registration/register.html', {'form': form})


class RoleBasedLoginView(LoginView):
    template_name = 'registration/login.html'
    authentication_form = StyledAuthenticationForm

    def get_success_url(self):
        user = self.request.user
        if user.is_admin():
            return reverse_lazy('core:admin_dashboard')
        return reverse_lazy('core:driver_dashboard')


def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('core:home')


@login_required
def driver_dashboard(request):
    if request.user.is_admin():
        return redirect('core:admin_dashboard')
    return render(request, 'user/dashboard.html')


@login_required
def admin_dashboard(request):
    if not request.user.is_admin():
        messages.error(request, 'Access denied. Admins only.')
        return redirect('core:driver_dashboard')
    return render(request, 'admin/dashboard.html')


@admin_required
def station_add(request):
    """
    Admin view: register a new charging station into the network.
    """
    form = StationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Station added successfully.')
        return redirect('core:admin_dashboard')
    return render(request, 'admin/station_form.html', {'form': form, 'action': 'Add'})


@login_required
def driver_station_map(request):
    """
    Driver view: map of all active stations using Leaflet + OpenStreetMap.
    """
    stations = Station.objects.filter(status='Active')
    return render(request, 'user/station_map.html', {'stations': stations})


# ---------- STATION MANAGEMENT (ADMIN) ----------

@admin_required
def station_list(request):
    stations = Station.objects.all().order_by('station_code')
    return render(request, 'admin/station_list.html', {'stations': stations})


@admin_required
def station_edit(request, station_id):
    station = get_object_or_404(Station, id=station_id)
    form = StationForm(request.POST or None, instance=station)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Station updated successfully.')
        return redirect('core:station_list')
    return render(request, 'admin/station_form.html', {'form': form, 'action': 'Edit'})


@admin_required
def station_delete(request, station_id):
    station = get_object_or_404(Station, id=station_id)
    if request.method == 'POST':
        station.delete()
        messages.success(request, 'Station deleted.')
        return redirect('core:station_list')
    return render(request, 'admin/station_confirm_delete.html', {'station': station})


# ---------- CHARGER MANAGEMENT (ADMIN) ----------

@admin_required
def charger_list(request):
    chargers = Charger.objects.select_related('station').order_by('station__station_code')
    return render(request, 'admin/charger_list.html', {'chargers': chargers})


@admin_required
def charger_add(request):
    form = ChargerForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Charger added successfully.')
        return redirect('core:charger_list')
    return render(request, 'admin/charger_form.html', {'form': form, 'action': 'Add'})


@admin_required
def charger_edit(request, charger_id):
    charger = get_object_or_404(Charger, id=charger_id)
    form = ChargerForm(request.POST or None, instance=charger)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Charger updated successfully.')
        return redirect('core:charger_list')
    return render(request, 'admin/charger_form.html', {'form': form, 'action': 'Edit'})


@admin_required
def charger_delete(request, charger_id):
    charger = get_object_or_404(Charger, id=charger_id)
    if request.method == 'POST':
        charger.delete()
        messages.success(request, 'Charger deleted.')
        return redirect('core:charger_list')
    return redirect('core:charger_list')

# ---------- SLOT MANAGEMENT (ADMIN) ----------

@admin_required
def slot_list(request):
    slots = ChargingSlot.objects.select_related('station', 'charger').order_by('-date')
    return render(request, 'admin/slot_list.html', {'slots': slots})


@admin_required
def slot_add(request):
    form = ChargingSlotForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Slot created successfully.')
        return redirect('core:slot_list')
    return render(request, 'admin/slot_form.html', {'form': form, 'action': 'Add'})


@admin_required
def slot_edit(request, slot_id):
    slot = get_object_or_404(ChargingSlot, id=slot_id)
    form = ChargingSlotForm(request.POST or None, instance=slot)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Slot updated successfully.')
        return redirect('core:slot_list')
    return render(request, 'admin/slot_form.html', {'form': form, 'action': 'Edit'})


@admin_required
def slot_delete(request, slot_id):
    slot = get_object_or_404(ChargingSlot, id=slot_id)
    if request.method == 'POST':
        slot.delete()
        messages.success(request, 'Slot deleted.')
        return redirect('core:slot_list')
    return redirect('core:slot_list')


# ---------- DRIVER STATION BROWSING ----------

@login_required
def driver_station_list(request):
    stations = Station.objects.filter(status='Active').order_by('station_code')
    return render(request, 'user/station_list.html', {'stations': stations})


@login_required
def driver_station_detail(request, station_id):
    station = get_object_or_404(Station, id=station_id)
    chargers = Charger.objects.filter(station=station)
    available_slots = ChargingSlot.objects.filter(
        station=station, status='Available'
    ).order_by('date', 'start_time')

    context = {
        'station': station,
        'chargers': chargers,
        'available_slots': available_slots,
    }
    return render(request, 'user/station_detail.html', context)


# ---------- BOOKING CORE (DRIVER) ----------

@login_required
def booking_create(request, slot_id):
    """
    GET: show confirmation page with slot details.
    POST: create the actual booking, inside a DB transaction to prevent
    two drivers booking the same slot at the same time (double booking).
    """
    slot = get_object_or_404(ChargingSlot, id=slot_id)

    # Admin should not book slots - booking is a driver action only
    if request.user.is_admin():
        messages.error(request, 'Admins cannot make bookings.')
        return redirect('core:admin_dashboard')

    # Reject slots whose date already passed - can't book yesterday's slot
    if slot.date < timezone.localdate():
        messages.error(request, 'Cannot book a slot in the past.')
        return redirect('core:driver_station_detail', station_id=slot.station.id)

    # Reject booking on inactive/maintenance stations
    if slot.station.status != 'Active':
        messages.error(request, 'This station is not currently active.')
        return redirect('core:driver_station_list')

    # Reject booking if charger itself unavailable (Occupied/Maintenance/Offline)
    if slot.charger.status != 'Available':
        messages.error(request, 'Selected charger is not available.')
        return redirect('core:driver_station_detail', station_id=slot.station.id)

    if request.method == 'POST':
        try:
            # atomic block: either everything inside succeeds, or nothing does
            with transaction.atomic():
                # select_for_update locks this row until transaction ends -
                # if two requests hit here at same time, second one waits,
                # then re-checks status below and correctly sees it's taken
                locked_slot = ChargingSlot.objects.select_for_update().get(id=slot.id)

                if locked_slot.status != 'Available':
                    messages.error(request, 'Sorry, this slot is no longer available.')
                    return redirect('core:driver_station_detail', station_id=slot.station.id)

                booking = Booking.objects.create(
                    user=request.user,
                    station=locked_slot.station,
                    charger=locked_slot.charger,
                    slot=locked_slot,
                    booking_date=locked_slot.date,
                    booking_time=locked_slot.start_time,
                    status='Confirmed',
                )

                # mark slot as taken so nobody else can book it
                locked_slot.status = 'Reserved'
                locked_slot.save()

            messages.success(request, 'Booking confirmed successfully.')
            return redirect('core:booking_detail', booking_id=booking.id)

        except IntegrityError:
            # safety net - shouldn't normally trigger given checks above,
            # but protects against rare DB-level constraint clashes
            messages.error(request, 'This slot was already booked. Please choose another.')
            return redirect('core:driver_station_detail', station_id=slot.station.id)

    # GET request - just show the confirmation page
    return render(request, 'user/booking_confirm.html', {'slot': slot})


@login_required
def booking_list(request):
    """
    Driver sees only their own bookings, newest first.
    select_related pulls station/charger/slot data in same query -
    avoids extra DB hits per row when template accesses booking.station.name etc.
    """
    bookings = Booking.objects.filter(user=request.user).select_related(
        'station', 'charger', 'slot'
    ).order_by('-created_at')
    return render(request, 'user/booking_list.html', {'bookings': bookings})


@login_required
def booking_detail(request, booking_id):
    """
    Show one booking's full details. Ownership check: a driver
    can only view their own booking, not someone else's by guessing the URL id.
    """
    booking = get_object_or_404(Booking, id=booking_id)

    if booking.user != request.user and not request.user.is_admin():
        messages.error(request, 'You are not authorized to view this booking.')
        return redirect('core:booking_list')

    return render(request, 'user/booking_detail.html', {'booking': booking})


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
        return redirect('core:booking_list')

    # can't cancel something already cancelled or already completed
    if booking.status in ['Cancelled', 'Completed']:
        messages.error(request, f'Booking already {booking.status.lower()}, cannot cancel.')
        return redirect('core:booking_detail', booking_id=booking.id)

    if request.method == 'POST':
        with transaction.atomic():
            booking.cancel_booking()  # model method - sets Cancelled + slot Available together
        messages.success(request, 'Booking cancelled successfully.')
        return redirect('core:booking_list')

    return render(request, 'user/booking_detail.html', {'booking': booking, 'confirm_cancel': True})