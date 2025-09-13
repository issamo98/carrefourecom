from django import forms
from .models import Client
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

class ClientUpdateForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ['first_name', 'last_name', 'email', 'number', 'adresse']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter First Name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Last Name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter Email'}),
            'number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Phone Number'}),
            'adresse': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Entrer Votre Business Adresse'}),
        }


class CustomSignUpForm(UserCreationForm):
    first_name = forms.CharField(max_length=20, required=True, label="Prénom")
    last_name = forms.CharField(max_length=20, required=True, label="Nom")
    email = forms.EmailField(required=True, label="Email")
    number = forms.CharField(max_length=10, required=True, label="Numéro de téléphone")
    adresse = forms.CharField(max_length=100, required=True, label="Adresse")

    class Meta:
        model = User
        fields = ("username", "password1", "password2", "first_name", "last_name", "email", "number", "adresse")
