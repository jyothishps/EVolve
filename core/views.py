from django.shortcuts import render, redirect


def home(request):
    if request.user.is_authenticated and request.user.is_admin():
        return redirect('accounts:admin_dashboard')
    context = {
        'page_title': 'EV Charging Slot Booking System',
    }
    return render(request, 'home.html', context)