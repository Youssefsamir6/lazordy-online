# D:\lazordy\lazordy\inventory\forms.py

from django import forms
from .models import Product, Category, Size, Invoice, InvoiceItem 
from django.utils.translation import gettext_lazy as _

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'name',
            'item_code',
            'category',
            'size',
            'description',
            'price',
            'cost',
            'quantity',
            'photo',
            'status',
            'color',
            # Ensure 'measurements' is NOT here.
            # If 'measurements' is truly a field in your Product model, then add it back to models.py first.
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'price': forms.NumberInput(attrs={'step': '0.01'}),
            'cost': forms.NumberInput(attrs={'step': '0.01'}),
            'quantity': forms.NumberInput(attrs={'min': '0'}),
        }
        labels = {
            'name': _('Product Name'),
            'item_code': _('Item Code (Unique)'),
            'category': _('Category'),
            'size': _('Available Sizes'),
            'description': _('Description'),
            'price': _('Selling Price (EGP)'),
            'cost': _('Cost Price (EGP)'),
            'quantity': _('Current Stock Quantity'),
            'photo': _('Product Image'),
            'status': _('Status'),
            'color': _('Color'),
            # Ensure 'measurements' label is NOT here.
        }

    def clean_item_code(self):
        item_code = self.cleaned_data['item_code']
        if self.instance and self.instance.item_code == item_code: 
            return item_code
        if Product.objects.filter(item_code=item_code).exists():
            raise forms.ValidationError(_("This item code already exists. Please choose a unique one."))
        return item_code
        
# (Rest of your forms.py below, like InvoiceForm and InvoiceItemForm, remains unchanged from the last correct version)

class InvoiceForm(forms.ModelForm):

    show_product_photos = forms.BooleanField(required=False, label=_("Show product photos in PDF"))

    class Meta:
        model = Invoice
        fields = [
            'customer_name',
            'home_address', 
            'customer_phone',
            'company_address',
            'company_phone',
            'invoice_date',
            'due_date',      
            'status',
            'discount_amount',
            'manager_discount_amount',
            'manager_discount_reason',
            'amount_paid',
            'payment_method',
            'notes',
            'terms_and_conditions',
            'show_product_photos',  # ✅ corrected name
        ]
        widgets = {
            'invoice_date': forms.DateInput(attrs={'type': 'date'}),
            'due_date': forms.DateInput(attrs={'type': 'date'}), 
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.initial.setdefault('company_address', _("FPI, Damietta Furniture Point Mall"))
        self.initial.setdefault('company_phone', _("01065881729 - 01126905990 - 01110001559"))
        
        self.fields['customer_name'].label = _("Customer Name")
        self.fields['home_address'].label = _("Home Address")
        self.fields['customer_phone'].label = _("Customer Phone")
        self.fields['company_address'].label = _("Company Address")
        self.fields['company_phone'].label = _("Company Phone")
        self.fields['invoice_date'].label = _("Invoice Date")
        self.fields['due_date'].label = _("Due Date")
        self.fields['status'].label = _("Status")
        self.fields['discount_amount'].label = _("Discount Amount")
        self.fields['manager_discount_amount'].label = _("Manager's Discount Amount")
        self.fields['manager_discount_reason'].label = _("Reason for Manager's Discount")
        self.fields['amount_paid'].label = _("Amount Paid")
        self.fields['payment_method'].label = _("Payment Method")
        self.fields['notes'].label = _("Notes")
        self.fields['terms_and_conditions'].label = _("Terms and Conditions")
        self.fields['show_product_photos'].label = _("Show product photos in PDF")  

class InvoiceItemForm(forms.ModelForm):
    class Meta:
        model = InvoiceItem
        fields = ['product', 'product_name', 'quantity', 'unit_price']
        widgets = {
            'unit_price': forms.NumberInput(attrs={'step': '0.01'}),
            'quantity': forms.NumberInput(attrs={'min': '1'}),
        }
        labels = {
            'product': _('Product'),
            'product_name': _('Product Name (Custom)'),
            'quantity': _('Quantity'),
            'unit_price': _('Unit Price'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['product'].queryset = Product.objects.filter(status='available').order_by('name')
        self.fields['product'].required = False
        self.fields['product_name'].required = False

    def clean(self):
        cleaned_data = super().clean()
        product = cleaned_data.get("product")
        product_name = cleaned_data.get("product_name")
        unit_price = cleaned_data.get("unit_price")

        if not product and not product_name:
            raise forms.ValidationError(_("You must select a product or enter a product name."))

        if product:
            if not product_name:
                cleaned_data['product_name'] = product.name
            if not unit_price:
                cleaned_data['unit_price'] = product.price

        if not unit_price or unit_price <= 0:
            raise forms.ValidationError(_("Unit price must be greater than zero."))

        return cleaned_data