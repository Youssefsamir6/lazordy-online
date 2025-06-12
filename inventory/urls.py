from django.urls import path
from . import views # Import your regular views

app_name = 'inventory'

urlpatterns = [
    # Map the root of the inventory app's URLs (which is now the project root '/') to the dashboard
    path('', views.dashboard_view, name='dashboard'),

    # Keep the product list at /products/
    path('products/', views.product_list, name='product_list'),

    # The specific product detail page
    path('products/<str:item_code>/', views.product_detail, name='product_detail'),

    # Invoice and product price related URLs
    path('invoice/<int:invoice_id>/pdf/', views.generate_invoice_pdf, name='invoice_pdf'),
    path('get_product_price/<int:pk>/', views.get_product_price_view, name='get_product_price_view'),

    path('admin/inventory/dashboard/', views.dashboard_view, name='admin_inventory_dashboard'),
    # path('dashboard/', views.dashboard_view, name='dashboard'),
]