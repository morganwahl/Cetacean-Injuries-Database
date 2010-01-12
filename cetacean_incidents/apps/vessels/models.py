from django.db import models
from cetacean_incidents.apps.contacts.models import PhoneNumber

class Vessel(models.Model):
    name = models.CharField(
        max_length= 255,
        blank= True,
    )
    call_sign = models.CharField(
        max_length= 255,
        blank= True,
    )
    phones = models.ManyToManyField(
        PhoneNumber,
        blank= True,
        null= True,
    )
    