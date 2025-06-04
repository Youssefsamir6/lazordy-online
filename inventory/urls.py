# D:\lazordy\lazordy\inventory\urls.py

from django.urls import path
from . import views # Import your regular views

app_name = 'inventory' # Keep this app_name for the regular views

urlpatterns = [
    # --- Non-API Views (Only these should remain here) ---
    path('', views.product_list, name='product_list_root'), # Mapped as the root of the /inventory/ prefix
    path('products/', views.product_list, name='product_list'),
    path('products/<str:item_code>/', views.product_detail, name='product_detail'), # Using item_code
    path('invoice/<int:invoice_id>/pdf/', views.generate_invoice_pdf, name='invoice_pdf'),
    path('get_product_price/<int:pk>/', views.get_product_price_view, name='get_product_price_view'),
]