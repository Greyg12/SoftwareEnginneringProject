"""
URL configuration for system_rezerwacji project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from rejestracja import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.index, name='index'),
    path('login/', views.login_view, name='login'),
    path('panel_pacjenta/', views.panel_pacjenta, name='panel_pacjenta'),
    path('panel_pacjenta/rezerwacja/', views.wybierz_specjalizacje, name='wybierz_specjalizacje'),
    path('panel_pacjenta/historia/', views.historia_wizyt, name='historia_wizyt'),
    path('panel_pacjenta/moje_dane/', views.dane_pacjenta, name='dane_pacjenta'),
    path('panel_pacjenta/usun_konto/', views.usun_konto, name='usun_konto'),
    path('rejestracja_pacjent/', views.rejestracja_pacjent, name='rejestracja_pacjent'),
    path('lekarze/', views.lista_lekarzy, name='lista_lekarzy'),
    path('lekarz/<int:lekarz_id>/terminy/', views.terminy_lekarza, name='terminy_lekarza'),
    path('rezerwacja/lekarz/', views.wybierz_lekarza, name='wybierz_lekarza'),
    path('rezerwacja/lekarz/<int:lekarz_id>/termin/', views.wybierz_termin, name='wybierz_termin'),
    path('rezerwacja/zatwierdz/', views.rezerwuj_wizyte, name='rezerwuj_wizyte'),
    path('wizyta/<int:wizyta_id>/modyfikuj/', views.modyfikuj_wizyte, name='modyfikuj_wizyte'),
    path('logout/', views.logout_view, name='logout'),
    path('moj_terminarz/', views.moj_terminarz, name='moj_terminarz'),
    path('anuluj_wizyte/<int:wizyta_id>/', views.anuluj_wizyte, name='anuluj_wizyte'),
    path('usun_termin/', views.usun_termin, name='usun_termin'),
    path('wiadomosc_do_admina/', views.wiadomosc_do_admina, name='wiadomosc_do_admina'),
]
