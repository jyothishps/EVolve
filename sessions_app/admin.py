from django.contrib import admin
from .models import ChargingSession


@admin.register(ChargingSession)
class ChargingSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'booking', 'station', 'actual_load', 'energy_kWh', 'timestamp')
    list_filter = ('weather_condition', 'traffic_density')