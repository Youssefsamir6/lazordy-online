# D:\lazordy\lazordy\inventory\views.py
from django.http import HttpResponse, HttpResponseForbidden, HttpResponseNotFound, JsonResponse, Http404 # Http404 added here
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
from datetime import timedelta
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db import transaction
from django.contrib import messages
from .models import Product, Category, Size, Invoice, InvoiceItem
from .forms import ProductForm, InvoiceForm
from django.contrib.auth.decorators import permission_required
import logging
import base64
from django.utils.translation import gettext as _
from .cloud_upload import upload_invoice_to_cloud
import tempfile
from django.utils import translation
from django.utils.translation import gettext_lazy as _
from django.urls import translate_url
import requests


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
        'page_title': _('Our Products') # Wrapped for translation
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
        'page_title': product.name # product.name comes from DB, doesn't need _() here.
    }
    return render(request, 'inventory/product_detail.html', context)

@login_required
def get_product_name(request, product_id):
    try:
        product = Product.objects.get(pk=product_id)
        return JsonResponse({'name': product.name})
    except Product.DoesNotExist:
        return JsonResponse({'error': _('Product not found')}, status=404) # Wrapped for translation

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
        'page_title': _('Add New Product'), # Wrapped for translation
        'is_edit': False
    }
    return render(request, 'inventory/product_form.html', context)
    
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
                'text': _(f"{product.name} ({product.item_code})"), # Wrapped f-string for translation
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
        'page_title': _(f'Update {product.name}'), # Wrapped f-string for translation
        'product': product,
        'is_edit': True
    }
    return render(request, 'inventory/product_form.html', context)
    
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
        'page_title': _(f'Delete {product.name}') # Wrapped f-string for translation
    }
    return render(request, 'inventory/product_confirm_delete.html', context)
    
@login_required
def invoice_list(request):
    """
    Displays a list of all invoices.
    """
    invoices = Invoice.objects.all().order_by('-invoice_date')
    context = {
        'invoices': invoices,
        'page_title': _('All Invoices') # Wrapped for translation
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
                invoice.show_product_photos = form.cleaned_data.get('show_product_photos', False) 
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
                                error_msg = _(f"Insufficient stock for product '{product.name}'. Available: {product.quantity}, Requested: {quantity_sold}") # Wrapped f-string
                                form.add_error(None, error_msg)
                                raise ValueError(_("Insufficient stock")) # Wrapped for translation
                        except (ValueError, Product.DoesNotExist) as e:
                            # Catch specific errors and add to form, then re-raise to rollback
                            if not form.errors: # Avoid adding duplicate errors if already present
                                error_msg = _(f"Error processing item: {e}") # Wrapped f-string
                                form.add_error(None, error_msg)
                            raise # Re-raise to ensure transaction rollback
                # --- END NEW LOGIC ---

                # Recalculate invoice totals after all items are potentially added and saved.
                # Ensure your Invoice model has a 'calculate_totals' method.
                invoice.calculate_totals()
                invoice.save() # Save invoice again to persist updated totals

                messages.success(request, _(f"Invoice #{invoice.invoice_number} created successfully.")) # Wrapped f-string
                return redirect('inventory:invoice_detail', pk=invoice.pk)

        else:
            # If form is not valid (e.g., validation errors on Invoice fields)
            messages.error(request, _("There was an error creating the invoice. Please review and try again.")) # Wrapped for translation

    else:
        form = InvoiceForm()

    context = {
        'form': form,
        'page_title': _('Create New Invoice'), # Wrapped for translation
        'is_edit': False
    }
    return render(request, 'inventory/invoice_form.html', context)
    
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
        'page_title': _(f'Invoice #{invoice.invoice_number}') # Wrapped f-string for translation
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
        'page_title': _(f'Confirm Delete Invoice #{invoice.invoice_number}') # Wrapped f-string for translation
    }
    return render(request, 'inventory/invoice_confirm_delete.html', context)


def get_base64_image(static_relative_path):
    """Reads an image file from static and encodes it in base64 for inline embedding."""
    # Assuming static files are directly under BASE_DIR/static for this helper
    static_full_path = os.path.join(settings.BASE_DIR, 'static', static_relative_path)
    try:
        with open(static_full_path, 'rb') as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except FileNotFoundError:
        logger.warning(f"Static image not found at {static_full_path}.")
        return ''


@login_required
def generate_invoice_pdf(request, invoice_id):
    invoice = get_object_or_404(Invoice, pk=invoice_id)
    invoice_items = InvoiceItem.objects.filter(invoice=invoice)

    # Recalculate totals before generating PDF to ensure accuracy
    invoice.calculate_totals()
    invoice.save(update_fields=['subtotal_amount', 'total_amount', 'amount_paid', 'amount_remaining', 'status'])

    # Encode product photos as base64 for each invoice item if show_product_photos is True
    if invoice.show_product_photos:
        for item in invoice_items:
            if item.product and item.product.photo:
                try:
                    with open(item.product.photo.path, "rb") as image_file:
                        item.product.photo_base64 = base64.b64encode(image_file.read()).decode('utf-8')
                except Exception as e:
                    logger.warning(f"Failed to encode product photo for product {item.product.id}: {e}")
                    item.product.photo_base64 = None
            else:
                item.product.photo_base64 = None

    # 🔁 Language selection logic
    lang = request.GET.get("lang")
    if not lang:
        lang = translation.get_language() # Get the currently active language from Django

    temp_pdf_path = None # Initialize for finally block

    try:
        logger.info(f"Starting PDF generation for invoice {invoice_id} with language {lang}")
        # Activate the language for rendering the template
        # This is crucial for {% trans %} tags and for context processors like LANGUAGE_CODE
        with translation.override(lang):
            # --- Resources loading (inside translation.override to ensure translatable strings are correct) ---

            # Construct full static file paths dynamically
            # Using get_base64_image helper for consistency and error handling
            watermark_base64 = get_base64_image('lazordy_theme/images/background_logo_.png')
            logo_base64 = get_base64_image('lazordy_theme/images/primary_logo.png')
            
            # Initial placeholder QR code (before upload)
            # This links to the invoice detail page, a sensible fallback if upload fails
            placeholder_url = request.build_absolute_uri(reverse('inventory:invoice_detail', args=[invoice.pk]))
            qr = qrcode.make(placeholder_url)
            buffer = BytesIO()
            qr.save(buffer, format='PNG')
            initial_qr_code_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

            # Context for the invoice template
            context = {
                'invoice': invoice,
                'invoice_items': invoice_items,
                'company_name': _('Lazordy'),  # Wrapped for translation
                'company_address': _('FPI, Damietta Furniture Mall'),
                'company_phone': _('01110001559 - 01126905990 - 01065881729'),
                'company_email': _('lazordyegypt@gmail.com'),
                'current_date': timezone.now().strftime('%Y-%m-%d'),
                'invoice_maker': invoice.last_modified_by.get_full_name()
                                        if invoice.last_modified_by and invoice.last_modified_by.get_full_name()
                                        else invoice.last_modified_by.username if invoice.last_modified_by else _('N/A'),
                'watermark_base64': watermark_base64,
                'logo_base64': logo_base64,
                'qr_code_base64': initial_qr_code_base64, # Use initial QR here
                'request': request,
                'LANGUAGE_CODE': lang,
                'show_product_photos': invoice.show_product_photos,  # 🆕

            }

            # Step 1: Render HTML with placeholder QR and generate initial PDF bytes
            html_string_initial = render_to_string('inventory/invoice_template.html', context)
            pdf_bytes_initial = HTML(string=html_string_initial, base_url=request.build_absolute_uri('/')).write_pdf()
            logger.info(f"Initial PDF generated for invoice {invoice_id}, size: {len(pdf_bytes_initial)} bytes")

            # Save initial PDF to a temporary file for GoFile upload
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf_file:
                temp_pdf_file.write(pdf_bytes_initial)
                temp_pdf_path = temp_pdf_file.name
            logger.info(f"Temporary PDF saved at {temp_pdf_path}")

            # Step 2: Upload to Cloudinary
            uploaded_url = upload_invoice_to_cloud(temp_pdf_path, f"invoice_{invoice.invoice_number}_{lang}.pdf")
            logger.info(f"Uploaded PDF to Cloudinary, URL: {uploaded_url}")

            if uploaded_url:
                # Step 3: Update invoice with Cloudinary link
                invoice.cloud_pdf_url = uploaded_url
                invoice.generate_token()  # Make sure this method exists on your Invoice model
                invoice.save()
                logger.info(f"Invoice {invoice_id} updated with cloud PDF URL")

                # Step 4: Generate new QR with Google Drive link
                qr_real = qrcode.make(uploaded_url)
                qr_buffer = BytesIO()
                qr_real.save(qr_buffer, format='PNG')
                final_qr_code_base64 = base64.b64encode(qr_buffer.getvalue()).decode('utf-8')

                # Step 5: Re-render HTML with the final QR code
                context['qr_code_base64'] = final_qr_code_base64  # Update context with final QR
                final_html = render_to_string('inventory/invoice_template.html', context)
                final_pdf_bytes = HTML(string=final_html, base_url=request.build_absolute_uri('/')).write_pdf()
                logger.info(f"Final PDF generated for invoice {invoice_id}, size: {len(final_pdf_bytes)} bytes")

                # Return the final PDF to the user
                response = HttpResponse(final_pdf_bytes, content_type='application/pdf')
                filename = _(f"invoice_{invoice.invoice_number}_{lang}.pdf")
                response['Content-Disposition'] = f'attachment; filename="{filename}"'
                return response
            else:
                # If Google Drive upload failed, return the initial PDF without the cloud link
                logger.error(_(f"Google Drive upload failed for invoice {invoice.invoice_number}. Returning initial PDF."))
                response = HttpResponse(pdf_bytes_initial, content_type='application/pdf')
                filename = _(f"invoice_{invoice.invoice_number}_{lang}_(no_cloud).pdf")
                response['Content-Disposition'] = f'attachment; filename="{filename}"'
                return response

    except Exception as e:
        logger.exception(_("An error occurred during PDF generation or upload for invoice ID: %s"), invoice_id)
        # In case of any error, return a generic error message
        messages.error(request, _("An error occurred while generating or uploading the invoice PDF."))
        return HttpResponse(_("An error occurred while generating or uploading the invoice PDF."), status=500)
    finally:
        # Clean up the temporary PDF file if it was created
        if temp_pdf_path and os.path.exists(temp_pdf_path):
            os.remove(temp_pdf_path)

@login_required
def test_generate_invoice_pdf(request, invoice_id):
    """
    Test function to generate invoice PDF locally without uploading to Google Drive.
    Useful for diagnosing PDF generation issues.
    """
    invoice = get_object_or_404(Invoice, pk=invoice_id)
    invoice_items = InvoiceItem.objects.filter(invoice=invoice)

    # Encode product photos as base64 for each invoice item if show_product_photos is True
    if invoice.show_product_photos:
        for item in invoice_items:
            if item.product and item.product.photo:
                try:
                    with open(item.product.photo.path, "rb") as image_file:
                        item.product.photo_base64 = base64.b64encode(image_file.read()).decode('utf-8')
                except Exception as e:
                    logger.warning(f"Failed to encode product photo for product {item.product.id}: {e}")
                    item.product.photo_base64 = None
            else:
                item.product.photo_base64 = None

    lang = request.GET.get("lang")
    if not lang:
        lang = translation.get_language()

    try:
        with translation.override(lang):
            watermark_base64 = get_base64_image('lazordy_theme/images/background_logo_.png')
            logo_base64 = get_base64_image('lazordy_theme/images/primary_logo.png')

            placeholder_url = request.build_absolute_uri(reverse('inventory:invoice_detail', args=[invoice.pk]))
            qr = qrcode.make(placeholder_url)
            buffer = BytesIO()
            qr.save(buffer, format='PNG')
            qr_code_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

            context = {
                'invoice': invoice,
                'invoice_items': invoice_items,
                'company_name': _('Lazordy'),
                'company_address': _('FPI, Damietta Furniture Mall'),
                'company_phone': _('01110001559 - 01126905990 - 01065881729'),
                'company_email': _('lazordyegypt@gmail.com'),
                'current_date': timezone.now().strftime('%Y-%m-%d'),
                'invoice_maker': invoice.last_modified_by.get_full_name()
                                        if invoice.last_modified_by and invoice.last_modified_by.get_full_name()
                                        else invoice.last_modified_by.username if invoice.last_modified_by else _('N/A'),
                'watermark_base64': watermark_base64,
                'logo_base64': logo_base64,
                'qr_code_base64': qr_code_base64,
                'request': request,
                'LANGUAGE_CODE': lang,
                'show_product_photos': invoice.show_product_photos,
            }

            html_string = render_to_string('inventory/invoice_template.html', context)
            pdf_bytes = HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf()
            logger.info(f"Test PDF generated for invoice {invoice_id}, size: {len(pdf_bytes)} bytes")

            response = HttpResponse(pdf_bytes, content_type='application/pdf')
            filename = _(f"test_invoice_{invoice.invoice_number}_{lang}.pdf")
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response

    except Exception as e:
        logger.exception(f"Error generating test PDF for invoice {invoice_id}: {e}")
        messages.error(request, _("An error occurred while generating the test invoice PDF."))
        return HttpResponse(_("An error occurred while generating the test invoice PDF."), status=500)

# --- Dashboard View ---
@login_required
def dashboard_view(request):
    """
    Renders the main dashboard page with various inventory and sales metrics.
    Supports toggle between current and new dashboard via 'use_new_dashboard' GET parameter.
    """
    use_new_dashboard = request.GET.get('use_new_dashboard', '0') == '1'

    context = {}

    # 1. Total Products
    context['total_products_label'] = _("Total Products") # Added label for translation
    context['total_products'] = Product.objects.count()

    # 2. Total Value (Estimated based on current stock)
    total_value_aggregate = Product.objects.aggregate(
        total_val=Sum(ExpressionWrapper(F('price') * F('quantity'), output_field=DecimalField()))
    )
    context['total_value_label'] = _("Total Stock Value") # Added label for translation
    context['total_value'] = total_value_aggregate['total_val'] if total_value_aggregate['total_val'] is not None else 0

    # 3. Low Stock Items (Define a low stock threshold, e.g., 3)
    LOW_STOCK_THRESHOLD = 2
    context['low_stock_items_label'] = _("Low Stock Items") # Added label for translation
    context['low_stock_items'] = Product.objects.filter(quantity__lte=LOW_STOCK_THRESHOLD).order_by('quantity')
    context['low_stock_threshold'] = LOW_STOCK_THRESHOLD

    # 4. Monthly Sales (e.g., last 6 months)
    monthly_sales_data = Invoice.objects.annotate(
        month=TruncMonth('invoice_date')
    ).values('month').annotate(
        total_sales=Sum('total_amount')
    ).order_by('month')

    context['monthly_sales_label'] = _("Monthly Sales") # Added label for translation
    context['monthly_sales'] = [
        {'month': sale['month'].strftime('%Y-%m'), 'total_sales': sale['total_sales']}
        for sale in monthly_sales_data
    ]

    # 5. Sales Overview (e.g., Total Sales, Number of Invoices, Average Invoice Value)
    total_invoices = Invoice.objects.count()
    total_sales_amount = Invoice.objects.aggregate(total=Sum('total_amount'))['total']
    average_invoice_value = Invoice.objects.aggregate(avg=Sum('total_amount') / Count('id'))['avg']

    context['sales_overview_label'] = _("Sales Overview") # Added label for translation
    context['sales_overview'] = {
        'total_invoices_label': _("Total Invoices"), # Added label for translation
        'total_invoices': total_invoices,
        'total_sales_amount_label': _("Total Sales Amount"), # Added label for translation
        'total_sales_amount': total_sales_amount if total_sales_amount is not None else 0,
        'average_invoice_value_label': _("Average Invoice Value"), # Added label for translation
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

    context['product_movement_label'] = _("Product Movement") # Added label for translation
    context['product_movement'] = list(top_selling_products)
    context['product_movement_timeframe'] = _('last 30 days') # Wrapped for translation

    if use_new_dashboard:
        return render(request, 'inventory/dashboard_new.html', context)
    else:
        return render(request, 'inventory/dashboard.html', context)

def invoice_qr(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    if not invoice.cloud_pdf_url:
        return HttpResponse(_("Invoice not uploaded yet."), status=400) # Wrapped for translation
    
    qr = qrcode.make(invoice.cloud_pdf_url)
    response = HttpResponse(content_type="image/png")
    qr.save(response, "PNG")
    return response

# Helper function for generating PDF bytes for secure_invoice_pdf
def _generate_invoice_pdf_bytes(invoice, invoice_items, request, lang):
    """Helper function to generate PDF bytes given invoice and items, in a specific language."""
    with translation.override(lang):
        watermark_base64 = get_base64_image('lazordy_theme/images/background_logo_.png')
        logo_base64 = get_base64_image('lazordy_theme/images/primary_logo.png')

        # For _generate_invoice_pdf_bytes, we typically don't have the final cloud URL yet for the QR
        # So it might generate a QR to the invoice detail page or a generic placeholder.
        placeholder_url = request.build_absolute_uri(reverse('inventory:invoice_detail', args=[invoice.pk]))
        qr = qrcode.make(placeholder_url)
        buffer = BytesIO()
        qr.save(buffer, format='PNG')
        qr_code_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

        context = {
            'invoice': invoice,
            'invoice_items': invoice_items,
            'company_name': _('Lazordy'),
            'company_address': _('FPI, Damietta Furniture Mall'),
            'company_phone': _('01110001559 - 01126905990 - 01065881729'),
            'company_email': _('lazordyegypt@gmail.com'),
            'current_date': timezone.now().strftime('%Y-%m-%d'),
            'invoice_maker': invoice.last_modified_by.get_full_name()
                                    if invoice.last_modified_by and invoice.last_modified_by.get_full_name()
                                    else invoice.last_modified_by.username if invoice.last_modified_by else _('N/A'),
            'watermark_base64': watermark_base64,
            'logo_base64': logo_base64,
            'qr_code_base64': qr_code_base64,
            'request': request,
            'LANGUAGE_CODE': lang,
        }
        html_string = render_to_string('inventory/invoice_template.html', context)
        return HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf()


def secure_invoice_pdf(request, token):
    invoice = get_object_or_404(Invoice, access_token=token)
    if not invoice.is_token_valid():
        raise Http404(_("Expired"))

    # Determine language for the secure link (optional, defaults to current or English)
    lang = request.GET.get("lang", translation.get_language())
    
    # Generate the PDF file content
    invoice_items = InvoiceItem.objects.filter(invoice=invoice)
    pdf_bytes = _generate_invoice_pdf_bytes(invoice, invoice_items, request, lang) # Use the helper function

    temp_pdf_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            temp_file.write(pdf_bytes)
            temp_file_path = temp_file.name

        # Use Google Drive upload
        drive_uploader = GoogleDriveUploader()
        url = drive_uploader.upload_pdf(temp_file_path, f"secure_invoice_{invoice.invoice_number}.pdf")

        if url:
            # Save cloud URL in invoice
            invoice.cloud_pdf_url = url
            # invoice.generate_token() # Token already generated and validated, don't re-generate unless logic demands
            invoice.save()
            return redirect(url)
        else:
            logger.error(_("Failed to upload PDF for secure invoice %s."), invoice.pk)
            return HttpResponse(_("Could not generate secure PDF link."), status=500)

    except Exception as e:
        logger.exception(_("Error generating or uploading secure invoice PDF for token %s."), token)
        return HttpResponse(_("An error occurred while generating the secure invoice PDF."), status=500)
    finally:
        if temp_pdf_path and os.path.exists(temp_pdf_path):
            os.remove(temp_pdf_path)
    
def switch_language(request, lang_code):
    # Activate the selected language
    translation.activate(lang_code)
    request.session[translation.LANGUAGE_SESSION_KEY] = lang_code

    # Get the current URL (or fallback to home)
    current_url = request.META.get('HTTP_REFERER', '/')

    # Translate the URL to the selected language
    translated_url = translate_url(current_url, lang_code)

    return redirect(translated_url)

def autocomplete_products(request):
    if request.method == "GET":
        query = request.GET.get("q", "")
        products = Product.objects.filter(name__icontains=query, status="available").values("id", "name")
        return JsonResponse(list(products), safe=False)
    

def get_product_price(request, pk):
    try:
        product = Product.objects.get(pk=pk)
        return JsonResponse({
            "price": float(product.unit_price),
            "name": product.name  # <== Add this line
        })
    except Product.DoesNotExist:
        return JsonResponse({"error": "Product not found"}, status=404)