# D:\lazordy\lazordy\reports\urls.py

from django.urls import path
from . import views

app_name = 'reports' # Define the app namespace

urlpatterns = [
    path('low-stock/', views.low_stock_report, name='low_stock_report'),
    # Add other report URLs here as you create them
]
