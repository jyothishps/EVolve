from django.conf import settings
from django.db import models


class Booking(models.Model):
    """
    A reservation/intention to charge. NOT actual charging data.
    Does NOT update baseline ML dataset.
    """

    STATUS_CHOICES = (
        ('Pending', 'Pending'),
        ('Confirmed', 'Confirmed'),
        ('Cancelled', 'Cancelled'),
        ('Completed', 'Completed'),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    station = models.ForeignKey('stations.Station', on_delete=models.CASCADE)
    charger = models.ForeignKey('stations.Charger', on_delete=models.CASCADE)
    slot = models.ForeignKey('stations.ChargingSlot', on_delete=models.CASCADE)
    booking_date = models.DateField()
    booking_time = models.TimeField()
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)
    checked_in_at = models.DateTimeField(null=True, blank=True)

    def check_in(self):
        from django.utils import timezone
        self.checked_in_at = timezone.now()
        self.save()

    def confirm_booking(self):
        self.status = 'Confirmed'
        self.save()

    def cancel_booking(self):
        self.status = 'Cancelled'
        self.slot.status = 'Available'
        self.slot.save()
        self.save()

    def __str__(self):
        return f"Booking #{self.id} - {self.user.username} - {self.station.station_code}"
