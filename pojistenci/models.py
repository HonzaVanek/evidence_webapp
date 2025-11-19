from django.db import models
from django.core.validators import FileExtensionValidator
from django.core.exceptions import ValidationError

def validate_image_size(image):
    max_size_mb = 3
    if image.size > max_size_mb * 1024 * 1024:
        raise ValidationError(f"Maximální velikost souboru je {max_size_mb} MB.")

# Create your models here.

class Pojistenec(models.Model):
    first_name = models.CharField(max_length=30, verbose_name='Jméno')
    last_name = models.CharField(max_length=50, verbose_name='Příjmení')
    address_street = models.CharField(max_length=50, verbose_name='Ulice')
    address_city = models.CharField(max_length=50, verbose_name='Město')
    psc = models.CharField(max_length=6, verbose_name='PSČ')
    phone = models.CharField(max_length=20, verbose_name='Telefon', null=True, blank=True)
    email = models.EmailField(max_length=50, verbose_name='Email', null=True, blank=True)
    foto = models.ImageField(upload_to='fotky_pojistencu/', null=True, blank=True, verbose_name='Fotografie', validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png']), validate_image_size])

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

class TypPojisteni(models.Model):
    nazev = models.CharField(max_length=30, unique=True, null=True, verbose_name='Typ Pojištění', blank=True) # nutno ještě ošetřit, aby šlo smazat i když je použito v pojisteni

    def __str__(self):
        return f"{self.nazev}"

class Pojisteni(models.Model):
    pojistenec = models.ForeignKey(Pojistenec, on_delete=models.CASCADE, related_name='pojisteni')
    typ = models.ForeignKey(TypPojisteni, verbose_name='Typ pojištění', on_delete=models.PROTECT)
    predmet = models.CharField(max_length=100, verbose_name='Předmět pojištění')  # např. "Byt", "Auto"
    castka = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Částka')
    platnost_od = models.DateField(verbose_name='Platnost od')
    platnost_do = models.DateField(verbose_name='Platnost do')