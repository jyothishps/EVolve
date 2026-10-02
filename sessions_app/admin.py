from django.contrib import admin
from .models import ChargingSession


@admin.register(ChargingSession)
class ChargingSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'booking', 'station', 'charger', 'timestamp', 'energy_kWh', 'duration')
    list_filter = ('weather_condition', 'traffic_density')
    search_fields = ('booking__id', 'station__station_code')
