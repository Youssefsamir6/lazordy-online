from django.db import models, transaction
from decimal import Decimal
from django.db.models import Sum, F, DecimalField
from django.forms import ValidationError
from django.utils import timezone
from datetime import timedelta
import uuid
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

User = get_user_model()


def generate_invoice_number(year, month, count):
    return f"LZR-{year}-{month}-{count:04d}"


class Category(models.Model):
    name = models.CharField(
        verbose_name=_("Name"),
        max_length=100,
        unique=True,
        help_text=_("The name of the category (e.g., Chandeliers, Furniture)."))
    description = models.TextField(
        verbose_name=_("Description"),
        blank=True,
        null=True,
        help_text=_("A brief description of the category."))

    class Meta:
        verbose_name = _("Category")
        verbose_name_plural = _("Categories")
        ordering = ['name']

    def __str__(self):
        return self.name


class Size(models.Model):
    name = models.CharField(
        verbose_name=_("Name"),
        max_length=50,
        unique=True,
        help_text=_("The name of the size (e.g., 40cm,50cm,60cm,80cm,90cm,100cm)."))

    class Meta:
        verbose_name = _("Size")
        verbose_name_plural = _("Sizes")
        ordering = ['name']

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(
        verbose_name=_("Name"),
        max_length=255,
        help_text=_("The name of the product."))
    description = models.TextField(
        verbose_name=_("Description"),
        blank=True,
        null=True,
        help_text=_("A detailed description of the product."))
    price = models.DecimalField(
        verbose_name=_("Price"),
        max_digits=10,
        decimal_places=2,
        help_text=_("The selling price of the product."))
    cost = models.DecimalField(
        verbose_name=_("Cost"),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("The cost price of the product (for calculating profit)."))
    quantity = models.IntegerField(
        verbose_name=_("Quantity"),
        default=0,
        help_text=_("The current stock quantity of the product."))
    item_code = models.CharField(
        verbose_name=_("Item Code"),
        max_length=100,
        unique=True,
        help_text=_("A unique code for identifying the product."))
    color = models.CharField(
        verbose_name=_("Color"),
        max_length=50,
        blank=True,
        null=True,
        help_text=_("The color of the product (e.g., 'Red', 'Blue', 'Assorted')."))
    measurements = models.CharField(
        verbose_name=_("Measurements"),
        max_length=255,
        blank=True,
        null=True,
        help_text=_("Measurements of the product in CM (e.g., '12 LAMP' or 'Diameter: 15cm')."))
    category = models.ForeignKey(
        Category,
        verbose_name=_("Category"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products',
        help_text=_("The category this product belongs to."))
    photo = models.ImageField(
        verbose_name=_("Photo"),
        upload_to='product_photos/',
        blank=True,
        null=True,
        help_text=_("An image of the product."))
    size = models.ManyToManyField(
        Size,
        verbose_name=_("Size"),
        blank=True,
        related_name='products_with_this_size',
        help_text=_("Select available sizes for this product."))
    STATUS_CHOICES = [
        ('available', _('Available')),
        ('sold', _('Sold')),
        ('reserved', _('Reserved')),
        ('out_of_stock', _('Out of Stock')),
    ]
    status = models.CharField(
        verbose_name=_("Status"),
        max_length=20,
        choices=STATUS_CHOICES,
        default='available',
        help_text=_("The current availability status of the product."))
    created_at = models.DateTimeField(verbose_name=_("Created At"), auto_now_add=True)
    updated_at = models.DateTimeField(verbose_name=_("Updated At"), auto_now=True)

    class Meta:
        verbose_name = _("Product")
        verbose_name_plural = _("Products")
        ordering = ['name']

    def __str__(self):
        return _("%(name)s (%(item_code)s)") % {'name': self.name, 'item_code': self.item_code}


class Invoice(models.Model):
    invoice_number = models.CharField(
        verbose_name=_("Invoice Number"),
        max_length=100,
        unique=True,
        editable=False,
        help_text=_("A unique identifier for the invoice.")
    )
    token = models.CharField(verbose_name=_("Token"), max_length=64, blank=True, null=True)
    token_created_at = models.DateTimeField(verbose_name=_("Token Created At"), blank=True, null=True)
    cloud_pdf_url = models.URLField(verbose_name=_("Cloud PDF URL"), blank=True, null=True)
    company_address = models.CharField(
        verbose_name=_("Company Address"),
        max_length=255,
        blank=True,
        null=True,
        default="FPI, Damietta Furniture Point Mall",
        help_text=_("Optional company/branch address for this invoice."))
    company_phone = models.CharField(
        verbose_name=_("Company Phone"),
        max_length=255,
        blank=True,
        null=True,
        default="01065881729 - 01126905990 - 01110001559",
        help_text=_("Optional company phone number for this invoice."))
    customer_name = models.CharField(
        verbose_name=_("Customer Name"),
        max_length=255,
        help_text=_("The name of the customer for this invoice."))
    home_address = models.TextField(
        verbose_name=_("Home Address"),
        blank=True,
        null=True,
        help_text=_("The customer's home address."))
    customer_phone = models.CharField(
        verbose_name=_("Customer Phone"),
        max_length=20,
        blank=True,
        null=True,
        help_text=_("The customer's phone number."))
    show_product_photos = models.BooleanField(
        verbose_name=_("Show Product Photos"),
        default=False,
        help_text=_("show product photos in the invoice PDF."))
    discount_amount = models.DecimalField(
        verbose_name=_("Discount Amount"),
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text=_("Discount applied to the total invoice amount (e.g., 10.00 for $10 discount)."))
    manager_discount_amount = models.DecimalField(
        verbose_name=_("Manager Discount Amount"),
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text=_("Special discount applied by manager."))
    manager_discount_reason = models.CharField(
        verbose_name=_("Manager Discount Reason"),
        max_length=255,
        blank=True,
        null=True,
        help_text=_("Reason for the manager's special discount."))
    PAYMENT_METHOD_CHOICES = [
        ('cash', _('Cash')),
        ('visa', _('Visa')),
        ('instapay', _('InstaPay')),
    ]
    payment_method = models.CharField(
        verbose_name=_("Payment Method"),
        max_length=50,
        blank=True,
        null=True,
        choices=PAYMENT_METHOD_CHOICES,
        help_text=_("Method of payment."))
    notes = models.TextField(verbose_name=_("Notes"), blank=True, null=True, help_text=_("Any additional notes for the invoice."))
    terms_and_conditions = models.TextField(
        verbose_name=_("Terms and Conditions"),
        blank=True,
        null=True,
        help_text=_("Terms and conditions for this invoice."))
    subtotal_amount = models.DecimalField(
        verbose_name=_("Subtotal Amount"),
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        editable=False,
        help_text=_("The sum of all items. Calculated automatically."))
    total_amount = models.DecimalField(
        verbose_name=_("Total Amount"),
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        editable=False,
        help_text=_("The total amount of the invoice after discount. Calculated automatically."))
    amount_paid = models.DecimalField(
        verbose_name=_("Amount Paid"),
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text=_("The amount paid by the customer for this invoice."))
    amount_remaining = models.DecimalField(
        verbose_name=_("Amount Remaining"),
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        editable=False,
        help_text=_("The remaining balance for this invoice."))
    STATUS_CHOICES = [
        ('draft', _('Draft')),
        ('sent', _('Sent')),
        ('uncompleted', _('Uncompleted')),
        ('paid', _('Paid')),
        ('cancelled', _('Cancelled')),
    ]
    status = models.CharField(
        verbose_name=_("Status"),
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        help_text=_("The current status of the invoice."))
    invoice_date = models.DateTimeField(verbose_name=_("Invoice Date"), default=timezone.now)
    due_date = models.DateTimeField(
        verbose_name=_("Due Date"),
        blank=True,
        null=True,
        help_text=_("The date by which the invoice amount is due."))
    created_at = models.DateTimeField(verbose_name=_("Created At"), auto_now_add=True)
    updated_at = models.DateTimeField(verbose_name=_("Updated At"), auto_now=True)
    created_by = models.ForeignKey(
        User,
        verbose_name=_("Created By"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='invoices_created',
        help_text=_("The user who created this invoice."))
    last_modified_by = models.ForeignKey(
        User,
        verbose_name=_("Last Modified By"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='invoices_modified',
        help_text=_("The user who last modified this invoice."))
    show_product_photos = models.BooleanField(
        verbose_name=_("Show Product Photos"),
        default=False,
        help_text=_("show product photos in the invoice PDF."))

    class Meta:
        verbose_name = _("Invoice")
        verbose_name_plural = _("Invoices")
        ordering = ['-created_at']

    def __str__(self):
        return _("Invoice %(invoice_number)s for %(customer_name)s") % {
            'invoice_number': self.invoice_number,
            'customer_name': self.customer_name
        }

    def calculate_totals(self):
        self.subtotal_amount = self.items.aggregate(total_sub=Sum('subtotal'))['total_sub'] or Decimal('0.00')
        self.total_amount = self.subtotal_amount - self.discount_amount - self.manager_discount_amount
        if self.amount_paid > self.total_amount:
            self.amount_paid = self.total_amount
        self.amount_remaining = self.total_amount - self.amount_paid

        if self.status not in ['cancelled', 'paid']:  # Only auto-update if not manually set to paid or cancelled
            if self.amount_remaining <= Decimal('0.00'):
                self.status = 'paid'
            elif self.amount_paid > Decimal('0.00'):
                self.status = 'uncompleted'
            else:
                self.status = 'draft'

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            self.invoice_number = self.generate_unique_invoice_number()
        
        super().save(*args, **kwargs)

    def generate_unique_invoice_number(self):
        max_retries = 5
        retry_delay = 0.1
        for attempt in range(max_retries):
            try:
                with transaction.atomic():
                    now = timezone.now()
                    year = now.strftime("%Y")
                    month = now.strftime("%m")
                    last_invoice = Invoice.objects.select_for_update().filter(
                        invoice_date__year=now.year,
                        invoice_date__month=now.month
                    ).order_by('-id').first()
                    
                    if last_invoice:
                        try:
                            last_sequence = int(last_invoice.invoice_number.split('-')[-1])
                        except (ValueError, IndexError):
                            last_sequence = 0
                        new_sequence = last_sequence + 1
                    else:
                        new_sequence = 1
                    
                    new_invoice_number = generate_invoice_number(year, month, new_sequence)
                    if not Invoice.objects.filter(invoice_number=new_invoice_number).exists():
                        return new_invoice_number
                        
            except IntegrityError:
                if attempt == max_retries - 1:
                    timestamp = int(timezone.now().timestamp() * 1000)
                    return f"LZR-{year}-{month}-{timestamp}"
                time.sleep(retry_delay * (attempt + 1))
        
        return f"LZR-{timezone.now().strftime('%Y%m%d%H%M%S')}"

    def generate_token(self):
        self.token = uuid.uuid4().hex
        self.token_created_at = timezone.now()
        self.save()

    def is_token_valid(self, expiry_minutes=60):
        if not self.token or not self.token_created_at:
            return False
        return timezone.now() <= self.token_created_at + timedelta(minutes=expiry_minutes)


class InvoiceItem(models.Model):
    invoice = models.ForeignKey(
        Invoice,
        verbose_name=_("Invoice"),
        on_delete=models.CASCADE,
        related_name='items',
        help_text=_("The invoice this item belongs to."))
    product = models.ForeignKey(
        Product,
        verbose_name=_("Product"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='invoice_lines',
        help_text=_("The product being invoiced (can be null if product deleted)."))
    product_name = models.CharField(
        verbose_name=_("Product Name"),
        max_length=255,
        blank=True,
        null=True)
    quantity = models.PositiveIntegerField(
        verbose_name=_("Quantity"),
        default=1,
        help_text=_("The quantity of the item."))
    unit_price = models.DecimalField(
        verbose_name=_("Unit Price"),
        max_digits=10,
        decimal_places=2,
        help_text=_("The price per unit of this item"))
    subtotal = models.DecimalField(
        verbose_name=_("Subtotal"),
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        editable=False,
        help_text=_("Calculated as quantity * unit_price."))

    class Meta:
        verbose_name = _("Invoice Item")
        verbose_name_plural = _("Invoice Items")
        ordering = ['id']

    def __str__(self):
        return _("%(quantity)s x %(product_name)s on Invoice %(invoice_number)s") % {
            'quantity': self.quantity,
            'product_name': self.product_name,
            'invoice_number': self.invoice.invoice_number
        }

    def clean(self):
        if self.product and self.quantity > self.product.quantity:
            raise ValidationError(_("Only %(quantity)s in stock for %(product_name)s.") % {
                'quantity': self.product.quantity,
                'product_name': self.product.name
            })

    def save(self, *args, **kwargs):
        deduct_stock = kwargs.pop('deduct_stock', False)
        is_new = self.pk is None
        previous_quantity = 0
        if not is_new:
            try:
                previous = InvoiceItem.objects.get(pk=self.pk)
                previous_quantity = previous.quantity
            except InvoiceItem.DoesNotExist:
                previous_quantity = 0

        if self.product:
            if not self.product_name:
                self.product_name = self.product.name
            if not self.unit_price or self.unit_price == Decimal('0.00'):
                self.unit_price = self.product.price

        if not self.product and not self.product_name:
            self.product_name = _("Unnamed Item")
        elif not self.unit_price or self.unit_price == Decimal('0.00'):
            raise ValueError(_("Unit price is required for custom items."))

        self.subtotal = self.quantity * self.unit_price
        super().save(*args, **kwargs)

        if deduct_stock and self.product:
            diff = self.quantity - previous_quantity
            if diff > 0:
                if self.product.quantity < diff:
                    raise ValueError(_("Insufficient stock for %(product_name)s") % {'product_name': self.product.name})
            self.product.quantity = F('quantity') - diff
            self.product.save(update_fields=['quantity'])


    def delete(self, *args, **kwargs):
        if self.product:
            self.product.quantity = F('quantity') + self.quantity
            self.product.save(update_fields=['quantity'])

        super().delete(*args, **kwargs)

class Dashboard(models.Model):
    class Meta:
        managed = False
        verbose_name = _("Dashboard")
        verbose_name_plural = _("Dashboard")
        default_permissions = ()

    def __str__(self):
        return _("Inventory Dashboard")


LANGUAGE_CHOICES = [
    ('en', _('English')),
    ('ar', _('Arabic')),
]
language = models.CharField(verbose_name=_("Language"), max_length=2, choices=LANGUAGE_CHOICES, default='en')