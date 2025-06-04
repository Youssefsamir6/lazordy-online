# D:\lazordy\lazordy\inventory\views.py

from django.http import JsonResponse, HttpResponse # Combined imports
from django.template.loader import render_to_string
from weasyprint import HTML, CSS
from django.conf import settings
import os
from django.shortcuts import render, get_object_or_404
from django.db.models import Q # Import Q object for complex lookups
from django.utils import timezone # Ensure timezone is imported for invoice_pdf_view

from .models import Product, Category, Size, Invoice, InvoiceItem 

def get_product_price_view(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    # CORRECTED: Return product name along with price for admin JS
    return JsonResponse({'price': str(product.price), 'name': product.name})

def product_list(request):
    # Start with all available products
    products = Product.objects.filter(status='available')

    # --- Filtering Logic ---
    selected_category_id = request.GET.get('category')
    selected_size_id = request.GET.get('size')
    search_query = request.GET.get('q') # 'q' is a common parameter for search queries

    if selected_category_id:
        try:
            category = Category.objects.get(pk=selected_category_id)
            products = products.filter(category=category)
        except Category.DoesNotExist:
            pass # Ignore invalid category IDs

    if selected_size_id:
        try:
            # Filter products that have the selected size in their many-to-many relationship
            size = Size.objects.get(pk=selected_size_id)
            products = products.filter(size=size)
        except Size.DoesNotExist:
            pass # Ignore invalid size IDs

    if search_query:
        # Use Q objects for OR conditions to search across multiple fields
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(item_code__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(color__icontains=search_query) # Search by color too
        )

    # Order the results
    products = products.order_by('name')

    # Fetch all categories and sizes for the filter dropdowns (even after filtering)
    categories = Category.objects.all().order_by('name')
    sizes = Size.objects.all().order_by('name')

    context = {
        'products': products,
        'categories': categories,
        'sizes': sizes,
        'selected_category_id': selected_category_id, # Pass back to pre-select dropdown
        'selected_size_id': selected_size_id,         # Pass back to pre-select dropdown
        'search_query': search_query,                  # Pass back to pre-fill search input
        'page_title': 'Our Products'
    }
    return render(request, 'inventory/product_list.html', context)

def product_detail(request, item_code): # Changed pk to item_code to match URL and product model
    # Fetch a single product by its unique item_code (as discussed for URLs)
    product = get_object_or_404(Product, item_code=item_code)
    context = {
        'product': product,
        'page_title': product.name # Use product name as page title
    }
    return render(request, 'inventory/product_detail.html', context)

# CONSOLIDATED PDF VIEW
def generate_invoice_pdf(request, invoice_id): # Using invoice_id to match URL pattern
    invoice = get_object_or_404(Invoice, pk=invoice_id)
    invoice_items = InvoiceItem.objects.filter(invoice=invoice) # Or invoice.invoiceitem_set.all()

    
    context = {
        'invoice': invoice,
        'invoice_items': invoice_items,
        'company_name': 'Lazordy', 
        'company_address': 'f90 park mall  -  fpi, damietta furniture mall', # Consistent with previous instructions
        'company_phone': '01110001559', # Your company phone
        'company_email': 'info@lazordy.com', # Your company email
        'current_date': timezone.now().strftime('%Y-%m-%d'), # For the PDF creation date
        'invoice_maker': invoice.last_modified_by.get_full_name() if invoice.last_modified_by and invoice.last_modified_by.get_full_name() else \
                         invoice.last_modified_by.username if invoice.last_modified_by else 'N/A',
    }

   
    html_string = render_to_string('inventory/invoice_template.html', context)

 
    pdf_file = HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf()

    response = HttpResponse(pdf_file, content_type='application/pdf')

    response['Content-Disposition'] = f'attachment; filename="invoice_{invoice.invoice_number}.pdf"'
    return response