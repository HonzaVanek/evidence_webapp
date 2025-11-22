from django.core.paginator import Paginator
from django.shortcuts import render, get_object_or_404, redirect
from .models import Pojistenec, Pojisteni, TypPojisteni
from .forms import PojistenecForm, PojisteniForm, TypPojisteniForm, BulkUploadForm, RegistraceForm
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.shortcuts import get_current_site
from django.contrib.auth.views import LoginView
from .forms import VlastniLoginForm, RegistraceForm
from django.core.mail import send_mail, EmailMessage
from django.template.loader import render_to_string
from django.conf import settings
from openpyxl import load_workbook
import requests
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from django import forms
from django.core.exceptions import ValidationError
from rest_framework import viewsets
from .serializers import PojistenecSerializer
from rest_framework.permissions import AllowAny, IsAdminUser
import qrcode
from PIL import Image
import os

# Create your views here.

class PojistenecViewSet(viewsets.ModelViewSet):
    queryset = Pojistenec.objects.all()
    serializer_class = PojistenecSerializer
    permission_classes = [AllowAny]

    def get_permissions(self):
        if self.request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
            return [IsAdminUser()]
        return super().get_permissions()

def index(request):
    return render(request, 'pojistenci/index.html')

@login_required
def pojistenci_vypis(request):
    search_query = request.GET.get('search', '').strip()
    if search_query:
        pojistenci = Pojistenec.objects.filter(
            Q(first_name__icontains=search_query) | 
            Q(last_name__icontains=search_query) |
            Q(address_street__icontains=search_query) |
            Q(address_city__icontains=search_query) |
            Q(psc__icontains=search_query) |
            Q(phone__icontains=search_query) |
            Q(email__icontains=search_query)
        ).order_by('last_name', 'first_name')
    else:
        pojistenci = Pojistenec.objects.all().order_by('last_name', 'first_name')
    
    paginator = Paginator(pojistenci, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'pojistenci/pojistenci.html', {'pojistenci': pojistenci, 'page_obj': page_obj, 'total_count': paginator.count, 'search_query': search_query})

@login_required
def pojistenec_detail(request, id):
    pojistenec = get_object_or_404(Pojistenec, id=id)
    
    return render(request, 'pojistenci/pojistenec_detail.html', {
        'jmeno': pojistenec.first_name,
        'prijmeni': pojistenec.last_name,
        'ulice' : pojistenec.address_street,
        'mesto' : pojistenec.address_city,
        'psc': pojistenec.psc,
        'tel': pojistenec.phone,
        'email': pojistenec.email,
        'id': pojistenec.id,
        'foto': pojistenec.foto,
        'pojisteni' : pojistenec.pojisteni.all()
        })

@login_required
def novy_pojistenec(request):
    if request.method == 'POST':
        form = PojistenecForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Pojištěnec byl úspěšně přidán.')
            return redirect('pojistenci')
        
    else:
        form = PojistenecForm()

    return render(request, 'pojistenci/novy_pojistenec.html', {'form': form})

@login_required
def smaz_pojistence(request, pojistenec_id):
    pojistenec = get_object_or_404(Pojistenec, id = pojistenec_id)
    pojistenec.delete()
    messages.success(request, 'Pojištěnec byl úspěšně odstraněn.', extra_tags='deleted')
    return HttpResponseRedirect ('/pojistenci')

@login_required
def uprav_pojistence(request, pojistenec_id):
    pojistenec = get_object_or_404(Pojistenec, id = pojistenec_id)
    if request.method == 'POST':
        pojistenec.first_name = request.POST['pojistenec.first_name']
        pojistenec.last_name = request.POST['pojistenec.last_name']
        pojistenec.address_street = request.POST['pojistenec.address_street']
        pojistenec.address_city = request.POST['pojistenec.address_city']
        pojistenec.psc = request.POST['pojistenec.psc']
        pojistenec.phone = request.POST['pojistenec.phone']
        pojistenec.email = request.POST['pojistenec.email']
        if 'foto' in request.FILES:
            pojistenec.foto = request.FILES['foto']
        pojistenec.save()
        return redirect ('pojistenec_detail', id=pojistenec_id)
    
    return render(request, 'pojistenci/uprav-pojistence.html', {
        'pojistenec': pojistenec
    })

@login_required
def pridat_pojisteni(request, pojistenec_id):
    pojistenec = get_object_or_404(Pojistenec, id = pojistenec_id)
    if request.method == 'POST':
        form = PojisteniForm(request.POST)
        if form.is_valid():
            pojisteni = form.save(commit=False)
            pojisteni.pojistenec = pojistenec
            pojisteni.save()
            messages.success(request, 'Pojištění bylo přidáno.')
            return redirect ('pojistenec_detail', id=pojistenec_id)
    
    else:
        form = PojisteniForm()
    
    return render(request, 'pojistenci/pridat_pojisteni.html', {'form' : form, 'pojistenec' : pojistenec})

@login_required
def pojisteni_vypis(request):
    pojisteni = Pojisteni.objects.all().order_by('platnost_do')
    paginator = Paginator(pojisteni, 10)

    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    today = timezone.now().date()

    return render(request, 'pojistenci/pojisteni.html', {'pojisteni': pojisteni, 'page_obj': page_obj, 'total_count': paginator.count, 'today': today})

@staff_member_required(login_url='login')
def smaz_typ_pojisteni(request, typ_pojisteni_id):
    typ_pojisteni = get_object_or_404(TypPojisteni, id = typ_pojisteni_id)
    typ_pojisteni.delete()
    messages.success(request, 'Typ pojištění byl úspěšně odstraněn.', extra_tags='deleted')
    return redirect('pridej-pojisteni')

@login_required
def pojisteni_detail(request, pojisteni_id):
    pojisteni = get_object_or_404(Pojisteni, id=pojisteni_id)
    return render(request, 'pojistenci/pojisteni_detail.html', {'pojisteni': pojisteni})

@login_required
def uprav_pojisteni(request, pojisteni_id):
    pojisteni = get_object_or_404(Pojisteni, id = pojisteni_id)
    if request.method == 'POST':
        form = PojisteniForm(request.POST, instance=pojisteni)
        if form.is_valid():
            form.save()
            messages.success(request, 'Pojištění bylo úspěšně upraveno.')
            return redirect ('pojistenec_detail', id=pojisteni.pojistenec.id)
    else:
        form = PojisteniForm(instance=pojisteni)

    return render(request, 'pojistenci/uprav_pojisteni.html', {'form': form, 'pojisteni': pojisteni})

@login_required
def smaz_pojisteni(request, pojisteni_id):
    pojisteni = get_object_or_404(Pojisteni, id = pojisteni_id)
    pojisteni.delete()
    messages.success(request, 'Pojištění bylo úspěšně odstraněno.', extra_tags='deleted')
    return redirect ('pojistenec_detail', id=pojisteni.pojistenec.id)

@staff_member_required(login_url='login')
def typ_pojisteni(request):
    typy_pojisteni = TypPojisteni.objects.all()
    if request.method == 'POST':
        form = TypPojisteniForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Nový typ pojištění byl úspěšně přidán.')
            return redirect('pridej-typ-pojisteni')
    else:
        form = TypPojisteniForm()

    return render(request, 'pojistenci/typy_pojisteni.html', {'form': form,'typy_pojisteni': typy_pojisteni})

class VlastniLoginView(LoginView):
    template_name = 'pojistenci/login.html'
    form_class = VlastniLoginForm


def registrace(request):
    if request.method == 'POST':
        form = RegistraceForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)

            # ----- DEV REŽIM -----
            if settings.APP_ENV == "dev":
                user.is_active = True
                user.save()
                login(request, user)
                return redirect('homepage')

            # ----- PROD REŽIM -----
            user.is_active = False
            user.save()

            uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)

            current_site = get_current_site(request)
            activation_link = f"http://{current_site.domain}{reverse('activate', args=[uidb64, token])}"

            subject = 'Aktivujte si účet'
            message = render_to_string(
                'registration/activation_email.txt',
                {'user': user, 'activation_link': activation_link}
            )

            email = EmailMessage(subject, message, settings.DEFAULT_FROM_EMAIL, to=[user.email])
            email.send(fail_silently=False)

            return render(request, 'pojistenci/registration_complete.html', {'form': form})

    else:
        form = RegistraceForm()

    return render(request, 'pojistenci/registrace.html', {'form': form})

def activate(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        messages.success(request, 'Váš účet byl aktivován, nyní se můžete přihlásit.')
        return redirect('login')
    else:
        return render(request, 'pojistenci/activation_invalid.html')

@staff_member_required(login_url='login')
def bulk_upload_pojistenci(request):
    if request.method == 'POST':
        form = BulkUploadForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_excel = request.FILES['file']
            try:
                wb = load_workbook(uploaded_excel, data_only=True)
                sheet = wb.active
            except Exception as e:
                form.add_error('file', f'Chyba při čtení Excelu: {e}')
            else:
                # první řádek = hlavička
                header = [cell.value for cell in sheet[1]]

                required_columns = ['Jméno','Příjmení','Ulice','Město','PSČ','Telefon','Email']
                missing = [col for col in required_columns if col not in header]

                if missing:
                    form.add_error('file', f'Excel postrádá sloupce: {", ".join(missing)}')
                else:
                    # mapa sloupců (název → index sloupce)
                    col_map = {name: header.index(name) for name in required_columns}

                    created = 0

                    try:
                        with transaction.atomic():
                            for row_index, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
                                
                                def normalize(value):
                                    if value is None:
                                        return ""
                                    return str(value).strip()

                                data = {
                                    'first_name':     normalize(row[col_map['Jméno']]),
                                    'last_name':      normalize(row[col_map['Příjmení']]),
                                    'address_street': normalize(row[col_map['Ulice']]),
                                    'address_city':   normalize(row[col_map['Město']]),
                                    'psc':            normalize(row[col_map['PSČ']]),
                                    'phone':          normalize(row[col_map['Telefon']]),
                                    'email':          normalize(row[col_map['Email']]),
                                }

                                obj = Pojistenec(**data)
                                obj.full_clean()
                                obj.save()
                                created += 1

                    except ValidationError as e:
                        form.add_error('file',
                            f"Chyba v řádku {row_index}: {e.messages[0]}"
                        )
                    else:
                        messages.success(request,
                            f"Úspěšně přidáno {created} pojištěnců."
                        )
                        return redirect('bulk-upload-pojistenci')
    else:
        form = BulkUploadForm()

    return render(request, 'pojistenci/bulk_upload.html', {'form': form})

@login_required
def vypis_api(request):
    return render(request, 'pojistenci/vypis_api.html')

def o_aplikaci(request):
    return render(request, 'pojistenci/o_aplikaci.html')

def vychytavky(request):
    return render(request, 'pojistenci/vychytavky.html')

@login_required
def generate_qr(request):
    if request.method == 'POST':
        data = request.POST.get('qr_text')
        qr_size = int(request.POST.get('qr_size'))
        qr_border = int(request.POST.get('qr_border'))
        qr = qrcode.QRCode(version=1, box_size=qr_size, border=qr_border)
        qr.add_data(data)
        qr.make(fit=True)
        image = qr.make_image(fill="black", back_color = "white")

        # Uložení QR kódu do mediální složky
        
        filename = f"qr_code_{timezone.now().strftime('%Y%m%d%H%M%S')}.png"
        save_dir = os.path.join(settings.MEDIA_ROOT, "qr_codes")
        os.makedirs(save_dir, exist_ok=True)             # vytvoří složku pokud neexistuje
        full_path = os.path.join(save_dir, filename)
        image.save(full_path)

        qr_image_url = f"{settings.MEDIA_URL}qr_codes/{filename}"

        return render(request, 'pojistenci/generate_qr.html', {'qr_image_url': qr_image_url, 'data': data})
    
    return render(request, 'pojistenci/generate_qr.html')

