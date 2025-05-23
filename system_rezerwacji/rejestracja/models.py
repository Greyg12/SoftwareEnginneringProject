from django.db import models
from django.contrib.auth.models import User


class Lekarz(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    specjalizacja = models.CharField(max_length=100)
    zatwierdzony = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.specjalizacja})"


class Profil(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    
    ROLA_CHOICES = (
        ('pacjent', 'Pacjent'),
        ('lekarz', 'Lekarz'),
    )
    rola = models.CharField(max_length=10, choices=ROLA_CHOICES, default='pacjent')
    telefon = models.CharField(max_length=15, blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.rola}"


class Termin(models.Model):
    lekarz = models.ForeignKey(Lekarz, on_delete=models.CASCADE)
    data = models.DateField()
    godzina = models.TimeField()
    dostepny = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.data} {self.godzina} - {self.lekarz}"


class Wizyta(models.Model):
    pacjent = models.ForeignKey(Profil, on_delete=models.CASCADE, related_name='wizyty', null=True, blank=True)
    lekarz = models.ForeignKey(Lekarz, on_delete=models.CASCADE, null=True, blank=True)
    termin = models.ForeignKey(Termin, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        pacjent_str = self.pacjent.user.get_full_name() if self.pacjent else "Brak pacjenta"
        termin_str = str(self.termin) if self.termin else "Brak terminu"
        return f"{pacjent_str} - {termin_str}"


class UsunKontoRequest(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    wiadomosc = models.TextField()
    data_zgloszenia = models.DateTimeField(auto_now_add=True)
    potwierdzone = models.BooleanField(default=False)

    def __str__(self):
        return f"Prośba o usunięcie konta: {self.user.username}"


class WiadomoscOdLekarza(models.Model):
    lekarz = models.ForeignKey(Lekarz, on_delete=models.CASCADE)
    tresc = models.TextField()
    data_wyslania = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return (
            f"Wiadomość od {self.lekarz.user.get_full_name()} "
            f"({self.lekarz.user.username}) z {self.data_wyslania.strftime('%Y-%m-%d %H:%M')}"
        )
