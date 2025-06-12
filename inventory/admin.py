# inventory/admin.py

from django.contrib import admin
from django.urls import reverse # Import reverse to get URL
from django.utils.html import format_html # Import format_html
from django.shortcuts import redirect # Import redirect for the DashboardAdmin
from .models import Product, Category, Size, Invoice, InvoiceItem, Dashboard # Import your new Dashboard model
from decimal import Decimal
from django.db.models import Sum

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'item_code', 'price', 'quantity', 'category', 'status',
        'color', 'measurements_cm', 'photo_display',
    )
    list_filter = (
        'category',
        'status',
        'color',
        'size',
    )
    search_fields = (
        'name__icontains',
        'item_code__iexact',
        'description__icontains',
        'color__icontains',
        'measurements_cm__icontains',
    )
    filter_horizontal = ('size',)

    def photo_display(self, obj):
        if obj.photo:
            return format_html('<img src="{}" width="50" height="50" style="object-fit: contain;" />', obj.photo.url)
        return "No Image"
    photo_display.short_description = "Photo"


# Admin for Category
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)

# Custom Admin for Size
@admin.register(Size)
class SizeAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
    filter_horizontal = ('products',) # Assuming related_name='products' in Size model for M2M with Product


# Inline for InvoiceItem to be used within Invoice admin
class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 1
    autocomplete_fields = ['product']
    readonly_fields = ('product_name', 'subtotal',)
    fields = ('product', 'product_name', 'quantity', 'unit_price', 'subtotal',)

    class Media:
        js = (
            'admin/js/vendor/jquery/jquery.min.js',
            'admin/js/jquery.init.js',
            'inventory/js/invoice_item_price_fill.js',
        )

# Custom admin for Invoice
@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = (
        'invoice_number', 'customer_name', 'invoice_date', 'total_amount',
        'amount_paid', 'amount_remaining', 'status',
        'view_pdf_link','created_at', 'updated_at',
        'created_by_display', 'last_modified_by_display'
    )
    list_filter = ('status', 'invoice_date', 'created_at', 'created_by', 'last_modified_by')
    search_fields = ('invoice_number', 'customer_name', 'customer_phone')
    inlines = [InvoiceItemInline]
    save_on_top = True

    fieldsets = (
        (None, {
            'fields': (('customer_name', 'customer_phone'), 'home_address', ('invoice_date', 'status'), 'discount_amount'),
        }),
        ('Payment Details', {
            'fields': ('amount_paid', 'amount_remaining'),
            'description': "Enter amount paid if invoice is uncompleted or paid. Amount remaining is calculated.",
            'classes': ('collapse',), # You might want this to be open by default, or collapse
        }),
        ('Invoice Totals', {
            'fields': ('invoice_number', 'total_amount'),
            'description': "These fields are automatically generated.",
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at',('created_by', 'last_modified_by')),
            'classes': ('collapse',),
        }),
    )

    readonly_fields = ('invoice_number', 'total_amount', 'amount_remaining', 'created_at', 'updated_at','created_by', 'last_modified_by')

    # Add JavaScript to show/hide fields based on status
    class Media:
        js = (
            'admin/js/vendor/jquery/jquery.min.js',
            'admin/js/jquery.init.js',
            'inventory/js/invoice_admin_status_logic.js',
        )
    # Custom method to display PDF link in list_display
    def view_pdf_link(self, obj):
        if obj.pk:
            url = reverse('inventory:invoice_pdf', args=[obj.pk])
            return format_html('<a class="button" href="{}" target="_blank">View PDF</a>', url)
        return "-"
    view_pdf_link.short_description = 'PDF'

    def created_by_display(self, obj):
        return obj.created_by.username if obj.created_by else 'N/A'
    created_by_display.short_description = 'Created By'

    def last_modified_by_display(self, obj):
        return obj.last_modified_by.username if obj.last_modified_by else 'N/A'
    last_modified_by_display.short_description = 'Last Modified By'


    def save_model(self, request, obj, form, change):
        if not obj.pk: # Only set created_by on initial creation
            obj.created_by = request.user
        obj.last_modified_by = request.user
        super().save_model(request, obj, form, change)

    def save_formset(self, request, form, formset, change):
        formset.save()
        invoice = form.instance
        if invoice.pk:
            invoice.save()

# Custom Admin for the Dashboard "model"
@admin.register(Dashboard)
class DashboardAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False # Hide the "Add" button for Dashboard

    def has_change_permission(self, request, obj=None):
        return True # Allow clicking the name to view (redirect to dashboard)

    def has_delete_permission(self, request, obj=None):
        return False # Hide the "Delete" button for Dashboard

    def get_model_perms(self, request):
        """
        Returns a dict of the perms for this model.
        We want 'view' perm to display it in the admin index.
        """
        return {
            'add': self.has_add_permission(request),
            'change': self.has_change_permission(request),
            'delete': self.has_delete_permission(request),
            'view': self.has_view_permission(request), # Ensure view permission is true
        }

    def changelist_view(self, request, extra_context=None):
        """
        Redirects to your actual dashboard view.
        """
        # Use reverse with the fully qualified URL name for your dashboard view
        dashboard_url = reverse('inventory:dashboard')
        return redirect(dashboard_url)