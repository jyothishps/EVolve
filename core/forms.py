from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm

from .models import User, Station, Charger, ChargingSlot


class DriverRegisterForm(UserCreationForm):
    """
    Registration form for Drivers only.
    Admin accounts created separately (via createsuperuser or admin panel).
    """
    email = forms.EmailField(required=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = 'DRIVER'
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user


class StyledAuthenticationForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'class': 'form-control'})
        self.fields['password'].widget.attrs.update({'class': 'form-control'})


class StationForm(forms.ModelForm):
    class Meta:
        model = Station
        fields = ['station_code', 'name', 'address', 'latitude', 'longitude',
                  'location_type', 'number_of_chargers', 'status', 'description']

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