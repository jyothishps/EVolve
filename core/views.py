from django.shortcuts import render


def home(request):
    context = {
        'page_title': 'EV Charging Slot Booking System',
    }
    return render(request, 'home.html', context)