from django import forms
from .models import Pojistenec, Pojisteni, TypPojisteni
from django.forms import DateInput, NumberInput
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator

class PojistenecForm(forms.ModelForm):
    class Meta:
        model = Pojistenec
        fields = ['first_name', 'last_name', 'address_street', 'address_city', 'psc', 'phone', 'email', 'foto']
        labels = {
            'first_name': 'Jméno',
            'last_name': 'Příjmení',
            'address_street': 'Ulice a číslo',
            'address_city': 'Město',
            'psc': 'PSČ',
            'phone': 'Telefon',
            'email': 'Email',
            'foto': 'Fotografie',
        }

    def clean(self):
        cleaned_data = super().clean()
        first_name = cleaned_data.get('first_name')
        last_name = cleaned_data.get('last_name')
        phone = cleaned_data.get('phone')
        email = cleaned_data.get('email')

        if not first_name:
            self.add_error('first_name', 'Jméno je povinné.')

        if not last_name:
            self.add_error('last_name', 'Příjmení je povinné.')

        if not phone and not email:
            self.add_error(None, "Musí být vyplněny alespoň nějaké kontaktní údaje – buď telefon, nebo email.")


class PojisteniForm(forms.ModelForm):
    class Meta:
        model = Pojisteni
        exclude = ['pojistenec']
        widgets = {
            'platnost_od': DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'platnost_do': DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'castka': forms.NumberInput(attrs={'step': '1'})
        }

class TypPojisteniForm(forms.ModelForm):
    class Meta:
        model = TypPojisteni
        fields = ['nazev']
        labels = {
            'nazev': 'Nový typ pojištění',
        }

class VlastniLoginForm(AuthenticationForm):
    username = forms.CharField(label="Uživatelské jméno")
    password = forms.CharField(label="Heslo", widget=forms.PasswordInput)

    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        if username and password:
            try:
                user = User.objects.get(username=username)
                if not user.check_password(password):
                    raise forms.ValidationError("Zadané heslo není správné.")
            except User.DoesNotExist:
                raise forms.ValidationError("Uživatel s tímto jménem neexistuje.")

        return super().clean()
    
class RegistraceForm(UserCreationForm):
    username = forms.CharField(label="Uživatelské jméno")
    email = forms.EmailField(required=True, label='Email')
    password1 = forms.CharField(label="Heslo", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Potvrzení hesla", widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

class BulkUploadForm(forms.Form):
    file = forms.FileField(
        label="Excel soubor (.xlsx)",
        help_text="Sloupce: Jméno, Příjmení, Ulice, Město, PSČ, Telefon, Email",
        validators=[FileExtensionValidator(allowed_extensions=['xlsx', 'xls'])],
    )