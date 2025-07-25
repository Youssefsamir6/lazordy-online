# D:\lazordy\lazordy\inventory\models.py
from django.db import models
from decimal import Decimal
from django.db.models import Sum,F,DecimalField
from django.forms import ValidationError
from django.utils import timezone
from datetime import timedelta
import uuid
from django.contrib.auth import get_user_model

# Get the currently active user model (which will be Django's default User if AUTH_USER_MODEL is not set)
User = get_user_model()



def generate_invoice_number(year, month, count):
    return f"LZR-{year}-{month}-{count:04d}"

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
    cost = models.DecimalField(max_digits=10,
                                 decimal_places=2,
                                 null=True,
                                 blank=True,
                                 help_text="The cost price of the product (for calculating profit).")

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
        Size, blank=True, related_name='products_with_this_size',
        help_text="Select available sizes for this product.")

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

    token = models.CharField(max_length=64, blank=True, null=True)
    token_created_at = models.DateTimeField(blank=True, null=True)
    cloud_pdf_url = models.URLField(blank=True, null=True)

    company_address = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        default="FPI, Damietta Furniture Point Mall",
        help_text="Optional company/branch address for this invoice."
    )

    company_phone = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        default="01065881729 - 01126905990 - 01110001559",
        help_text="Optional company phone number for this invoice."
    )

    
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

    manager_discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), # Changed default to Decimal('0.00')
                                                 help_text="Special discount applied by manager.")
    manager_discount_reason = models.CharField(max_length=255, blank=True, null=True,
                                               help_text="Reason for the manager's special discount.")
    
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('visa', 'Visa'),
        ('instapay', 'InstaPay'), # Corrected display name to 'InstaPay'
    ]
    payment_method = models.CharField(
        max_length=50, 
        blank=True, 
        null=True,
        choices=PAYMENT_METHOD_CHOICES,
        help_text="Method of payment."
    )

    notes = models.TextField(blank=True, null=True, help_text="Any additional notes for the invoice.")
    terms_and_conditions = models.TextField(blank=True, null=True, help_text="Terms and conditions for this invoice.")

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
    due_date = models.DateTimeField(
        blank=True,
        null=True,
        help_text="The date by which the invoice amount is due."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

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

    @property
    def subtotal_amount(self):
        return self.items.aggregate(total_sub=Sum('subtotal'))['total_sub'] or Decimal('0.00')

    def save(self, *args, **kwargs):
        now = timezone.now()
        if not self.pk and not self.invoice_number:
            year = now.strftime("%Y")
            month = now.strftime("%m")

            existing_count = Invoice.objects.filter(
                invoice_date__year=now.year,
                invoice_date__month=now.month
            ).count() + 1

            self.invoice_number = generate_invoice_number(year, month, existing_count)

        is_initial_save = not self.pk

        if is_initial_save:
            super().save(*args, **kwargs)
            return

        self.total_amount = self.subtotal_amount - self.discount_amount - self.manager_discount_amount

        if self.amount_paid > self.total_amount:
            self.amount_paid = self.total_amount

        self.amount_remaining = self.total_amount - self.amount_paid

        if self.status != 'cancelled':
            if self.amount_remaining == Decimal('0.00'):
                self.status = 'paid'
            elif self.amount_paid > Decimal('0.00') and self.amount_remaining > Decimal('0.00'):
                self.status = 'uncompleted'
            elif self.amount_paid == Decimal('0.00') and self.total_amount > Decimal('0.00'):
                self.status = 'draft'
            elif self.total_amount == Decimal('0.00'):
                self.status = 'draft'

        super().save(*args, **kwargs)
    def generate_token(self):
        """Generate a secure token and store timestamp"""
        self.token = uuid.uuid4().hex
        self.token_created_at = timezone.now()
        self.save()

    def is_token_valid(self, expiry_minutes=60):  # default: 1 hour
        if not self.token or not self.token_created_at:
            return False
        return timezone.now() <= self.token_created_at + timedelta(minutes=expiry_minutes)

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
        blank=True, 
        null=True)
    quantity = models.PositiveIntegerField(
        default=1,
        help_text="The quantity of the item.")
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="The price per unit of this item")
    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        editable=False,
        help_text="Calculated as quantity * unit_price.")

    class Meta:
        verbose_name = "Invoice Item"
        verbose_name_plural = "Invoice Items"
        ordering = ['id']

    def __str__(self):
        return f"{self.quantity} x {self.product_name} on Invoice {self.invoice.invoice_number}"

    def clean(self):
        if self.product and self.quantity > self.product.quantity:
            raise ValidationError(f"Only {self.product.quantity} in stock for {self.product.name}.")

    def save(self, *args, **kwargs):
        deduct_stock = kwargs.pop('deduct_stock', False)

        is_new = self.pk is None
        previous_quantity = 0

        if not is_new:
            previous = InvoiceItem.objects.get(pk=self.pk)
            previous_quantity = previous.quantity

    # Auto-fill fields
        if self.product:
            if not self.product_name:
                self.product_name = self.product.name
            if not self.unit_price or self.unit_price == Decimal('0.00'):
                self.unit_price = self.product.price

        if not self.product and not self.product_name:
            self.product_name = "Unnamed Item"
        elif not self.unit_price or self.unit_price == Decimal('0.00'):
            raise ValueError("Unit price is required for custom items.")

        self.subtotal = self.quantity * self.unit_price
        # Save item first
        super().save(*args, **kwargs)

        


        # ✅ Deduct or adjust stock safely
        if deduct_stock and self.product:
            diff = self.quantity - previous_quantity
            if diff > 0:
                if self.product.quantity < diff:
                    raise ValueError(f"Insufficient stock for {self.product.name}")
            self.product.quantity -= diff
            self.product.save()

    # ✅ Recalculate invoice totals
        if self.invoice:
            self.invoice.save()


    def delete(self, *args, **kwargs):
        if self.product:
            self.product.quantity += self.quantity
            self.product.save()

        invoice = self.invoice
        super().delete(*args, **kwargs)

    # Recalculate invoice after deletion
        if invoice:
            invoice.save()
        
class Dashboard(models.Model):
    class Meta:
        managed = False
        verbose_name = "Dashboard"
        verbose_name_plural = "Dashboard"
        default_permissions = ()

    def __str__(self):
        return "Inventory Dashboard"
    


LANGUAGE_CHOICES = [
    ('en', 'English'),
    ('ar', 'Arabic'),
]

language = models.CharField(max_length=2, choices=LANGUAGE_CHOICES, default='en')
