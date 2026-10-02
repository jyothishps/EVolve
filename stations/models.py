from django.db import models


class Station(models.Model):
    """
    Charging station location. Latitude/longitude used ONLY for map display,
    never as ML input features.
    """

    STATUS_CHOICES = (
        ('Active', 'Active'),
        ('Inactive', 'Inactive'),
        ('Maintenance', 'Maintenance'),
    )

    station_code = models.CharField(max_length=10, unique=True, help_text="e.g. ST001")
    name = models.CharField(max_length=150)
    address = models.CharField(max_length=255)
    latitude = models.FloatField()
    longitude = models.FloatField()
    location_type = models.CharField(max_length=50, blank=True, help_text="e.g. Highway, Mall, City Center")
    number_of_chargers = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='Active')
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def check_availability(self):
        return self.status == 'Active'

    def get_available_slots(self):
        return self.chargingslot_set.filter(status='Available')

    def __str__(self):
        return f"{self.station_code} - {self.name}"


class Charger(models.Model):
    """
    A charger belongs to a station. A station can have multiple chargers.
    """

    STATUS_CHOICES = (
        ('Available', 'Available'),
        ('Occupied', 'Occupied'),
        ('Maintenance', 'Maintenance'),
        ('Offline', 'Offline'),
    )

    CONNECTOR_CHOICES = (
        ('CCS2', 'CCS2'),
        ('CHAdeMO', 'CHAdeMO'),
        ('Type2', 'Type2'),
        ('GB/T', 'GB/T'),
    )

    station = models.ForeignKey(Station, on_delete=models.CASCADE)
    charging_power_kW = models.FloatField()
    connector_type = models.CharField(max_length=20, choices=CONNECTOR_CHOICES)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='Available')

    def check_status(self):
        return self.status

    def set_status(self, new_status):
        self.status = new_status
        self.save()

    def __str__(self):
        return f"Charger {self.id} - {self.station.station_code} ({self.charging_power_kW}kW)"


class ChargingSlot(models.Model):
    """
    A time slot on a specific charger at a specific station.
    A slot can have at most one active booking.
    """

    STATUS_CHOICES = (
        ('Available', 'Available'),
        ('Reserved', 'Reserved'),
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
    )

    station = models.ForeignKey(Station, on_delete=models.CASCADE)
    charger = models.ForeignKey(Charger, on_delete=models.CASCADE)
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='Available')

    def check_availability(self):
        return self.status == 'Available'

    def reserve_slot(self):
        self.status = 'Reserved'
        self.save()

    class Meta:
        ordering = ['date', 'start_time']

    def __str__(self):
        return f"{self.station.station_code} | {self.date} {self.start_time}-{self.end_time} | {self.status}"
