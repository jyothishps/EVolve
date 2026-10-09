from django import forms
from .models import Station, Charger, ChargingSlot
from django.core.exceptions import ValidationError


class StationForm(forms.ModelForm):
    class Meta:
        model = Station
        fields = [
            'station_code', 'name', 'address', 'latitude', 'longitude',
            'location_type', 'number_of_chargers', 'status', 'description'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})


class ChargerForm(forms.ModelForm):
    class Meta:
        model = Charger
        fields = ['station', 'charging_power_kW', 'connector_type', 'status']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})


class ChargingSlotForm(forms.ModelForm):
    class Meta:
        model = ChargingSlot
        fields = ['station', 'charger', 'date', 'start_time', 'end_time', 'status']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'type': 'time'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})

    def clean(self):
        cleaned = super().clean()
        station = cleaned.get('station')
        charger = cleaned.get('charger')
        date = cleaned.get('date')
        start = cleaned.get('start_time')
        end = cleaned.get('end_time')

        # Skip extra checks if any required field already failed basic validation
        if not all([station, charger, date, start, end]):
            return cleaned

        # Rule 1: charger must belong to the selected station
        if charger.station_id != station.id:
            raise ValidationError('Selected charger does not belong to the selected station.')

        # Rule 2: end must be after start (no zero-length or midnight-crossing slots)
        if end <= start:
            raise ValidationError('End time must be after start time.')

        # Rule 3: no overlapping slot on the same charger and date
        overlapping = ChargingSlot.objects.filter(
            charger=charger,
            date=date,
            start_time__lt=end,
            end_time__gt=start,
        ).exclude(status='Cancelled')

        if self.instance.pk:
            overlapping = overlapping.exclude(pk=self.instance.pk)

        if overlapping.exists():
            clash = overlapping.first()
            raise ValidationError(
                f'This overlaps an existing slot on this charger '
                f'({clash.start_time.strftime("%H:%M")} - {clash.end_time.strftime("%H:%M")}).'
            )

        return cleaned
