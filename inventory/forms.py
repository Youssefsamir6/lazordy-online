# D:\lazordy\lazordy\inventory\forms.py

from django import forms
from .models import Product, Category, Size,Invoice, InvoiceItem 
from django.utils.translation import gettext_lazy as _

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'name',
            'item_code',
            'category',
            'size',  # CORRECTED: Changed from 'sizes' to 'size'
            'description',
            'price',
            'cost',  # CORRECTED: This field now exists in the model
            'quantity',
            'photo', # CORRECTED: Changed from 'image' to 'photo'
            'status',
            'color',
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'price': forms.NumberInput(attrs={'step': '0.01'}),
            'cost': forms.NumberInput(attrs={'step': '0.01'}), # Added widget for cost
            'quantity': forms.NumberInput(attrs={'min': '0'}),
        }
        labels = {
            'name': 'Product Name',
            'item_code': 'Item Code (Unique)',
            'category': 'Category',
            'size': 'Available Sizes', # CORRECTED: Changed from 'sizes' to 'size'
            'description': 'Description',
            'price': 'Selling Price (EGP)',
            'cost': 'Cost Price (EGP)', # Added label for cost
            'quantity': 'Current Stock Quantity',
            'photo': 'Product Image', # CORRECTED: Changed from 'image' to 'photo'
            'status': 'Status',
        }

    # Optional: Add clean methods for custom validation if needed
    def clean_item_code(self):
        item_code = self.cleaned_data['item_code']
        # Ensure item_code is unique across all products
        if self.instance and self.instance.item_code == item_code: 
            return item_code
        if Product.objects.filter(item_code=item_code).exists():
            raise forms.ValidationError("This item code already exists. Please choose a unique one.")
        return item_code
        

class InvoiceForm(forms.ModelForm):
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
            'amount_paid'
        ]
        widgets = {
            'invoice_date': forms.DateInput(attrs={'type': 'date'}),
            'due_date': forms.DateInput(attrs={'type': 'date'}), 
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.initial.setdefault('company_address', "FPI, Damietta Furniture Point Mall")
        self.initial.setdefault('company_phone', "01065881729 - 01126905990 - 01110001559")
    


class InvoiceItemForm(forms.ModelForm):
    class Meta:
        model = InvoiceItem
        fields = ['product', 'product_name', 'quantity', 'unit_price']
        widgets = {
            'unit_price': forms.NumberInput(attrs={'step': '0.01'}),
            'quantity': forms.NumberInput(attrs={'min': '1'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ensure product list is filtered and displayed
        self.fields['product'].queryset = Product.objects.filter(status='available').order_by('name')
        self.fields['product'].required = False  # Let the user skip selecting a product
        self.fields['product_name'].required = False  # Also make this optional initially

    def clean(self):
        cleaned_data = super().clean()
        product = cleaned_data.get("product")
        product_name = cleaned_data.get("product_name")
        unit_price = cleaned_data.get("unit_price")

        if not product and not product_name:
            raise forms.ValidationError("You must select a product or enter a product name.")

        if product:
            # Use the product's name and price if not already filled
            if not product_name:
                cleaned_data['product_name'] = product.name
            if not unit_price:
                cleaned_data['unit_price'] = product.price

        if not unit_price or unit_price <= 0:
            raise forms.ValidationError("Unit price must be greater than zero.")

        return cleaned_data
    
    

