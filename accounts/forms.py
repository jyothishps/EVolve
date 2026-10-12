from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import User


class DriverRegisterForm(UserCreationForm):
    """
    Registration form for Drivers.
    Admin accounts are provisioned via createsuperuser or Django administration.
    """
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control form-control-ev',
            'placeholder': 'driver@example.com',
            'autocomplete': 'email',
        })
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'username' in self.fields:
            self.fields['username'].widget.attrs.update({
                'class': 'form-control form-control-ev',
                'placeholder': 'Choose a unique username',
                'autocomplete': 'username',
            })
        if 'email' in self.fields:
            self.fields['email'].widget.attrs.update({
                'class': 'form-control form-control-ev',
                'placeholder': 'driver@example.com',
                'autocomplete': 'email',
            })
        if 'password1' in self.fields:
            self.fields['password1'].widget.attrs.update({
                'class': 'form-control form-control-ev',
                'placeholder': 'Create strong password',
                'autocomplete': 'new-password',
            })
        if 'password2' in self.fields:
            self.fields['password2'].widget.attrs.update({
                'class': 'form-control form-control-ev',
                'placeholder': 'Confirm your password',
                'autocomplete': 'new-password',
            })

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
        if 'username' in self.fields:
            self.fields['username'].widget.attrs.update({
                'class': 'form-control form-control-ev',
                'placeholder': 'Enter your username',
                'autocomplete': 'username',
            })
        if 'password' in self.fields:
            self.fields['password'].widget.attrs.update({
                'class': 'form-control form-control-ev',
                'placeholder': '••••••••',
                'autocomplete': 'current-password',
            })
