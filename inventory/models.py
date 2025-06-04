from django.db import models
from decimal import Decimal
from django.db.models import Sum
from django.utils import timezone
import uuid
from django.contrib.auth import get_user_model

User = get_user_model()

def generate_invoice_number():
    return f"INV-{uuid.uuid4().hex[:8].upper()}-{timezone.now().strftime('%Y%m%d')}"

class Category(models.Model):
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="The name of the category (e.g., Chandeliers, Furniture).")
    description = models.TextField(
        blank=True,
        null=True,
        help_text="A brief description of the category.")

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"
        ordering = ['name']

    def __str__(self):
        return self.name


class Size(models.Model):
    name = models.CharField(
        max_length=50,
        unique=True,
        help_text="The name of the size (e.g., 40cm,50cm,60cm,80cm,90cm,100cm).")
    products = models.ManyToManyField('Product', blank=True, related_name='sizes',
                                     help_text="Products that have this size.")
    class Meta:
        verbose_name = "Size"
        verbose_name_plural = "Sizes"
        ordering = ['name']

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=255,
                            help_text="The name of the product.")
    description = models.TextField(
        blank=True,
        null=True,
        help_text="A detailed description of the product.")
    price = models.DecimalField(max_digits=10,
                                 decimal_places=2,
                                 help_text="The selling price of the product.")
    quantity = models.IntegerField(
        default=0, help_text="The current stock quantity of the product.")
    item_code = models.CharField(
        max_length=100,
        unique=True,
        help_text="A unique code for identifying the product.")

    color = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="The color of the product (e.g., 'Red', 'Blue', 'Assorted').")
    measurements_cm = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Measurements of the product in CM (e.g., '10x5x2 cm' or 'Diameter: 15cm').")

    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products',
        help_text="The category this product belongs to.")

    photo = models.ImageField(upload_to='product_photos/',
                              blank=True,
                              null=True,
                              help_text="An image of the product.")

    size = models.ManyToManyField(
        Size, blank=True, help_text="Select available sizes for this product.")

    STATUS_CHOICES = [
        ('available', 'Available'),
        ('sold', 'Sold'),
        ('reserved', 'Reserved'),
        ('out_of_stock', 'Out of Stock'),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='available',
        help_text="The current availability status of the product.")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Product"
        verbose_name_plural = "Products"
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.item_code})"


class Invoice(models.Model):
    invoice_number = models.CharField(
        max_length=100,
        unique=True,
        editable=False,
        help_text="A unique identifier for the invoice.")
    customer_name = models.CharField(
        max_length=255,
        help_text="The name of the customer for this invoice.")
    home_address = models.TextField(
        blank=True,
        null=True,
        help_text="The customer's home address.")
    customer_phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="The customer's phone number.")
    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Discount applied to the total invoice amount (e.g., 10.00 for $10 discount)."
    )
    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        editable=False,
        help_text="The total amount of the invoice after discount. Calculated automatically.")

    amount_paid = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="The amount paid by the customer for this invoice."
    )
    amount_remaining = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        editable=False,
        help_text="The remaining balance for this invoice."
    )

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('uncompleted', 'Uncompleted'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled'),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        help_text="The current status of the invoice.")

    invoice_date = models.DateTimeField(default=timezone.now)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # These fields MUST be indented to be part of the Invoice class
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='invoices_created',
        help_text="The user who created this invoice."
    )
    last_modified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='invoices_modified',
        help_text="The user who last modified this invoice."
    )

    class Meta:
        verbose_name = "Invoice"
        verbose_name_plural = "Invoices"
        ordering = ['-created_at']

    def __str__(self):
        return f"Invoice {self.invoice_number} for {self.customer_name}"

    def save(self, *args, **kwargs):
        if not self.pk and not self.invoice_number:
            self.invoice_number = generate_invoice_number()

        if not self.pk:
            super().save(*args, **kwargs)

        calculated_subtotal = self.items.all().aggregate(total_sub=Sum('subtotal'))['total_sub'] or Decimal('0.00')

        self.total_amount = calculated_subtotal - self.discount_amount

        if self.amount_paid > self.total_amount:
            self.amount_paid = self.total_amount

        self.amount_remaining = self.total_amount - self.amount_paid

        if self.amount_remaining == Decimal('0.00') and self.status != 'cancelled':
            self.status = 'paid'
        elif self.amount_paid > Decimal('0.00') and self.amount_remaining > Decimal('0.00') and self.status not in ['draft', 'cancelled']:
            self.status = 'uncompleted'
        elif self.amount_paid == Decimal('0.00') and self.total_amount > Decimal('0.00') and self.status not in ['draft', 'cancelled']:
            self.status = 'draft'
        elif self.total_amount == Decimal('0.00') and self.status not in ['draft', 'cancelled']:
            self.status = 'draft'

        super().save(*args, **kwargs)


class InvoiceItem(models.Model):
    invoice = models.ForeignKey(Invoice,
                                on_delete=models.CASCADE,
                                related_name='items',
                                help_text="The invoice this item belongs to.")
    product = models.ForeignKey(Product,
                                on_delete=models.SET_NULL,
                                null=True,
                                blank=True,
                                related_name='invoice_lines',
                                help_text="The product being invoiced (can be null if product deleted).")
    product_name = models.CharField(
        max_length=255,
        editable=False,
        help_text="The name of the product at the time of invoicing (stored for historical accuracy).")
    quantity = models.PositiveIntegerField(
        default=1,
        help_text="The quantity of the product in this invoice item.")
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="The price of the product at the time of invoicing.")
    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        editable=False,
        help_text="Calculated as quantity * unit_price.")

    class Meta:
        verbose_name = "Invoice Item"
        verbose_name_plural = "Invoice Items"
        unique_together = ('invoice', 'product')
        ordering = ['id']


    def __str__(self):
        return f"{self.quantity} x {self.product_name} on Invoice {self.invoice.invoice_number}"

    def save(self, *args, **kwargs):
        if self.product:
            if not self.product_name:
                self.product_name = self.product.name
            if self.unit_price == Decimal('0.00'):
                self.unit_price = self.product.price

        self.subtotal = self.quantity * self.unit_price

        super().save(*args, **kwargs)

        if self.invoice:
            self.invoice.save()