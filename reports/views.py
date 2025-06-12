# D:\lazordy\lazordy\reports\views.py

from django.shortcuts import render
# from inventory.models import Product # You'll uncomment and use this later if needed

def low_stock_report(request):
    # Placeholder data for now
    low_stock_items = [
        {'name': 'Product A', 'current_stock': 5, 'min_stock': 10},
        {'name': 'Product B', 'current_stock': 8, 'min_stock': 15},
    ]
    context = {
        'low_stock_items': low_stock_items,
        'title': 'Low Stock Items Report'
    }
    return render(request, 'reports/low_stock_report.html', context)