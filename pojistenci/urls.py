from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
from .views import VlastniLoginView


urlpatterns = [
    path('', views.index, name='homepage'),
    path('pojistenci', views.pojistenci_vypis, name='pojistenci'),
    path('pojistenci/<int:id>', views.pojistenec_detail, name='pojistenec_detail'),
    path('pojistenci/novy_pojistenec', views.novy_pojistenec, name='novy_pojistenec'),
    path('pojistenci/smazat/<int:pojistenec_id>', views.smaz_pojistence, name='smazat-pojistence'),
    path('pojistenci/upravit/<int:pojistenec_id>', views.uprav_pojistence, name='uprav-pojistence'),
    path('pojistenci/smazat/<int:pojistenec_id>/pojisteni/pridat', views.pridat_pojisteni, name='pridat_pojisteni'),
    path('pojisteni', views.pojisteni_vypis, name='pojisteni-vypis'),
    path('pojisteni/smazat/<int:typ_pojisteni_id>', views.smaz_typ_pojisteni, name='smazat-typ-pojisteni'), 
    path('pojisteni/upravit/<int:pojisteni_id>', views.uprav_pojisteni, name='uprav-pojisteni'),
    path('pojisteni/delete/<int:pojisteni_id>', views.smaz_pojisteni, name='smazat-pojisteni'),
    path('pojisteni/<int:pojisteni_id>', views.pojisteni_detail, name='pojisteni_detail'),
    path('pojisteni/typ-pojisteni', views.typ_pojisteni, name='pridej-typ-pojisteni'),
    path('login/', VlastniLoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('registrace/', views.registrace, name='registrace'),
    path('activate/<uidb64>/<token>/', views.activate, name='activate'),
    path('pojistenci/import/', views.bulk_upload_pojistenci, name='bulk-upload-pojistenci'),
    path('pojistenci/vypis-api', views.vypis_api, name='vypis-api'),
    path('pojistenci/o_aplikaci', views.o_aplikaci, name='o-aplikaci'),
    path('pojistenci/vychytavky', views.vychytavky, name='vychytavky'),
    path('pojistenci/vychytavky/qr', views.generate_qr, name='generate-qr'),
]
