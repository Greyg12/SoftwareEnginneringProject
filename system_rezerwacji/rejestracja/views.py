from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from .models import Lekarz, Profil, Wizyta, Termin, UsunKontoRequest, WiadomoscOdLekarza
from django.contrib.auth.models import User
from django import forms
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.http import HttpResponseRedirect, JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST
from django.core.mail import mail_admins
from django.core.validators import RegexValidator
import datetime
from django.views.decorators.csrf import csrf_exempt

def index(request):
    return render(request, 'rejestracja/index.html')

class PacjentRejestracjaForm(UserCreationForm):
    username = forms.CharField(label="Login", max_length=150)
    first_name = forms.CharField(label="Imię", max_length=30)
    last_name = forms.CharField(label="Nazwisko", max_length=150)
    email = forms.EmailField()
    telefon = forms.CharField(
    label="Numer telefonu",
    max_length=9,
    validators=[
        RegexValidator(
            regex=r'^\d{9}$',
            message="Numer telefonu musi zawierać dokładnie 9 cyfr.",
            code='invalid_phone'
        )
    ]
)

    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "email", "telefon", "password1", "password2")

def rejestracja_pacjent(request):
    if request.method == "POST":
        form = PacjentRejestracjaForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.username = form.cleaned_data['username']
            user.first_name = form.cleaned_data['first_name']
            user.last_name = form.cleaned_data['last_name']
            user.email = form.cleaned_data['email']
            user.save()
            # ZAPISZ numer telefonu do profilu pacjenta
            Profil.objects.create(user=user, rola='pacjent', telefon=form.cleaned_data['telefon'])
            # Zapisz numer telefonu do sesji na czas rezerwacji wizyty
            request.session['telefon'] = form.cleaned_data['telefon']
            return redirect('login')
    else:
        form = PacjentRejestracjaForm()
    return render(request, 'rejestracja/rejestracja_pacjent.html', {'form': form})

def login_view(request):
    error_message = None
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if user.is_superuser:
                login(request, user)
                return redirect('/admin/')
            try:
                profil = Profil.objects.get(user=user)
                login(request, user)
                if profil.rola == 'lekarz':
                    return redirect('moj_terminarz')
                # pacjent po zalogowaniu trafia do panelu pacjenta
                if profil.rola == 'pacjent':
                    return redirect('panel_pacjenta')
                return redirect('index')
            except Profil.DoesNotExist:
                error_message = "Brak profilu użytkownika."
    else:
        form = AuthenticationForm()
    return render(request, 'rejestracja/login.html', {'form': form, 'error_message': error_message})

def logout_view(request):
    logout(request)
    return redirect('index')

@login_required
def lista_lekarzy(request):
    lekarze = Lekarz.objects.filter(zatwierdzony=True)
    return render(request, 'rejestracja/lista_lekarzy.html', {'lekarze': lekarze})

@login_required
def terminy_lekarza(request, lekarz_id):
    lekarz = Lekarz.objects.get(id=lekarz_id)
    wizyty = Wizyta.objects.filter(nazwisko=lekarz.user.last_name, imie=lekarz.user.first_name)
    return render(request, 'rejestracja/terminy_lekarza.html', {'lekarz': lekarz, 'wizyty': wizyty})

@login_required
def panel_pacjenta(request):
    return render(request, 'rejestracja/panel_pacjenta.html')

@login_required
def wybierz_specjalizacje(request):
    specjalizacje = [
        ('Lekarz rodzinny', 'Lekarz rodzinny'),
        ('Dermatolog', 'Dermatolog'),
        ('Okulista', 'Okulista'),
        ('Kardiolog', 'Kardiolog'),
        ('Ortopeda', 'Ortopeda'),
    ]
    return render(request, 'rejestracja/wybierz_specjalizacje.html', {'specjalizacje': specjalizacje})

@login_required
def wybierz_lekarza(request):
    specjalizacja = request.GET.get('specjalizacja')
    lekarze = Lekarz.objects.filter(zatwierdzony=True, specjalizacja=specjalizacja)
    return render(request, 'rejestracja/wybierz_lekarza.html', {'lekarze': lekarze, 'specjalizacja': specjalizacja})

@login_required
def wybierz_termin(request, lekarz_id):
    lekarz = Lekarz.objects.get(id=lekarz_id)
    # Pobierz zajęte terminy na podstawie powiązania z modelem Termin
    zajete = Wizyta.objects.filter(lekarz=lekarz, termin__isnull=False)
    zajete_term = set((w.termin.data, w.termin.godzina) for w in zajete if w.termin)
    today = datetime.date.today()
    dni = [today + datetime.timedelta(days=d) for d in range(31)]  # najbliższe 31 dni

    # Usuń dni, w których pacjent ma już wizytę u specjalisty tej samej kategorii
    profil = Profil.objects.get(user=request.user)
    moje_wizyty = Wizyta.objects.filter(
        pacjent=profil,
        termin__isnull=False,
        termin__lekarz__specjalizacja=lekarz.specjalizacja
    )
    dni_zajete_przez_pacjenta = set(w.termin.data for w in moje_wizyty if w.termin)
    dni = [d for d in dni if d not in dni_zajete_przez_pacjenta]

    # Etap 1: wybór dnia
    if request.method == "GET" and not request.GET.get('data'):
        return render(request, 'rejestracja/wybierz_dzien.html', {
            'lekarz': lekarz,
            'dni': dni,
        })

    # Etap 2: wybór godziny
    wybrany_dzien = request.GET.get('data') or request.POST.get('data')
    if wybrany_dzien:
        try:
            if isinstance(wybrany_dzien, datetime.date):
                dzien_obj = wybrany_dzien
            else:
                dzien_obj = datetime.datetime.strptime(wybrany_dzien, "%Y-%m-%d").date()
        except ValueError:
            return redirect(request.path)
        wolne_godziny = []
        for h in range(7, 15):
            for m in (0, 30):
                slot_time = datetime.time(hour=h, minute=m)
                if (dzien_obj, slot_time) not in zajete_term:
                    wolne_godziny.append(slot_time)
        slot_time = datetime.time(hour=15, minute=0)
        if (dzien_obj, slot_time) not in zajete_term:
            wolne_godziny.append(slot_time)

        # Sprawdź czy wybrany termin jest nadal wolny przed rezerwacją
        if request.method == "POST" and request.POST.get('godzina'):
            godzina = request.POST.get('godzina')
            godzina_obj = datetime.datetime.strptime(godzina, "%H:%M").time()
            if (dzien_obj, godzina_obj) in zajete_term:
                return render(request, 'rejestracja/wybierz_godzine.html', {
                    'lekarz': lekarz,
                    'dzien': dzien_obj,
                    'wolne_godziny': wolne_godziny,
                    'error': "Wybrany termin został już zajęty. Wybierz inny."
                })
            return HttpResponseRedirect(
                reverse('rezerwuj_wizyte') +
                f'?lekarz_id={lekarz.id}&data={dzien_obj}&godzina={godzina}'
            )

        return render(request, 'rejestracja/wybierz_godzine.html', {
            'lekarz': lekarz,
            'dzien': dzien_obj,
            'wolne_godziny': wolne_godziny,
        })
@login_required
@never_cache
def rezerwuj_wizyte(request):
    lekarz_id = request.GET.get('lekarz_id')
    data = request.GET.get('data')
    godzina = request.GET.get('godzina')
    lekarz = Lekarz.objects.get(id=lekarz_id)
    termin = None
    if data and godzina:
        try:
            termin = Termin.objects.get(lekarz=lekarz, data=data, godzina=godzina)
        except Termin.DoesNotExist:
            termin = Termin.objects.create(
                lekarz=lekarz,
                data=data,
                godzina=godzina,
                dostepny=False
            )

    if request.method == "POST":
        opis = request.POST.get('opis', '')
        profil = Profil.objects.get(user=request.user)
        Wizyta.objects.create(
            pacjent=profil,
            opis=opis,
            lekarz=lekarz,
            termin=termin
        )
        if termin:
            termin.dostepny = False
            termin.save()
        return redirect('historia_wizyt')
    response = render(request, 'rejestracja/rezerwuj_wizyte.html', {
        'lekarz': lekarz,
        'data': data,
        'godzina': godzina
    })
    response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response

@login_required
def historia_wizyt(request):
    profil = Profil.objects.get(user=request.user)
    wizyty = Wizyta.objects.filter(pacjent=profil)
    # Usuń wizyty, których termin już minął (data i godzina <= teraz)
    now = datetime.datetime.now()
    aktywne_wizyty = []
    for w in wizyty:
        if w.termin and w.termin.data and w.termin.godzina:
            termin_datetime = datetime.datetime.combine(w.termin.data, w.termin.godzina)
            if termin_datetime > now:
                aktywne_wizyty.append(w)
        else:
            aktywne_wizyty.append(w)
    today = datetime.date.today()
    return render(request, 'rejestracja/historia_wizyt.html', {'wizyty': aktywne_wizyty, 'today': today})

@login_required
def modyfikuj_wizyte(request, wizyta_id):
    profil = Profil.objects.get(user=request.user)
    wizyta = Wizyta.objects.get(id=wizyta_id, pacjent=profil)
    if request.method == "POST":
        wizyta.opis = request.POST.get('opis', wizyta.opis)
        wizyta.save()
        return redirect('historia_wizyt')
    return render(request, 'rejestracja/modyfikuj_wizyte.html', {'wizyta': wizyta})

@login_required
def dane_pacjenta(request):
    user = request.user
    success = False
    error = None
    telefon_error = None
    # Ensure profil exists for the user
    profil, created = Profil.objects.get_or_create(user=user, defaults={'rola': 'pacjent'})
    current_telefon = profil.telefon if hasattr(profil, 'telefon') else ''
    if request.method == "POST":
        new_email = request.POST.get('email', '').strip()
        new_telefon = request.POST.get('telefon', '').strip()
        # Walidacja numeru telefonu (9 cyfr)
        if not new_telefon.isdigit() or len(new_telefon) != 9:
            telefon_error = "Numer telefonu musi zawierać dokładnie 9 cyfr."
        else:
            if new_email and new_email != user.email:
                if User.objects.filter(email=new_email).exclude(pk=user.pk).exists():
                    error = "Podany adres e-mail jest już zajęty."
                else:
                    user.email = new_email
                    user.save()
                    success = True
            if new_telefon != current_telefon and not telefon_error:
                profil.telefon = new_telefon
                profil.save()
                success = True
            current_telefon = new_telefon  # zaktualizuj do wyświetlenia
    pacjent_data = {
        'first_name': user.first_name,
        'last_name': user.last_name,
        'email': user.email,
        'telefon': current_telefon,
    }
    return render(request, 'rejestracja/dane_pacjenta.html', {
        'pacjent': pacjent_data,
        'success': success,
        'error': error,
        'telefon_error': telefon_error
    })

@login_required
def moj_terminarz(request):
    try:
        profil = Profil.objects.get(user=request.user)
        if profil.rola != 'lekarz':
            return redirect('index')
        lekarz = Lekarz.objects.get(user=request.user)
        # Pokazuj tylko przyszłe wizyty (termin > teraz)
        wizyty = []
        now = datetime.datetime.now()
        for w in Wizyta.objects.filter(lekarz=lekarz):
            if w.termin and w.termin.data and w.termin.godzina:
                termin_datetime = datetime.datetime.combine(w.termin.data, w.termin.godzina)
                if termin_datetime > now:
                    wizyty.append(w)
            else:
                wizyty.append(w)
        return render(request, 'rejestracja/moj_terminarz.html', {'lekarz': lekarz, 'wizyty': wizyty})
    except (Profil.DoesNotExist, Lekarz.DoesNotExist):
        return redirect('index')

@require_POST
@login_required
def anuluj_wizyte(request, wizyta_id):
    profil = Profil.objects.get(user=request.user)
    wizyta = Wizyta.objects.filter(id=wizyta_id, pacjent=profil).first()
    if wizyta:
        wizyta.delete()
    return redirect('historia_wizyt')

@login_required
def usun_konto(request):
    success = False
    already_sent = UsunKontoRequest.objects.filter(user=request.user, potwierdzone=False).exists()
    if request.method == "POST" and not already_sent:
        wiadomosc = request.POST.get('wiadomosc', '')
        user = request.user
        UsunKontoRequest.objects.create(user=user, wiadomosc=wiadomosc)
        success = True
    return render(request, 'rejestracja/usun_konto.html', {'success': success, 'already_sent': already_sent})

@csrf_exempt
@login_required
def usun_termin(request):
    if request.method == "POST":
        lekarz_id = request.GET.get('lekarz_id')
        data = request.GET.get('data')
        if lekarz_id and data:
            try:
                lekarz = Lekarz.objects.get(id=lekarz_id)
                Termin.objects.filter(lekarz=lekarz, data=data).delete()
                return JsonResponse({'status': 'ok'})
            except Lekarz.DoesNotExist:
                pass
    return JsonResponse({'status': 'error'}, status=400)

@login_required
def wiadomosc_do_admina(request):
    profil = Profil.objects.get(user=request.user)
    if profil.rola != 'lekarz':
        return redirect('index')
    success = False
    error = None
    if request.method == "POST":
        tresc = request.POST.get('wiadomosc', '').strip()
        if not tresc:
            error = "Wiadomość nie może być pusta."
        else:
            # Zapisz do bazy
            WiadomoscOdLekarza.objects.create(lekarz=request.user, tresc=tresc)
            # Wyślij do admina
            mail_admins(
                subject=f"Wiadomość od lekarza: {request.user.get_full_name()} ({request.user.username})",
                message=tresc,
                fail_silently=False,
            )
            success = True
    return render(request, 'rejestracja/wiadomosc_do_admina.html', {
        'success': success,
        'error': error
    })
