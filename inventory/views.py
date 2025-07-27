from django.http import HttpResponse, HttpResponseForbidden, HttpResponseNotFound, JsonResponse
from django.urls import reverse
import qrcode
from io import BytesIO
from django.template.loader import render_to_string
from weasyprint import HTML, CSS
from django.conf import settings
import os
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q, Sum, Count, F, ExpressionWrapper, DecimalField
from django.db.models.functions import TruncMonth
from django.utils import timezone
from django.utils.timezone import now
from datetime import timedelta
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db import transaction 
from django.contrib import messages
from .models import Product, Category, Size, Invoice, InvoiceItem
from .forms import ProductForm, InvoiceForm 
from django.contrib.auth.decorators import permission_required
import logging
import base64
from django.utils.translation import gettext as _  # Optional, if you want i18n
from .cloud_upload import upload_invoice_to_cloud
import tempfile
from django.shortcuts import redirect
from django.utils import translation
from django.utils.translation import gettext_lazy as _
from django.urls import translate_url



logger = logging.getLogger(__name__)

# --- API / Utility Views ---
@login_required
def get_product_price_view(request, product_id):
    """
    Returns the price and name of a product as a JSON response.
    Used for dynamically populating product details in forms.
    """
    product = get_object_or_404(Product, pk=product_id)
    return JsonResponse({'price': str(product.price), 'name': product.name})

@login_required
def product_list(request):
    """
    Displays a paginated list of products with filtering and sorting options.
    """
    products_list = Product.objects.filter(status='available')
    
    selected_category_id = request.GET.get('category')
    selected_size_id = request.GET.get('size')
    search_query = request.GET.get('q')
    sort_by = request.GET.get('sort', '') # Get sort parameter, default to empty string

    # Apply filters
    if selected_category_id:
        try:
            category = Category.objects.get(pk=selected_category_id)
            products_list = products_list.filter(category=category)
        except Category.DoesNotExist:
            pass

    if selected_size_id:
        try:
            size = Size.objects.get(pk=selected_size_id)
            products_list = products_list.filter(size=size) # Assuming 'size' is the ManyToMany field name
        except Size.DoesNotExist:
            pass

    if search_query:
        products_list = products_list.filter(
            Q(name__icontains=search_query) |
            Q(item_code__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    # Apply sorting
    if sort_by == 'name':
        products_list = products_list.order_by('name')
    elif sort_by == 'name_desc':
        products_list = products_list.order_by('-name')
    elif sort_by == 'price_asc':
        products_list = products_list.order_by('price')
    elif sort_by == 'price_desc':
        products_list = products_list.order_by('-price')
    else:
        products_list = products_list.order_by('name') # Default sort

    # Pagination
    paginator = Paginator(products_list, 12) # Show 12 products per page
    page_number = request.GET.get('page')
    try:
        products = paginator.page(page_number)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        products = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        products = paginator.page(paginator.num_pages)

    categories = Category.objects.all().order_by('name')
    sizes = Size.objects.all().order_by('name')

    context = {
        'products': products, # This is now the paginated object
        'categories': categories,
        'sizes': sizes,
        'selected_category_id': selected_category_id,
        'selected_size_id': selected_size_id,
        'search_query': search_query,
        'sort': sort_by, # Pass the sort parameter to the template
        'page_title': 'Our Products'
    }
    return render(request, 'inventory/product_list.html', context)

@login_required
def product_detail(request, item_code):
    """
    Displays the details of a single product.
    """
    product = get_object_or_404(Product, item_code=item_code)
    context = {
        'product': product,
        'page_title': product.name
    }
    return render(request, 'inventory/product_detail.html', context)

@login_required
def get_product_name(request, product_id):
    try:
        product = Product.objects.get(pk=product_id)
        return JsonResponse({'name': product.name})
    except Product.DoesNotExist:
        return JsonResponse({'error': 'Product not found'}, status=404)

@login_required
@permission_required('inventory.add_product', raise_exception=True)
def add_product(request):
    """
    Handles adding a new product to the inventory.
    """
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('inventory:product_list')
    else:
        form = ProductForm()
    context = {
        'form': form,
        'page_title': 'Add New Product',
        'is_edit': False
    }
    return render(request, 'inventory/product_form.html', context)
    pass
@login_required
def product_autocomplete(request):
    query = request.GET.get('q', '')
    results = []

    if query:
        products = Product.objects.filter(name__icontains=query)[:15]
        for product in products:
            results.append({
                'id': product.id,
                'name': product.name,
                'text': f"{product.name} ({product.item_code})",
                'price': str(product.price)
            })

    return JsonResponse({'results': results})

@login_required
@permission_required('inventory.add_product', raise_exception=True)
def update_product(request, pk):
    """
    Handles updating an existing product in the inventory.
    """
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            return redirect('inventory:product_list')
    else:
        form = ProductForm(instance=product)
    context = {
        'form': form,
        'page_title': f'Update {product.name}',
        'product': product,
        'is_edit': True
    }
    return render(request, 'inventory/product_form.html', context)
    pass
@login_required
@permission_required('inventory.add_product', raise_exception=True)
def delete_product(request, pk):
    """
    Handles deleting a product from the inventory after confirmation.
    """
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        product.delete()
        return redirect('inventory:product_list')
    context = {
        'product': product,
        'page_title': f'Delete {product.name}'
    }
    return render(request, 'inventory/product_confirm_delete.html', context)
    pass
@login_required
def invoice_list(request):
    """
    Displays a list of all invoices.
    """
    invoices = Invoice.objects.all().order_by('-invoice_date')
    context = {
        'invoices': invoices,
        'page_title': 'All Invoices'
    }
    return render(request, 'inventory/invoice_list.html', context)

@login_required
@permission_required('inventory.add_product', raise_exception=True)
def create_invoice(request):
    """
    Handles creating a new invoice and updating product quantities.
    """
    if request.method == 'POST':
        form = InvoiceForm(request.POST)
        if form.is_valid():
            # Use a transaction to ensure atomicity:
            # either all quantity updates succeed, or none do.
            with transaction.atomic():
                invoice = form.save(commit=False)
                # Set 'last_modified_by' to the current user (assuming user is authenticated)
                if request.user.is_authenticated:
                    invoice.last_modified_by = request.user
                invoice.save()

                # --- NEW LOGIC FOR INVOICE ITEMS AND STOCK DECREMENT ---
                # This section assumes your form sends product details like product_id_1, quantity_1, etc.
                # You MUST adapt this loop to how your actual form fields for invoice items are named.
                
                # A simple way to count items if they are named product_id_1, product_id_2, etc.
                item_prefix = 'product_id_'
                item_indices = sorted([int(k.split('_')[-1]) for k in request.POST if k.startswith(item_prefix)], reverse=True)
                
                if not item_indices:
                    # Handle case where no items are provided (e.g., add form error, or return a message)
                    # For now, we'll let it proceed, but the totals will be 0.
                    pass 

                for i in item_indices: # Iterate through item indices (e.g., 1, 2, 3...)
                    product_id_str = request.POST.get(f'product_id_{i}')
                    quantity_str = request.POST.get(f'quantity_{i}')
                    unit_price_str = request.POST.get(f'unit_price_{i}') # Assuming unit price is sent

                    if product_id_str and quantity_str and unit_price_str:
                        try:
                            product_id = int(product_id_str)
                            quantity_sold = int(quantity_str)
                            unit_price = float(unit_price_str)

                            # Lock product row to prevent race conditions during quantity update
                            product = Product.objects.select_for_update().get(pk=product_id) 

                            if product.quantity >= quantity_sold:
                                InvoiceItem(
                                invoice=invoice,
                                product=product,
                                product_name=product.name,
                                quantity=quantity_sold,
                                unit_price=unit_price
                            ).save(deduct_stock=True)
                            else:
                                # Insufficient stock - raise an error to rollback the transaction
                                form.add_error(None, f"Insufficient stock for product '{product.name}'. Available: {product.quantity}, Requested: {quantity_sold}")
                                raise ValueError("Insufficient stock") # This will trigger transaction rollback
                        except (ValueError, Product.DoesNotExist) as e:
                            # Catch specific errors and add to form, then re-raise to rollback
                            if not form.errors: # Avoid adding duplicate errors if already present
                                form.add_error(None, f"Error processing item: {e}")
                            raise # Re-raise to ensure transaction rollback
                # --- END NEW LOGIC ---

                # Recalculate invoice totals after all items are potentially added and saved.
                # Ensure your Invoice model has a 'calculate_totals' method.
                invoice.calculate_totals()
                invoice.save() # Save invoice again to persist updated totals

                messages.success(request, f"Invoice #{invoice.invoice_number} created successfully.")
                return redirect('inventory:invoice_detail', pk=invoice.pk)

        else:
            # If form is not valid (e.g., validation errors on Invoice fields)
            messages.error(request, "There was an error creating the invoice. Please review and try again.")

              # For debugging

    else:
        form = InvoiceForm()

    context = {
        'form': form,
        'page_title': 'Create New Invoice',
        'is_edit': False
    }
    return render(request, 'inventory/invoice_form.html', context)
    pass
@login_required
def invoice_detail(request, pk):
    """
    Displays a single invoice's details.
    """
    invoice = get_object_or_404(Invoice, pk=pk) # Fetch the actual invoice
    invoice_items = InvoiceItem.objects.filter(invoice=invoice) # Fetch related items

    context = {
        'invoice': invoice,
        'invoice_items': invoice_items,
        'page_title': f'Invoice #{invoice.invoice_number}' # Use actual invoice number
    }
    return render(request, 'inventory/invoice_detail.html', context)



@login_required
@permission_required('inventory.add_product', raise_exception=True)
def invoice_delete(request, pk):
    """
    Handles deleting a product from the inventory after confirmation.
    """
    invoice = get_object_or_404(Invoice, pk=pk) # Fetch the actual invoice
    if request.method == 'POST':
        invoice.delete()
        return redirect('inventory:invoice_list') # Redirect to the invoice list after deletion

    context = {
        'invoice': invoice,
        'page_title': f'Confirm Delete Invoice #{invoice.invoice_number}'
    }
    return render(request, 'inventory/invoice_confirm_delete.html', context)



def get_base64_image(static_relative_path):
    """Reads an image file from static and encodes it in base64 for inline embedding."""
    static_full_path = os.path.join(settings.BASE_DIR, 'inventory', 'static', static_relative_path)
    try:
        with open(static_full_path, 'rb') as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except FileNotFoundError:
        return ''


@login_required
def generate_invoice_pdf(request, invoice_id):
    invoice = get_object_or_404(Invoice, pk=invoice_id)
    invoice_items = InvoiceItem.objects.filter(invoice=invoice)

    # 🔁 Language selector from query params (defaults to English)
    lang = request.GET.get("lang", "en")

    # Load watermark and logo
    with open(os.path.join(settings.BASE_DIR, 'inventory/static/lazordy_theme/images/background_logo_.png'), 'rb') as img:
        watermark_base64 = base64.b64encode(img.read()).decode('utf-8')

    with open(os.path.join(settings.BASE_DIR, 'inventory/static/lazordy_theme/images/primary_logo.png'), 'rb') as logo:
        logo_base64 = base64.b64encode(logo.read()).decode('utf-8')

    # Temporary placeholder QR code
    placeholder_url = "https://lazordy.com/processing"
    qr = qrcode.make(placeholder_url)
    buffer = BytesIO()
    qr.save(buffer, format='PNG')
    qr_code_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

    # Shared context
    context = {
        'invoice': invoice,
        'invoice_items': invoice_items,
        'company_name': 'Lazordy',
        'company_address': invoice.company_address or 'fpi, damietta furniture mall',
        'company_phone': '01110001559 - 01126905990 - 01065881729',
        'company_email': 'lazordyegypt@gmail.com',
        'current_date': timezone.now().strftime('%Y-%m-%d'),
        'invoice_maker': invoice.last_modified_by.get_full_name()
                         if invoice.last_modified_by and invoice.last_modified_by.get_full_name()
                         else invoice.last_modified_by.username if invoice.last_modified_by else 'N/A',
        'watermark_base64': watermark_base64,
        'logo_base64': logo_base64,
        'qr_code_base64': qr_code_base64,
        'lang': lang,
        'request': request,
    }

    # Step 1: Render Initial PDF (placeholder QR)
    html_string = render_to_string('inventory/invoice_template.html', context)
    pdf_bytes = HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf()

    # Save temp PDF file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
        temp_pdf.write(pdf_bytes)
        temp_pdf_path = temp_pdf.name

    # Step 2: Upload to GoFile.io
    try:
        with open(temp_pdf_path, 'rb') as f:
            upload_response = requests.post(
                "https://store1.gofile.io/uploadFile",
                files={"file": f}
            )
        data = upload_response.json()

        if data.get("status") == "ok":
            final_url = data["data"]["downloadPage"]

            # Step 3: Update invoice with real link
            invoice.cloud_pdf_url = final_url
            invoice.generate_token()
            invoice.save()

            # Step 4: New QR with real link
            qr_real = qrcode.make(final_url)
            qr_buffer = BytesIO()
            qr_real.save(qr_buffer, format='PNG')
            qr_code_base64 = base64.b64encode(qr_buffer.getvalue()).decode('utf-8')

            # Step 5: Re-render with real QR
            context['qr_code_base64'] = qr_code_base64
            final_html = render_to_string('inventory/invoice_template.html', context)
            final_pdf = HTML(string=final_html, base_url=request.build_absolute_uri('/')).write_pdf()

            response = HttpResponse(final_pdf, content_type='application/pdf')
            filename = f"invoice_{invoice.invoice_number}_{lang}.pdf"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response

        else:
            raise Exception(f"Gofile upload failed: {data.get('message')}")

    except Exception as e:
        print("Upload or PDF generation error:", str(e))
        return HttpResponse("An error occurred while generating or uploading the invoice PDF.", status=500)
    finally:
        if os.path.exists(temp_pdf_path):
            os.remove(temp_pdf_path)

# --- Dashboard View ---
@login_required
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

    # 3. Low Stock Items (Define a low stock threshold, e.g., 3)
    LOW_STOCK_THRESHOLD = 2
    context['low_stock_items'] = Product.objects.filter(quantity__lte=LOW_STOCK_THRESHOLD).order_by('quantity')
    context['low_stock_threshold'] = LOW_STOCK_THRESHOLD

    # 4. Monthly Sales (e.g., last 6 months)
    monthly_sales_data = Invoice.objects.annotate(
        month=TruncMonth('invoice_date')
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
        invoice__invoice_date__range=[start_date, end_date]
    ).values(
        'product__name'
    ).annotate(
        total_quantity_sold=Sum('quantity')
    ).order_by('-total_quantity_sold')[:5]

    context['product_movement'] = list(top_selling_products)
    context['product_movement_timeframe'] = 'last 30 days'

    return render(request, 'inventory/dashboard.html', context)

def invoice_qr(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    if not invoice.cloud_pdf_url:
        return HttpResponse("Invoice not uploaded yet.", status=400)
    
    qr = qrcode.make(invoice.cloud_pdf_url)
    response = HttpResponse(content_type="image/png")
    qr.save(response, "PNG")
    return response




def secure_invoice_pdf(request, token):
    invoice = get_object_or_404(Invoice, access_token=token)
    if not invoice.is_token_valid():
        raise Http404("Expired")

    # Generate the PDF file temporarily
    file = generate_pdf(invoice)  # <- your custom logic
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
        temp_file.write(file.read())
        temp_file.flush()
        url = upload_invoice_to_cloud(temp_file.name, f"invoice_{invoice.pk}")
    
    # Save cloud URL in invoice
    invoice.cloud_pdf_url = url
    invoice.save()

    return redirect(url) 

def upload_to_gofile(pdf_path):
    try:
        url = "https://api.gofile.io/uploadFile"
        with open(pdf_path, 'rb') as f:
            files = {'file': f}
            response = requests.post(url, files=files)
        data = response.json()
        if data["status"] == "ok":
            return data["data"]["downloadPage"]
    except Exception as e:
        print("Upload failed:", e)
    return None

def switch_language(request, lang_code):
    # Activate the selected language
    translation.activate(lang_code)
    request.session[translation.LANGUAGE_SESSION_KEY] = lang_code

    # Get the current URL (or fallback to home)
    current_url = request.META.get('HTTP_REFERER', '/')

    # Translate the URL to the selected language
    translated_url = translate_url(current_url, lang_code)

    return redirect(translated_url)