from django.urls import path
from . import api_views

urlpatterns = [
    path('products/autocomplete/', api_views.product_autocomplete, name='product_autocomplete'),
]