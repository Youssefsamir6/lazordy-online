from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from apps.common.models import TimeStampedModel, UUIDModel
from apps.customers.models import Customer
from apps.inventory.models import Product


class InvoiceStatus(models.TextChoices):
    DRAFT = 'draft', _('Draft')
    SENT = 'sent', _('Sent')
    UNCOMPLETED = 'uncompleted', _('Uncompleted')
    PAID = 'paid', _('Paid')
    CANCELLED = 'cancelled', _('Cancelled')


class PaymentMethod(models.TextChoices):
    CASH = 'cash', _('Cash')
    VISA = 'visa', _('Visa')
    INSTAPAY = 'instapay', _('Instapay')


class Invoice(UUIDModel, TimeStampedModel):
    number = models.CharField(max_length=30, unique=True, blank=True)
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, related_name='invoices')
    status = models.CharField(max_length=20, choices=InvoiceStatus.choices, default=InvoiceStatus.DRAFT)
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    manager_discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices, default=PaymentMethod.CASH)
    notes = models.TextField(blank=True)
    token = models.CharField(max_length=64, unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.number:
            today = timezone.now().date()
            prefix = getattr(settings, 'INVOICE_PREFIX', 'LZR')
            date_part = today.strftime('%Y-%m')
            last = Invoice.objects.filter(created_at__date__month=today.month, created_at__date__year=today.year).order_by('-created_at').first()
            seq = 1
            if last and last.number and last.number.split('-')[-1].isdigit():
                seq = int(last.number.split('-')[-1]) + 1
            self.number = f"{prefix}-{date_part}-{seq:04d}"
        if not self.token:
            from uuid import uuid4
            self.token = uuid4().hex
        super().save(*args, **kwargs)

    @property
    def subtotal(self):
        return sum(item.subtotal for item in self.items.all())

    @property
    def total_discount(self):
        return self.discount + self.manager_discount

    @property
    def total(self):
        return max(self.subtotal - self.total_discount, 0)

    def __str__(self) -> str:
        return self.number or str(self.id)


class InvoiceItem(UUIDModel, TimeStampedModel):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=12, decimal_places=2)

    @property
    def subtotal(self):
        return self.quantity * self.price

    def __str__(self) -> str:
        return f"{self.product} x {self.quantity}"
