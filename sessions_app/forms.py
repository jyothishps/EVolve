from django import forms
from .models import ChargingSession


class ChargingSessionForm(forms.ModelForm):
    """
    Used when admin starts a session - captures operational data.
    No data_source field by design. Traffic/weather clearly estimated,
    not real IoT data (no hardware in this project).
    """
    class Meta:
        model = ChargingSession
        fields = ['timestamp', 'actual_load', 'charging_power_kW', 'duration',
                   'traffic_density', 'weather_condition']
        widgets = {
            'timestamp': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})