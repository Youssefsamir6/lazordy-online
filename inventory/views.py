# In D:\lazordy\lazordy\inventory\views.py

from django.http import JsonResponse, HttpResponse
from django.template.loader import render_to_string
from weasyprint import HTML, CSS
from django.conf import settings
import os
from django.shortcuts import render, get_object_or_404
from django.db.models import Q, Sum, Count, F, ExpressionWrapper, DecimalField
from django.db.models.functions import TruncMonth
from django.utils import timezone
from datetime import timedelta

from .models import Product, Category, Size, Invoice, InvoiceItem

# --- Your existing views ---

def get_product_price_view(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    return JsonResponse({'price': str(product.price), 'name': product.name})

def product_list(request):
    products = Product.objects.filter(status='available')
    selected_category_id = request.GET.get('category')
    selected_size_id = request.GET.get('size')
    search_query = request.GET.get('q')

    if selected_category_id:
        try:
            category = Category.objects.get(pk=selected_category_id)
            products = products.filter(category=category)
        except Category.DoesNotExist:
            pass

    if selected_size_id:
        try:
            size = Size.objects.get(pk=selected_size_id)
            products = products.filter(size=size)
        except Size.DoesNotExist:
            pass

    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(item_code__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(color__icontains=search_query)
        )

    products = products.order_by('name')

    categories = Category.objects.all().order_by('name')
    sizes = Size.objects.all().order_by('name')

    context = {
        'products': products,
        'categories': categories,
        'sizes': sizes,
        'selected_category_id': selected_category_id,
        'selected_size_id': selected_size_id,
        'search_query': search_query,
        'page_title': 'Our Products'
    }
    return render(request, 'inventory/product_list.html', context)

def product_detail(request, item_code):
    product = get_object_or_404(Product, item_code=item_code)
    context = {
        'product': product,
        'page_title': product.name
    }
    return render(request, 'inventory/product_detail.html', context)

def generate_invoice_pdf(request, invoice_id):
    invoice = get_object_or_404(Invoice, pk=invoice_id)
    invoice_items = InvoiceItem.objects.filter(invoice=invoice)

    context = {
        'invoice': invoice,
        'invoice_items': invoice_items,
        'company_name': 'Lazordy',
        'company_address': 'f90 park mall - fpi, damietta furniture mall',
        'company_phone': '01110001559',
        'company_email': 'info@lazordy.com',
        'current_date': timezone.now().strftime('%Y-%m-%d'),
        'invoice_maker': invoice.last_modified_by.get_full_name() if invoice.last_modified_by and invoice.last_modified_by.get_full_name() else \
                             invoice.last_modified_by.username if invoice.last_modified_by else 'N/A',
    }

    html_string = render_to_string('inventory/invoice_template.html', context)

    pdf_file = HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf()

    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="invoice_{invoice.invoice_number}.pdf"'
    return response

# --- ADD THIS NEW DASHBOARD VIEW FUNCTION ---
def dashboard_view(request):
    """
    Renders the main dashboard page with various inventory and sales metrics.
    """
    context = {}

    # 1. Total Products
    context['total_products'] = Product.objects.count()

    # 2. Total Value (Estimated based on current stock)
    total_value_aggregate = Product.objects.aggregate(
        total_val=Sum(ExpressionWrapper(F('price') * F('quantity'), output_field=DecimalField()))
    )
    context['total_value'] = total_value_aggregate['total_val'] if total_value_aggregate['total_val'] is not None else 0

    # 3. Low Stock Items (Define a low stock threshold, e.g., 10)
    LOW_STOCK_THRESHOLD = 3
    context['low_stock_items'] = Product.objects.filter(quantity__lte=LOW_STOCK_THRESHOLD).order_by('quantity')
    context['low_stock_threshold'] = LOW_STOCK_THRESHOLD

    # 4. Monthly Sales (e.g., last 6 months)
    monthly_sales_data = Invoice.objects.annotate(
        month=TruncMonth('invoice_date') # Corrected: 'date' to 'invoice_date'
    ).values('month').annotate(
        total_sales=Sum('total_amount')
    ).order_by('month')

    context['monthly_sales'] = [
        {'month': sale['month'].strftime('%Y-%m'), 'total_sales': sale['total_sales']}
        for sale in monthly_sales_data
    ]

    # 5. Sales Overview (e.g., Total Sales, Number of Invoices, Average Invoice Value)
    total_invoices = Invoice.objects.count()
    total_sales_amount = Invoice.objects.aggregate(total=Sum('total_amount'))['total']
    average_invoice_value = Invoice.objects.aggregate(avg=Sum('total_amount') / Count('id'))['avg']

    context['sales_overview'] = {
        'total_invoices': total_invoices,
        'total_sales_amount': total_sales_amount if total_sales_amount is not None else 0,
        'average_invoice_value': average_invoice_value if average_invoice_value is not None else 0,
    }

    # 6. Product Movement (e.g., Top 5 most sold products in the last 30 days)
    end_date = timezone.now()
    start_date = end_date - timedelta(days=30)

    top_selling_products = InvoiceItem.objects.filter(
        invoice__invoice_date__range=[start_date, end_date] # Corrected: 'invoice__date' to 'invoice__invoice_date'
    ).values(
        'product__name'
    ).annotate(
        total_quantity_sold=Sum('quantity')
    ).order_by('-total_quantity_sold')[:5]

    context['product_movement'] = list(top_selling_products)
    context['product_movement_timeframe'] = 'last 30 days'

    return render(request, 'inventory/dashboard.html', context)