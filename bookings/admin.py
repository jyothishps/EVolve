from django.contrib import admin
from .models import Booking


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'station', 'charger', 'booking_date', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('user__username', 'station__station_code', 'station__name')
