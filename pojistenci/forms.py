from django import forms
from .models import Pojistenec, Pojisteni, TypPojisteni, Contact, EmailTemplate, EmailImage
from django.forms import DateInput, NumberInput
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator, validate_email
from django.core.exceptions import ValidationError
from django.db.models import Sum

import re
from bs4 import BeautifulSoup

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

# rozesílač (importování kontaktů):

class ContactForm(forms.ModelForm):
    class Meta:
        model = Contact
        fields = ["name", "email", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Jméno (volitelné)"}),
            "email": forms.EmailInput(attrs={"placeholder": "email@domena.cz"}),
        }


class ContactImportForm(forms.Form):
    file = forms.FileField(help_text="XLSX se sloupci: jméno, email")

    def clean_file(self):
        f = self.cleaned_data["file"]
        name = (f.name or "").lower()
        if not name.endswith(".xlsx"):
            raise ValidationError("Tohle nevypadá jako xlsx soubor. Nahraj prosím soubor s příponou .xlsx, který má dva sloupce se záhlavím jméno a email")
        return f


#přepis html emailu do plaintextu:
def html_to_plain_text(html: str) -> str:
    if not html:
        return ""

    soup = BeautifulSoup(html, "html.parser")

    # zachovat základní zalomení
    for br in soup.find_all("br"):
        br.replace_with("\n")

    for p in soup.find_all("p"):
        p.append("\n\n")

    for li in soup.find_all("li"):
        li.insert_before("• ")
        li.append("\n")

    text = soup.get_text()

    # úklid whitespace
    text = text.replace("\xa0", " ")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)

    return text.strip()

class EmailTemplateForm(forms.ModelForm):
    class Meta:
        model = EmailTemplate
        fields = ["name", "subject", "html_body", "text_body"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Např. Newsletter březen 2026"}),
            "subject": forms.TextInput(attrs={"placeholder": "Předmět emailu"}),
            "html_body": forms.Textarea(attrs={"rows": 18, "required": False}),
            "text_body": forms.Textarea(attrs={"rows": 8}),
        }

    def clean_html_body(self):
        html = self.cleaned_data.get("html_body", "").strip()

        # TinyMCE někdy pošle "prázdné" HTML typu <p>&nbsp;</p>
        normalized = (
            html.replace("&nbsp;", "")
                .replace("<p></p>", "")
                .replace("<p><br></p>", "")
                .replace("<p> </p>", "")
                .strip()
        )

        if not normalized:
            raise forms.ValidationError("HTML tělo emailu nesmí být prázdné.")

        return html
    
    def clean(self):
        cleaned_data = super().clean()

        html_body = cleaned_data.get("html_body", "")
        text_body = (cleaned_data.get("text_body") or "").strip()

        if html_body and not text_body:
            cleaned_data["text_body"] = html_to_plain_text(html_body)

        return cleaned_data
    
# odesílání kampaní:
class SendCampaignForm(forms.Form):
    SEND_MODE_CHOICES = [("test", "Testovací email"), ("live", "Ostré rozeslání"),]

    template = forms.ModelChoiceField(
        queryset=EmailTemplate.objects.all().order_by("name"),
        label="Šablona",
        empty_label="-- vyber šablonu k rozeslání --",
    )

    send_mode = forms.ChoiceField(
        choices=SEND_MODE_CHOICES,
        widget=forms.RadioSelect,
        initial="test",
        label="Režim odeslání",
    )

    test_email = forms.EmailField(
        required=False,
        label="Testovací email",
        widget=forms.EmailInput(attrs={"placeholder": "test@example.com"}),
    )

    contacts = forms.ModelMultipleChoiceField(
        queryset=Contact.objects.filter(is_active=True).order_by("email"),
        required=False,
        label="Kontakty",
        widget=forms.CheckboxSelectMultiple,
    )

    note = forms.CharField(
        required=False,
        label="Poznámka",
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Volitelná interní poznámka ke kampani"}),
    )

    def clean(self):
        cleaned_data = super().clean()

        send_mode = cleaned_data.get("send_mode")
        test_email = cleaned_data.get("test_email")
        contacts = cleaned_data.get("contacts")

        if send_mode == "test":
            if not test_email:
                self.add_error("test_email", "U testovacího režimu musíš vyplnit testovací email.")

        elif send_mode == "live":
            if not contacts or contacts.count() == 0:
                self.add_error("contacts", "Pro ostré rozeslání musíš vybrat aspoň jeden kontakt.")

        return cleaned_data
    


# pro nahrávání obrázků na server v rozesílači emailů (aby šablony mohly používat obrázky, které jsou na našem serveru a ne někde jinde na internetu):
class EmailImageUploadForm(forms.ModelForm):
    class Meta:
        model = EmailImage
        fields = ["title", "image"]
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "Volitelný název obrázku"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        image = cleaned_data.get("image")

        if image:
            current_total = EmailImage.objects.aggregate(total=Sum("file_size"))["total"] or 0

            max_total = 100 * 1024 * 1024  # 100 MB

            if current_total + image.size > max_total:
                raise ValidationError(
                    "Nelze nahrát další obrázek. Úložiště pro emailové obrázky překročilo limit 100 MB. "
                    "Nejdříve je potřeba z galerie smazat alespoň pár nepotřebných obrázků."
                )

        return cleaned_data