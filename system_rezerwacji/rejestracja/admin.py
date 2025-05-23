from django.contrib import admin
from .models import Lekarz, Termin, UsunKontoRequest, WiadomoscOdLekarza
from .models import Wizyta  # Dodaj ten import
from django.contrib import messages
from django.contrib.auth.models import User
from django.utils.html import format_html
from django.urls import path
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django import forms
from django.contrib.auth.hashers import make_password


class LekarzCreateForm(forms.ModelForm):
    username = forms.CharField(label="Login", max_length=150)
    first_name = forms.CharField(label="Imię", max_length=30)
    last_name = forms.CharField(label="Nazwisko", max_length=150)
    email = forms.EmailField(label="Email")
    telefon = forms.CharField(label="Telefon", max_length=15)
    password = forms.CharField(label="Hasło", widget=forms.PasswordInput)
    specjalizacja = forms.CharField(label="Specjalizacja", max_length=100)

    class Meta:
        model = Lekarz
        fields = ('username', 'first_name', 'last_name', 'email', 'telefon', 'specjalizacja', 'password')

    def clean_username(self):
        username = self.cleaned_data['username']
        from django.contrib.auth.models import User
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("Użytkownik o tym loginie już istnieje.")
        return username

    def clean_email(self):
        email = self.cleaned_data['email']
        from django.contrib.auth.models import User
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Użytkownik o tym adresie email już istnieje.")
        return email

    def save(self, commit=True):
        # Utwórz użytkownika i lekarza
        from django.contrib.auth.models import User
        user = User(
            username=self.cleaned_data['username'],
            first_name=self.cleaned_data['first_name'],
            last_name=self.cleaned_data['last_name'],
            email=self.cleaned_data['email'],
        )
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        lekarz = Lekarz(user=user, specjalizacja=self.cleaned_data['specjalizacja'], zatwierdzony=True)
        if commit:
            lekarz.save()
        # Dodaj profil z rolą lekarz i telefonem
        from .models import Profil
        profil, _ = Profil.objects.get_or_create(user=user)
        profil.rola = 'lekarz'
        profil.telefon = self.cleaned_data['telefon']
        profil.save()
        return lekarz


@admin.register(Lekarz)
class LekarzAdmin(admin.ModelAdmin):
    list_display = ('user', 'first_name', 'last_name', 'specjalizacja', 'zatwierdzony')
    list_filter = ('zatwierdzony', 'specjalizacja')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'specjalizacja')
    actions = ['aktywuj_lekarzy', 'odrzuc_lekarzy']
    add_form = LekarzCreateForm

    def get_form(self, request, obj=None, **kwargs):
        if obj is None:
            return self.add_form
        return super().get_form(request, obj, **kwargs)

    def add_view(self, request, form_url='', extra_context=None):
        if request.method == 'POST':
            form = self.add_form(request.POST)
            if form.is_valid():
                form.save()
                self.message_user(request, "Lekarz został dodany.")
                from django.urls import reverse
                return redirect(reverse('admin:rejestracja_lekarz_changelist'))
        else:
            form = self.add_form()
        context = {
            **self.admin_site.each_context(request),
            'title': 'Dodaj lekarza',
            'form': form,
            'opts': self.model._meta,
        }
        return TemplateResponse(request, 'admin/lekarz_add_form.html', context)

    def first_name(self, obj):
        return obj.user.first_name
    first_name.short_description = "Imię"
    first_name.admin_order_field = 'user__first_name'

    def last_name(self, obj):
        return obj.user.last_name
    last_name.short_description = "Nazwisko"
    last_name.admin_order_field = 'user__last_name'

    @admin.action(description="Aktywuj wybranych lekarzy")
    def aktywuj_lekarzy(self, request, queryset):
        queryset.update(zatwierdzony=True)

    @admin.action(description="Odrzuć wybranych lekarzy")
    def odrzuc_lekarzy(self, request, queryset):
        queryset.update(zatwierdzony=False)





@admin.register(Termin)
class TerminAdmin(admin.ModelAdmin):
    list_display = ('lekarz', 'data', 'godzina', 'dostepny', 'get_pacjent')
    list_filter = ('lekarz', 'dostepny', 'data')
    search_fields = ('lekarz__user__first_name', 'lekarz__user__last_name', 'data', 'godzina', 'wizyta__imie', 'wizyta__nazwisko')
    ordering = ('data', 'godzina')

    def get_pacjent(self, obj):
        wizyta = Wizyta.objects.filter(termin=obj).first()
        if wizyta:
            return f"{wizyta.imie} {wizyta.nazwisko}"
        return "-"
    get_pacjent.short_description = "Pacjent"
    get_pacjent.admin_order_field = 'wizyta__nazwisko'

@admin.register(UsunKontoRequest)
class UsunKontoRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'wiadomosc', 'data_zgloszenia', 'potwierdzone', 'potwierdz_link', 'anuluj_link')
    readonly_fields = ('user', 'wiadomosc', 'data_zgloszenia', 'potwierdzone')

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('potwierdz/<int:request_id>/', self.admin_site.admin_view(self.potwierdz_usuniecie), name='potwierdz_usuniecie_konta'),
            path('anuluj/<int:request_id>/', self.admin_site.admin_view(self.anuluj_prosbe), name='anuluj_prosbe_usuniecia_konta'),
        ]
        return custom_urls + urls

    def potwierdz_link(self, obj):
        if not obj.potwierdzone:
            return format_html(
                '<a class="button" href="{}">Potwierdź usunięcie</a>',
                f'potwierdz/{obj.id}/'
            )
        return "Potwierdzone"
    potwierdz_link.short_description = "Akcja"

    def anuluj_link(self, obj):
        if not obj.potwierdzone:
            return format_html(
                '<a class="button" style="background:#888;padding:4px 10px;border-radius:4px;" href="{}">Anuluj prośbę</a>',
                f'anuluj/{obj.id}/'
            )
        return "-"
    anuluj_link.short_description = "Anuluj"

    def potwierdz_usuniecie(self, request, request_id):
        req = UsunKontoRequest.objects.get(id=request_id)
        if not req.potwierdzone:
            user = req.user
            req.potwierdzone = True
            req.save()
            user.delete()
            messages.success(request, f"Konto użytkownika {user.username} zostało usunięte.")
        return redirect('..')

    def anuluj_prosbe(self, request, request_id):
        req = UsunKontoRequest.objects.get(id=request_id)
        if not req.potwierdzone:
            req.delete()
            messages.success(request, "Prośba o usunięcie konta została anulowana.")
        return redirect('..')

@admin.register(WiadomoscOdLekarza)
class WiadomoscOdLekarzaAdmin(admin.ModelAdmin):
    list_display = ('lekarz', 'data_wyslania', 'skrot_tresci')
    search_fields = ('lekarz__username', 'lekarz__first_name', 'lekarz__last_name', 'tresc')
    readonly_fields = ('lekarz', 'tresc', 'data_wyslania')

    def skrot_tresci(self, obj):
        return (obj.tresc[:60] + '...') if len(obj.tresc) > 60 else obj.tresc
    skrot_tresci.short_description = "Treść"

class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'first_name', 'last_name', 'email', 'telefon', 'rola')
    search_fields = ('username', 'first_name', 'last_name', 'email')
    list_filter = ('is_staff', 'is_superuser', 'is_active')
    ordering = ('username',)

    def telefon(self, obj):
        profil = getattr(obj, 'profil', None)
        return profil.telefon if profil and hasattr(profil, 'telefon') else '-'
    telefon.short_description = "Telefon"
    telefon.admin_order_field = 'profil__telefon'

    def rola(self, obj):
        profil = getattr(obj, 'profil', None)
        return profil.rola if profil else '-'
    rola.short_description = "Rola"
    rola.admin_order_field = 'profil__rola'

# Re-register User with the new admin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)

