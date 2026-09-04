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