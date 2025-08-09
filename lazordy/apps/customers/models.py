from django.db import models
from django.utils.translation import gettext_lazy as _
from phonenumber_field.modelfields import PhoneNumberField
from apps.common.models import TimeStampedModel, UUIDModel


class Customer(UUIDModel, TimeStampedModel):
    name = models.CharField(max_length=150)
    email = models.EmailField(blank=True)
    phone = PhoneNumberField(blank=True, null=True)
    address = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)

    def __str__(self) -> str:
        return self.name
