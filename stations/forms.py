from django import forms
from .models import Station, Charger, ChargingSlot


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
