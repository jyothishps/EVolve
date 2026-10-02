from django.contrib import admin
from .models import Station, Charger, ChargingSlot


@admin.register(Station)
class StationAdmin(admin.ModelAdmin):
    list_display = ('station_code', 'name', 'status', 'number_of_chargers', 'created_at')
    list_filter = ('status',)
    search_fields = ('station_code', 'name')


@admin.register(Charger)
class ChargerAdmin(admin.ModelAdmin):
    list_display = ('id', 'station', 'charging_power_kW', 'connector_type', 'status')
    list_filter = ('status', 'connector_type')


@admin.register(ChargingSlot)
class ChargingSlotAdmin(admin.ModelAdmin):
    list_display = ('id', 'station', 'charger', 'date', 'start_time', 'end_time', 'status')
    list_filter = ('status', 'date')
