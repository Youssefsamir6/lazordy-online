# D:\lazordy\lazordy\inventory\urls.py

from django.urls import path
from . import views # Import your regular views
from .views import switch_language
app_name = 'inventory' # Important for namespacing (e.g., {% url 'inventory:dashboard' %})

urlpatterns = [
    # Main Dashboard (often the root of the app, or the project root)
    path('', views.dashboard_view, name='dashboard'), # Maps /inventory/ to the dashboard

    # Product Management URLs
    path('products/', views.product_list, name='product_list'),
    path('products/add/', views.add_product, name='add_product'), 
    path('products/update/<int:pk>/', views.update_product, name='update_product'), 
    path('products/delete/<int:pk>/', views.delete_product, name='delete_product'), 
    path('products/<str:item_code>/', views.product_detail, name='product_detail'), 

    # Invoice and Product Price API URLs
    path('api/product/<int:product_id>/price/', views.get_product_price_view, name='get_product_price'),
    path('api/product/<int:product_id>/name/', views.get_product_name, name='product_name'),
    path('invoices/', views.invoice_list, name='invoice_list'), 
    path('invoices/create/', views.create_invoice, name='create_invoice'),
    path('invoice/<int:pk>/', views.invoice_detail, name='invoice_detail'),
    path('switch-language/<str:lang_code>/', switch_language, name='switch_language'),
    path('invoice/<int:pk>/delete/', views.invoice_delete, name='invoice_delete'),
    path('invoice/<int:invoice_id>/pdf/', views.generate_invoice_pdf, name='invoice_pdf'),  
    path('invoice/<int:invoice_id>/qr/', views.invoice_qr, name='invoice_qr'),
    path('api/products/autocomplete/', views.product_autocomplete, name='product_autocomplete'),
    path('get_product_price/<int:product_id>/', views.get_product_price_view, name='get_product_price'),
    #path('invoice/token/<str:token>/', views.invoice_pdf_token_view, name='invoice_pdf_token'),



    # Removed: path('admin/inventory/dashboard/', views.dashboard_view, name='admin_inventory_dashboard'),
    # This path is redundant if the custom dashboard is primary, and admin views are typically registered differently.
]