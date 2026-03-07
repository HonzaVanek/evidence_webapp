from django.db import models
from django.core.validators import FileExtensionValidator
from django.core.exceptions import ValidationError
from django.conf import settings

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



# rozesílač (newsletter):

class Contact(models.Model):
    """Jednoduchý seznam příjemců"""
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=200, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return f"{self.name} <{self.email}>" if self.name else self.email


class EmailTemplate(models.Model):
    name = models.CharField(max_length=200)
    subject = models.CharField(max_length=250)
    html_body = models.TextField()
    text_body = models.TextField(blank=True, help_text="Volitelné: plain-text fallback.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.name


class EmailCampaign(models.Model):
    """Jedno konkrétní rozeslání (test i ostré)."""
    template = models.ForeignKey(EmailTemplate, on_delete=models.PROTECT)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="email_campaigns")
    created_at = models.DateTimeField(auto_now_add=True)

    # co se poslalo (snapshot – ať to nezmění pozdější editace šablony)
    subject = models.CharField(max_length=250)
    html_body = models.TextField()
    text_body = models.TextField(blank=True)

    is_test = models.BooleanField(default=False)
    note = models.CharField(max_length=250, blank=True)

    def __str__(self) -> str:
        return f"{'TEST ' if self.is_test else ''}{self.subject} ({self.created_at:%Y-%m-%d %H:%M})"


class EmailDelivery(models.Model):
    STATUS_CHOICES = [
        ("queued", "Queued"),
        ("sent", "Sent"),
        ("failed", "Failed"),
    ]
    campaign = models.ForeignKey(EmailCampaign, on_delete=models.CASCADE, related_name="deliveries")
    to_email = models.EmailField()
    to_name = models.CharField(max_length=200, blank=True)

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="queued")
    error = models.TextField(blank=True)

    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["campaign", "status"]),
            models.Index(fields=["to_email"]),
        ]

    def __str__(self) -> str:
        return f"{self.to_email} - {self.status}"


# model pro ukládání obrázků, které můžeme vkládat do rozesílače emailů (abychom nemuseli používat externí hosting a riskovat, že se nám obrázky ztratí):
def validate_email_image_size(image):
    max_size_mb = 2
    if image.size > max_size_mb * 1024 * 1024:
        raise ValidationError(f"Maximální povolená velikost obrázku je pouze {max_size_mb} MB.")

class EmailImage(models.Model):
    title = models.CharField(max_length=255, blank=True, verbose_name="Název")
    image = models.ImageField(
        upload_to="email_images/",
        verbose_name="Obrázek",
        validators=[
            FileExtensionValidator(allowed_extensions=["jpg", "jpeg", "png", "webp", "gif"]),
            validate_email_image_size,
        ],
    )
    file_size = models.PositiveIntegerField(default=0, verbose_name="Velikost souboru (B)")
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="Nahráno")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Nahrál",
    )

    class Meta:
        ordering = ["-uploaded_at"]
        verbose_name = "Obrázek do emailu"
        verbose_name_plural = "Obrázky do emailu"

    def __str__(self):
        return self.title or self.image.name