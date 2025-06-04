from django.urls import path
from rest_framework.urlpatterns import format_suffix_patterns
from . import api_views

urlpatterns = [
    path('', api_views.api_root, name='api-root'),  # using a simple function instead of APIRootView

    # Example endpoints
    path('products/', api_views.ProductList.as_view(), name='product-list'),
    path('products/<int:pk>/', api_views.ProductDetail.as_view(), name='product-detail'),

    path('categories/', api_views.CategoryList.as_view(), name='category-list'),
    path('categories/<int:pk>/', api_views.CategoryDetail.as_view(), name='category-detail'),
]

urlpatterns = format_suffix_patterns(urlpatterns)
