from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Station, Charger, ChargingSlot, Booking, ChargingSession


class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'role', 'is_active', 'created_at')
    list_filter = ('role', 'is_active')
    fieldsets = UserAdmin.fieldsets + (
        ('Role Info', {'fields': ('role',)}),
    )


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


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'station', 'charger', 'booking_date', 'status', 'created_at')
    list_filter = ('status',)


@admin.register(ChargingSession)
class ChargingSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'booking', 'station', 'actual_load', 'energy_kWh', 'timestamp')
    list_filter = ('weather_condition', 'traffic_density')


admin.site.register(User, CustomUserAdmin)