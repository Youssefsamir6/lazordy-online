# D:\lazordy\lazordy\django_project\urls.py

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# Import the product_list view directly to map it to the root
from inventory.views import product_list

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', product_list, name='home'), # Your traditional Django homepage

    # Include regular inventory views under /inventory/
    path('inventory/', include('inventory.urls')),

    # Include API views under /api/
    path('api/', include('inventory.api_urls', namespace='api_inventory')), # THIS IS THE CORRECTED LINE
]

# Serve media and static files in development (make sure STATIC_ROOT is defined in settings.py)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)