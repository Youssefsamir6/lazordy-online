from django.urls import path
from . import views

urlpatterns = [
    path('', views.invoice_list, name='invoice_list'),
    path('<uuid:pk>/', views.invoice_detail, name='invoice_detail'),
    path('share/<str:token>/', views.invoice_share, name='invoice_share'),
    path('<uuid:pk>/pdf/', views.invoice_pdf, name='invoice_pdf'),
]