from django.db import models
from decimal import Decimal, ROUND_HALF_UP
from django.utils import timezone


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

    PAYMENT_STATUS_CHOICES = (
        ('Unpaid', 'Unpaid'),
        ('Paid', 'Paid'),
    )
    PAYMENT_METHOD_CHOICES = (
        ('Cash', 'Cash'),
        ('UPI', 'UPI'),
        ('Card', 'Card'),
    )

    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    price_per_kWh_applied = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    payment_status = models.CharField(max_length=10, choices=PAYMENT_STATUS_CHOICES, default='Unpaid')
    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHOD_CHOICES, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    def calculate_energy(self):
        self.energy_kWh = self.charging_power_kW * self.duration
        return self.energy_kWh

    def complete_session(self):
        self.booking.status = 'Completed'
        self.booking.save()
        self.booking.slot.status = 'Completed'
        self.booking.slot.save()

    def generate_bill(self):
        """
        Amount = energy_kWh x station tariff. The rate is copied onto the
        session so a later tariff change does not rewrite old bills.
        """
        rate = self.station.price_per_kWh
        energy = Decimal(str(self.energy_kWh))
        self.price_per_kWh_applied = rate
        self.amount = (energy * rate).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        self.payment_status = 'Unpaid'
        self.save()

    def mark_paid(self, method):
        self.payment_status = 'Paid'
        self.payment_method = method
        self.paid_at = timezone.now()
        self.save()

    def __str__(self):
        return f"Session #{self.id} - Booking #{self.booking.id}"
