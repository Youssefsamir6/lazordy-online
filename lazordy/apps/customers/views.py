from django.shortcuts import render, get_object_or_404
from .models import Customer


def customer_list(request):
    customers = Customer.objects.all().order_by('name')
    return render(request, 'customers/customer_list.html', {"customers": customers})


def customer_detail(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    return render(request, 'customers/customer_detail.html', {"customer": customer})
