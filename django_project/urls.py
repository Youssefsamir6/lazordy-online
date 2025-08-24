from django.contrib import admin
from django.conf.urls.i18n import i18n_patterns
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView 
from django.contrib.auth import views as auth_views
from inventory import views
from django.views.i18n import set_language

# ✅ Non-i18n URLS
urlpatterns = [
    path('set-language/', set_language, name='set_language'),  # Moved OUT of i18n_patterns
]

# ✅ i18n-aware URLs
urlpatterns += i18n_patterns(
    path('grappelli/', include('grappelli.urls')),  # Added grappelli URLs
    path('admin/', admin.site.urls),
    path('rosetta/', include('rosetta.urls')),
    path('reports/', include('reports.urls')),
    path('inventory/', include('inventory.urls', namespace='inventory')),
    path('', RedirectView.as_view(url='/inventory/', permanent=True)),
    path('accounts/password_change/', auth_views.PasswordChangeView.as_view(template_name='registration/password_change_form.html'), name='password_change'),
    path('accounts/password_change/done/', auth_views.PasswordChangeDoneView.as_view(template_name='registration/password_change_done.html'), name='password_change_done'),
    path('accounts/', include('django.contrib.auth.urls')),
    path('invoice/<int:invoice_id>/pdf/', views.generate_invoice_pdf, name='invoice_pdf'),
)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
