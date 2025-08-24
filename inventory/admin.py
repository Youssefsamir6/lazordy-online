from django.contrib import messages
from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.shortcuts import redirect
from .models import Product, Category, Size, Invoice, InvoiceItem, Dashboard
from decimal import Decimal
from django.utils.translation import gettext_lazy as _
from django.contrib.admin import DateFieldListFilter
from .forms import InvoiceItemForm
from django import forms
from django.contrib.auth.admin import UserAdmin

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'item_code', 'price', 'cost', 'quantity', 'category', 'status',
        'color', 'measurements', 'photo_display',
    )
    list_filter = ('category', 'status', 'color', 'size')
    search_fields = (
        'name__icontains', 'item_code__iexact', 'description__icontains',
        'color__icontains', 'measurements__icontains',
    )
    filter_horizontal = ('size',)

    def photo_display(self, obj):
        if obj.photo:
            return format_html('<img src="{}" width="50" height="50" style="object-fit: contain;" />', obj.photo.url)
        return _("No Image")
    photo_display.short_description = _("Photo")

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)

@admin.register(Size)
class SizeAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    form = InvoiceItemForm
    extra = 1
    autocomplete_fields = ['product',]
    readonly_fields = ( 'subtotal',)
    fields = ('product', 'product_name', 'quantity', 'unit_price', 'subtotal',)
    
    class Media:
        js = (
            'admin/js/vendor/jquery/jquery.min.js',
            'admin/js/jquery.init.js',
            'lazordy_theme/js/invoice_item_price_fill.js',
            'lazordy_theme/js/admin_invoiceitem_autofill.js'
        )

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        form = formset.form
        form.base_fields['product_name'].widget.attrs['style'] = 'width: 250px;'
        form.base_fields['unit_price'].widget.attrs['style'] = 'width: 100px;'
        return formset

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = (
        'invoice_number', 'customer_name', 'invoice_date', 'total_amount',
        'amount_paid', 'amount_remaining', 'status',
        'view_pdf_link', 'created_at', 'updated_at',
        'created_by_display', 'last_modified_by_display','status_colored'
    )
    list_filter = ('status', ('invoice_date', DateFieldListFilter), 'created_at', 'created_by', 'last_modified_by')
    ordering = ('-invoice_date', 'invoice_number')
    search_fields = ('invoice_number', 'customer_name', 'customer_phone')
    inlines = [InvoiceItemInline]
    save_on_top = True

    fieldsets = (
        (None, {
            'fields': (('customer_name', 'customer_phone'), 'home_address', 'company_address', 'company_phone', ('invoice_date', 'status')),
        }),
        (_('General Discount'), {
            'fields': ('discount_amount',),
            'description': _('General discount applied to the invoice.'),
        }),
        (_('Special Discount from Manager'), {
            'fields': ('manager_discount_amount', 'manager_discount_reason'),
            'description': _('Apply a special discount by a manager if needed.'),
        }),
        (_('Payment Details'), {
            'fields': ('amount_paid', 'amount_remaining', 'payment_method'),
            'description': _("Enter amount paid if invoice is uncompleted or paid. Amount remaining is calculated."),
        }),
        (_('Invoice Totals'), {
            'fields': ('invoice_number', 'subtotal_amount', 'total_amount'),
            'description': _("These fields are automatically generated."),
        }),
        (_('Additional Information'), {
            'fields': ('notes', 'terms_and_conditions', 'show_product_photos'),
            'description': _('Any additional notes or terms for the invoice.'),
        }),
        (_('Timestamps and Audit'), {
            'fields': ('created_at', 'updated_at', 'created_by', 'last_modified_by', 'due_date'),
        }),
    )

    readonly_fields = (
        'invoice_number',
        'subtotal_amount',
        'total_amount',
        'amount_remaining',
        'created_at',
        'updated_at',
        'invoice_date',
        'last_modified_by',
    )

    autocomplete_fields = ['created_by', 'last_modified_by']

    class Media:
        js = ()
        css = {
            'all': ('lazordy_theme/css/admin_dark_mode_fix.css',)
        }

    def view_pdf_link(self, obj):
        if obj.pk:
            url = reverse('inventory:invoice_pdf', args=[obj.pk])
            return format_html('<a class="button" href="{}" target="_blank">{}</a>', url, _("View PDF"))
        return "-"
    view_pdf_link.short_description = _('PDF')

    def created_by_display(self, obj):
        return obj.created_by.username if obj.created_by else _('N/A')
    created_by_display.short_description = _('Created By')

    def last_modified_by_display(self, obj):
        return obj.last_modified_by.username if obj.last_modified_by else _('N/A')
    last_modified_by_display.short_description = _('Last Modified By')

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        obj.last_modified_by = request.user
        super().save_model(request, obj, form, change)

    def save_formset(self, request, form, formset, change):
        try:
            instances = formset.save(commit=False)
            for obj in instances:
                obj.save(deduct_stock=True)
            formset.save_m2m()

            invoice = form.instance
            invoice.save()
            messages.success(request, _("Invoice items and product stock updated successfully."))
        except Exception as e:
            messages.error(request, _(f"Failed to update invoice items: {str(e)}"))

    def status_colored(self, obj):
        if obj.amount_remaining > 0:
            return format_html('<span style="color: red; font-weight: bold;">{}</span>', _("Unpaid"))
        else:
            return format_html('<span style="color: green; font-weight: bold;">{}</span>', _("Paid"))

    status_colored.short_description = _('Status')

@admin.register(Dashboard)
class DashboardAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return True

    def has_delete_permission(self, request, obj=None):
        return False

    def get_model_perms(self, request):
        return {
            'add': self.has_add_permission(request),
            'change': self.has_change_permission(request),
            'delete': self.has_delete_permission(request),
            'view': self.has_view_permission(request),
        }

    def changelist_view(self, request, extra_context=None):
        dashboard_url = reverse('inventory:dashboard')
        return redirect(dashboard_url)