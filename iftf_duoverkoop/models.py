from django.db import models
from django.utils.translation import gettext as _


class Association(models.Model):
    name = models.CharField(max_length=100, unique=True, primary_key=True)
    image = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.name


class Performance(models.Model):
    key = models.CharField("Key", max_length=128, unique=True, primary_key=True)
    date = models.DateTimeField("Date")
    association = models.ForeignKey(Association, on_delete=models.CASCADE)
    name = models.CharField("Name", max_length=128)
    price = models.FloatField("Price")
    max_tickets = models.IntegerField("Maximum Tickets")

    def tickets_sold(self):
        return Purchase.objects.filter(ticket1__key=self.key).count() + Purchase.objects.filter(
            ticket2__key=self.key).count()

    def tickets_left(self):
        return self.max_tickets - self.tickets_sold()

    def __str__(self):
        return self.key

    def selection(self):
        return _('performance.tostring') % {
            'date': self.date.strftime("%d / %b"),
            'association': self.association,
            'name': self.name
        }


class Purchase(models.Model):
    date = models.DateTimeField("Date")
    name = models.CharField("Name", max_length=128)
    email = models.EmailField("Email")
    ticket1 = models.ForeignKey(Performance, on_delete=models.PROTECT, related_name="ticket1")
    ticket2 = models.ForeignKey(Performance, on_delete=models.PROTECT, related_name="ticket2")

    def __str__(self):
        return f"Purchase {self.id} by {self.name}"
