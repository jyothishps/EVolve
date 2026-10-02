from django.db import models


class ChargingSession(models.Model):
    """
    Represents actual/completed charging activity.
    No data_source field (removed by design decision).
    No IoT hardware - data may be manually/system recorded, labeled in UI as such.
    """

    WEATHER_CHOICES = (
        ('Clear', 'Clear'),
        ('Cloudy', 'Cloudy'),
        ('Rainy', 'Rainy'),
    )

    TRAFFIC_CHOICES = (
        (0, 'Low'),
        (1, 'Medium'),
        (2, 'High'),
    )

    booking = models.OneToOneField('bookings.Booking', on_delete=models.CASCADE)
    station = models.ForeignKey('stations.Station', on_delete=models.CASCADE)
    charger = models.ForeignKey('stations.Charger', on_delete=models.CASCADE)
    timestamp = models.DateTimeField()
    actual_load = models.FloatField(help_text="Station load in kW at time of session")
    charging_power_kW = models.FloatField()
    energy_kWh = models.FloatField(help_text="Energy delivered, NOT load")
    duration = models.FloatField(help_text="Duration in hours")
    traffic_density = models.IntegerField(choices=TRAFFIC_CHOICES, default=0)
    weather_condition = models.CharField(max_length=10, choices=WEATHER_CHOICES, default='Clear')
    created_at = models.DateTimeField(auto_now_add=True)

    def calculate_energy(self):
        self.energy_kWh = self.charging_power_kW * self.duration
        return self.energy_kWh

    def complete_session(self):
        self.booking.status = 'Completed'
        self.booking.save()
        self.booking.slot.status = 'Completed'
        self.booking.slot.save()

    def __str__(self):
        return f"Session #{self.id} - Booking #{self.booking.id}"
