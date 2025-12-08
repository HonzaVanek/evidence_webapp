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
import matplotlib
matplotlib.use("Agg") 
import matplotlib.pyplot as plt
from matplotlib.patches import PathPatch
from matplotlib.patches import Wedge
from matplotlib.path import Path

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
        qr_color = request.POST.get('qr_color')
        qr_background_color = request.POST.get('qr_background_color')
        use_custom_logo = request.POST.get("use_custom_logo") == "on"
        custom_logo_file = request.FILES.get("custom_logo_file")

        logo = None
        if use_custom_logo and custom_logo_file:
            try:
                logo = Image.open(custom_logo_file).convert("RGBA")
            except Exception as e:
                print("LOGO ERROR:", e)
                logo = None
        
        qr = qrcode.QRCode(version=None, box_size=qr_size, border=qr_border, error_correction=qrcode.constants.ERROR_CORRECT_H)
        qr.add_data(data)
        qr.make(fit=True)
        image = qr.make_image(fill_color=qr_color, back_color = qr_background_color).convert('RGBA')

        if logo:
            # spočítat cílovou velikost loga jako 20 % šířky QR
            qr_w, qr_h = image.size
            logo_target_width = int(qr_w * 0.20)

            wpercent = logo_target_width / float(logo.size[0])
            logo_target_height = int(float(logo.size[1]) * wpercent)

            logo = logo.resize((logo_target_width, logo_target_height), Image.LANCZOS)

            # pozice uprostřed
            pos = ((qr_w - logo_target_width) // 2, (qr_h - logo_target_height) // 2)

            image.alpha_composite(logo, dest=pos)
        
        # Uložení QR kódu do mediální složky
        filename = f"qr_code_{timezone.now().strftime('%Y%m%d%H%M%S')}.png"
        save_dir = os.path.join(settings.MEDIA_ROOT, "qr_codes")
        os.makedirs(save_dir, exist_ok=True)             # vytvoří složku pokud neexistuje
        full_path = os.path.join(save_dir, filename)
        image.save(full_path)

        qr_image_url = f"{settings.MEDIA_URL}qr_codes/{filename}"

        # Smazání starších QR kódů:
        try:
            files = sorted([os.path.join(save_dir, f) for f in os.listdir(save_dir)], key=os.path.getmtime)
            if len(files) > 10:  # ponechat posledních 10
                for old_file in files[:-10]:
                    os.remove(old_file)
        except Exception:
            pass  # pokud se něco pokazí, prostě to přeskočíme

        return render(request, 'pojistenci/generate_qr.html', {'qr_image_url': qr_image_url, 'data': data})
    
    return render(request, 'pojistenci/generate_qr.html')

@login_required
def generate_chart(request):
    DEFAULT_COLORS = ["#004289", "#5C9EAE", "#8F2D56", "#E9BA6A", "#E4E5C3","#3F7CAC", "#D9BF77", "#6B4226", "#A1C181", "#F2E394"]
    if request.method == "POST":
        count = int(request.POST.get("donut_number"))
        values = list(map(int, request.POST.getlist("chart_values")))
        
        if sum(values) != 100:
            return render(request,'pojistenci/generate_donut_chart.html',
                {
                    "error_message": f"Součet všech hodnot jednotlivých položek musí být 100. Aktuálně je to {sum(values)}.",
                    "prev_count": count,
                    "prev_values": values,
                    "prev_use_custom": request.POST.get("use_custom_colors") == "on",
                    "prev_colors": request.POST.getlist("chart_colors") or DEFAULT_COLORS[:count]
                }
            )

        use_custom = request.POST.get("use_custom_colors") == "on"
        prev_colors = request.POST.getlist("chart_colors")
        if use_custom:
            if not prev_colors or len(prev_colors) < count:
                prev_colors = DEFAULT_COLORS[:count]
            colors = prev_colors[:count]
        else:
            colors = DEFAULT_COLORS[:count]
        
        fig, ax = plt.subplots()
        ax.pie(values, colors=colors[:len(values)],wedgeprops=dict(width=0.5), startangle=-40)
        centre_circle = plt.Circle((0,0),0.25,fc='none')
        fig.gca().add_artist(centre_circle)
        ax.axis('equal')  
        # plt.title(f'Donut Chart with {count} segments')
        fig.patch.set_alpha(0)  # transparentní pozadí
        ax.patch.set_alpha(0)

        filename = f"donut_chart_{timezone.now().strftime('%Y%m%d%H%M%S')}.png"
        save_dir = os.path.join(settings.MEDIA_ROOT, "donut_charts")
        os.makedirs(save_dir, exist_ok=True)
        full_path = os.path.join(save_dir, filename)
        
        plt.savefig(full_path, transparent=True)
        plt.close()

        donut_image_url = f"{settings.MEDIA_URL}donut_charts/{filename}"

        # Smazání starších grafů:
        try:
            files = sorted([os.path.join(save_dir, f) for f in os.listdir(save_dir)], key=os.path.getmtime)
            if len(files) > 10:  # ponechat posledních 10
                for old_file in files[:-10]:
                    os.remove(old_file)
        except Exception:
            pass  # pokud se něco pokazí, prostě to přeskočíme

        return render(request, 'pojistenci/generate_donut_chart.html', {'donut_image_url': donut_image_url, 'prev_count': count, "prev_values": values, "prev_colors": colors, "prev_use_custom": use_custom})
    
    return render(request, 'pojistenci/generate_donut_chart.html', {"prev_count": 4, "prev_values": [25, 25, 25, 25], "prev_colors": DEFAULT_COLORS[:4], "prev_use_custom": False})


@login_required
def remove_background(request):
    if request.method == "POST":
        image_file = request.FILES.get("image_file")
        if not image_file:
            return render(request, "pojistenci/remove_background.html", {
                "error_message": "Prosím nahraj fotografii."
            })

        api_key = os.getenv("REMOVE_BG_API_KEY")
        if not api_key:
            return render(request, "pojistenci/remove_background.html", {
                "error_message": "Chybí API klíč k remove.bg. Zkontroluj .env."
            })

        # ==== CALL REMOVE.BG API ====
        files = {"image_file": image_file}
        data = {"size": "auto"}   # může být "auto", "medium", "full"

        response = requests.post(
            "https://api.remove.bg/v1.0/removebg",
            data=data,
            files=files,
            headers={"X-Api-Key": api_key},
        )

        if response.status_code != 200:
            return render(request, "pojistenci/remove_background.html", {
                "error_message": f"Remove.bg API error: {response.text}"
            })

        # ==== SAVE RESULT ====
        output_dir = os.path.join(settings.MEDIA_ROOT, "removed_backgrounds")
        os.makedirs(output_dir, exist_ok=True)

        filename = f"no_bg_{timezone.now().strftime('%Y%m%d%H%M%S')}.png"
        full_path = os.path.join(output_dir, filename)

        with open(full_path, "wb") as f:
            f.write(response.content)

        # === zde přidáme rotaci starších obrázků ===
        try:
            files = sorted(
                [os.path.join(output_dir, f) for f in os.listdir(output_dir)],
                key=os.path.getmtime
            )
            if len(files) > 5:
                for old_file in files[:-5]:
                    os.remove(old_file)
        except Exception:
            pass  # pokud se něco pokazí, prostě to přeskočíme

        output_url = f"{settings.MEDIA_URL}removed_backgrounds/{filename}"

        return render(request, "pojistenci/remove_background.html", {
            "output_image_url": output_url
        })

    return render(request, "pojistenci/remove_background.html")

@login_required
def generate_pie_chart(request):
    DEFAULT_COLORS = ["#004289", "#5C9EAE", "#8F2D56", "#E9BA6A", "#E4E5C3","#3F7CAC", "#D9BF77", "#6B4226", "#A1C181", "#F2E394"    ]
    if request.method == "POST":
        count = int(request.POST.get("pie-chart-number"))
        values = list(map(int, request.POST.getlist("chart_values")))
        highlight_index = None
        highlight_outline = False
        full_outline = False

        if request.user.is_staff:
            # index vystouplé části, může být None
            raw_index = request.POST.get("highlight_index")
            if raw_index not in (None, "", "none"):
                highlight_index = int(raw_index)

        full_outline = request.POST.get("full_outline") == "on"
        
        if sum(values) != 100:
            return render(request,'pojistenci/generate_pie_chart.html',
                {
                    "error_message": f"Součet všech hodnot jednotlivých položek musí být 100. Aktuálně je to {sum(values)}.",
                    "prev_count": count,
                    "prev_values": values,
                    "prev_use_custom": request.POST.get("use_custom_colors") == "on",
                    "prev_colors": request.POST.getlist("chart_colors") or DEFAULT_COLORS[:count]
                }
            )

        use_custom = request.POST.get("use_custom_colors") == "on"
        prev_colors = request.POST.getlist("chart_colors")
        if use_custom:
            if not prev_colors or len(prev_colors) < count:
                prev_colors = DEFAULT_COLORS[:count]
            colors = prev_colors[:count]
        else:
            colors = DEFAULT_COLORS[:count]

        labels = request.POST.getlist("chart_labels")
        use_labels = request.POST.get("use_labels") == "on"
        if use_labels:
            if len(labels) < count:
                labels = labels + [""] * (count - len(labels))
        else:
            labels = [""] * count


        explode = [0] * len(values)
        if highlight_index is not None:
            explode[highlight_index] = 0.12
        
        fig, ax = plt.subplots(figsize=(7,7))
        wedges, texts = ax.pie(
            values,
            explode=explode,
            colors=colors[:len(values)],
            labels=labels,
            startangle=-40,
            textprops={'fontsize': 14, 'color': '#000'}
        )

        if full_outline:
            # Nakresli kruh mírně větší než pie graf
            circ = plt.Circle((0, 0), radius=1.08, fill=False, linewidth=9, edgecolor="#55002e")
            ax.add_patch(circ)

        # Posunout popisky dál od středu, aby nebyly uříznuté
        for t in texts:
            x, y = t.get_position()
            t.set_position((x * 1.15, y * 1.15))

        ax.axis('equal') 
        plt.subplots_adjust(left=0.05, right=0.95, top=0.95, bottom=0.05)
        fig.patch.set_alpha(0)  # transparentní pozadí
        ax.patch.set_alpha(0)

        filename = f"pie_chart_{timezone.now().strftime('%Y%m%d%H%M%S')}.png"
        save_dir = os.path.join(settings.MEDIA_ROOT, "pie_charts")
        os.makedirs(save_dir, exist_ok=True)
        full_path = os.path.join(save_dir, filename)
        
        plt.savefig(full_path, transparent=True, dpi=150)
        plt.close()

        pie_chart_image_url = f"{settings.MEDIA_URL}pie_charts/{filename}"

        # Smazání starších grafů:
        try:
            files = sorted([os.path.join(save_dir, f) for f in os.listdir(save_dir)], key=os.path.getmtime)
            if len(files) > 10:  # ponechat posledních 10
                for old_file in files[:-10]:
                    os.remove(old_file)
        except Exception:
            pass  # pokud se něco pokazí, prostě to přeskočíme

        return render(request, 'pojistenci/generate_pie_chart.html', {'pie_chart_image_url': pie_chart_image_url, 'prev_count': count, "prev_values": values, "prev_colors": colors, "prev_use_custom": use_custom, "prev_labels": labels, "prev_use_labels": use_labels, "is_staff": request.user.is_staff, "count_range": range(count)})
    return render(request, 'pojistenci/generate_pie_chart.html', {"is_staff": request.user.is_staff, "count_range": range(3), "prev_count" : 3})