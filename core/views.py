from django.shortcuts import render


def home(request):
    """
    Public home page for EV Charging Slot Booking System.
    Later phases will show login-based content here.
    """
    context = {
        'page_title': 'EV Charging Slot Booking System',
    }
    return render(request, 'home.html', context)