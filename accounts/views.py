from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.contrib import messages
from django.urls import reverse_lazy

from .forms import DriverRegisterForm, StyledAuthenticationForm
from .dashboard_data import build_dashboard_analytics


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
            return redirect('accounts:driver_dashboard')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = DriverRegisterForm()

    return render(request, 'accounts/register.html', {'form': form})


class RoleBasedLoginView(LoginView):
    template_name = 'accounts/login.html'
    authentication_form = StyledAuthenticationForm

    def get_success_url(self):
        user = self.request.user
        if user.is_admin():
            return reverse_lazy('accounts:admin_dashboard')
        return reverse_lazy('accounts:driver_dashboard')


def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('core:home')


@login_required
def driver_dashboard(request):
    if request.user.is_admin():
        return redirect('accounts:admin_dashboard')
    
    from bookings.models import Booking
    from bookings.utils import expire_overdue_bookings
    
    expire_overdue_bookings()
    user_bookings = Booking.objects.filter(user=request.user).select_related('station', 'charger', 'slot')
    recent_bookings = user_bookings.order_by('-created_at')[:5]
    total_bookings = user_bookings.count()
    active_bookings = user_bookings.filter(status__in=['Pending', 'Confirmed']).count()
    completed_bookings = user_bookings.filter(status='Completed').count()
    next_booking = user_bookings.filter(status='Confirmed').order_by('booking_date', 'booking_time').first()

    return render(request, 'accounts/dashboard.html', {
        'recent_bookings': recent_bookings,
        'total_bookings': total_bookings,
        'active_bookings': active_bookings,
        'completed_bookings': completed_bookings,
        'next_booking': next_booking,
    })



@login_required
def admin_dashboard(request):
    if not request.user.is_admin():
        messages.error(request, 'Access denied. Admins only.')
        return redirect('accounts:driver_dashboard')

    from stations.models import Station, Charger, ChargingSlot
    from bookings.models import Booking
    from sessions_app.models import ChargingSession
    from django.db.models import Sum
    from bookings.utils import expire_overdue_bookings

    expire_overdue_bookings()

    total_stations = Station.objects.count()
    active_stations = Station.objects.filter(status='Active').count()

    total_chargers = Charger.objects.count()
    available_chargers = Charger.objects.filter(status='Available').count()

    total_slots = ChargingSlot.objects.count()
    available_slots = ChargingSlot.objects.filter(status='Available').count()

    total_bookings = Booking.objects.count()
    confirmed_bookings = Booking.objects.filter(status='Confirmed').count()

    # Checked-in queue: drivers at station awaiting session start
    checked_in_qs = Booking.objects.filter(
        checked_in_at__isnull=False,
        chargingsession__isnull=True,
        status__in=['Pending', 'Confirmed']
    ).select_related('user', 'station', 'charger', 'slot').order_by('-checked_in_at')
    checked_in_count = checked_in_qs.count()

    # Energy and revenue telemetry
    total_energy = ChargingSession.objects.aggregate(total=Sum('energy_kWh'))['total'] or 0.0
    total_sessions = ChargingSession.objects.count()
    reservation_revenue = Booking.objects.filter(payment_status='Paid').aggregate(total=Sum('booking_fee'))['total'] or 0.0
    charging_revenue = ChargingSession.objects.filter(payment_status='Paid').aggregate(total=Sum('amount'))['total'] or 0.0
    total_revenue = float(reservation_revenue) + float(charging_revenue)

    # Recent activity
    recent_bookings = Booking.objects.select_related('user', 'station', 'charger', 'slot').order_by('-created_at')[:6]
    recent_sessions = ChargingSession.objects.select_related('booking', 'station', 'charger').order_by('-created_at')[:6]

    context = {
        'total_stations': total_stations,
        'active_stations': active_stations,
        'total_chargers': total_chargers,
        'available_chargers': available_chargers,
        'total_slots': total_slots,
        'available_slots': available_slots,
        'total_bookings': total_bookings,
        'confirmed_bookings': confirmed_bookings,
        'checked_in_bookings': checked_in_qs[:5],
        'checked_in_count': checked_in_count,
        'total_energy': round(total_energy, 1),
        'total_sessions': total_sessions,
        'reservation_revenue': reservation_revenue,
        'charging_revenue': charging_revenue,
        'total_revenue': round(total_revenue, 2),
        'recent_bookings': recent_bookings,
        'recent_sessions': recent_sessions,
    }
    context.update(build_dashboard_analytics())

    return render(request, 'accounts/admin_dashboard.html', context)
