from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.contrib import messages
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404
from .decorators import admin_required
from .forms import StationForm, ChargerForm, ChargingSlotForm
from .models import Station, Charger, ChargingSlot
from .forms import DriverRegisterForm
from .forms import DriverRegisterForm, StyledAuthenticationForm
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
def station_list(request):
    stations = Station.objects.all().order_by('station_code')
    return render(request, 'admin/station_list.html', {'stations': stations})

@admin_required
def station_add(request):
    form = StationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Station added successfully.')
        return redirect('core:station_list')
    return render(request, 'admin/station_form.html', {'form': form, 'action': 'Add'})

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

@admin_required
def charger_list(request):
    chargers = Charger.objects.all().select_related('station').order_by('station__station_code')
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
    return render(request, 'admin/charger_list.html', {'chargers': Charger.objects.all()})

@admin_required
def slot_list(request):
    slots = ChargingSlot.objects.all().select_related('station', 'charger').order_by('-date')
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
    return render(request, 'admin/slot_list.html', {'slots': ChargingSlot.objects.all()})



# ---------- DRIVER STATION BROWSING ----------

@login_required
def driver_station_list(request):
    """
    Driver view: list all active stations.
    """
    stations = Station.objects.filter(status='Active').order_by('station_code')
    return render(request, 'user/station_list.html', {'stations': stations})


@login_required
def driver_station_detail(request, station_id):
    """
    Driver view: station details, chargers, and available slots.
    """
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


@login_required
def driver_station_map(request):
    """
    Driver view: map of all active stations using Leaflet + OpenStreetMap.
    """
    stations = Station.objects.filter(status='Active')
    return render(request, 'user/station_map.html', {'stations': stations})


# ---------- BOOKING SYSTEM (DRIVER) ----------

@login_required
def booking_create(request, slot_id):
    """
    Show confirmation page and create booking on POST.
    Uses transaction + row lock to prevent double booking.
    """
    slot = get_object_or_404(ChargingSlot, id=slot_id)

    if request.user.is_admin():
        messages.error(request, 'Admins cannot make bookings.')
        return redirect('core:admin_dashboard')

    # Reject past slots
    if slot.date < timezone.localdate():
        messages.error(request, 'Cannot book a slot in the past.')
        return redirect('core:driver_station_detail', station_id=slot.station.id)

    # Reject inactive station or unavailable charger
    if slot.station.status != 'Active':
        messages.error(request, 'This station is not currently active.')
        return redirect('core:driver_station_list')

    if slot.charger.status not in ['Available']:
        messages.error(request, 'Selected charger is not available.')
        return redirect('core:driver_station_detail', station_id=slot.station.id)

    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Lock the slot row to prevent race condition double booking
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

                locked_slot.status = 'Reserved'
                locked_slot.save()

            messages.success(request, 'Booking confirmed successfully.')
            return redirect('core:booking_detail', booking_id=booking.id)

        except IntegrityError:
            messages.error(request, 'This slot was already booked. Please choose another.')
            return redirect('core:driver_station_detail', station_id=slot.station.id)

    return render(request, 'user/booking_confirm.html', {'slot': slot})


@login_required
def booking_list(request):
    """
    Driver: view own booking history.
    """
    bookings = Booking.objects.filter(user=request.user).select_related(
        'station', 'charger', 'slot'
    ).order_by('-created_at')
    return render(request, 'user/booking_list.html', {'bookings': bookings})


@login_required
def booking_detail(request, booking_id):
    """
    Driver: view details of a specific booking. Only owner can view.
    """
    booking = get_object_or_404(Booking, id=booking_id)

    if booking.user != request.user and not request.user.is_admin():
        messages.error(request, 'You are not authorized to view this booking.')
        return redirect('core:booking_list')

    return render(request, 'user/booking_detail.html', {'booking': booking})


@login_required
def booking_cancel(request, booking_id):
    """
    Driver: cancel own booking. Slot becomes Available again.
    """
    booking = get_object_or_404(Booking, id=booking_id)

    if booking.user != request.user:
        messages.error(request, 'You are not authorized to cancel this booking.')
        return redirect('core:booking_list')

    if booking.status in ['Cancelled', 'Completed']:
        messages.error(request, f'Booking already {booking.status.lower()}, cannot cancel.')
        return redirect('core:booking_detail', booking_id=booking.id)

    if request.method == 'POST':
        with transaction.atomic():
            booking.cancel_booking()  # model method: sets Cancelled + slot Available
        messages.success(request, 'Booking cancelled successfully.')
        return redirect('core:booking_list')

    return render(request, 'user/booking_detail.html', {'booking': booking, 'confirm_cancel': True})


# ---------- BOOKING MANAGEMENT (ADMIN) ----------

@admin_required
def admin_booking_list(request):
    """
    Admin: view all bookings across all users.
    """
    bookings = Booking.objects.select_related('user', 'station', 'charger', 'slot').order_by('-created_at')
    return render(request, 'admin/booking_list.html', {'bookings': bookings})


@admin_required
def admin_booking_update_status(request, booking_id):
    """
    Admin: update booking status manually (e.g. mark Confirmed/Cancelled).
    """
    booking = get_object_or_404(Booking, id=booking_id)

    if request.method == 'POST':
        new_status = request.POST.get('status')
        valid_statuses = dict(Booking.STATUS_CHOICES).keys()

        if new_status not in valid_statuses:
            messages.error(request, 'Invalid status.')
            return redirect('core:admin_booking_list')

        with transaction.atomic():
            booking.status = new_status
            booking.save()

            if new_status == 'Cancelled':
                booking.slot.status = 'Available'
                booking.slot.save()

        messages.success(request, 'Booking status updated.')
        return redirect('core:admin_booking_list')

    return redirect('core:admin_booking_list')