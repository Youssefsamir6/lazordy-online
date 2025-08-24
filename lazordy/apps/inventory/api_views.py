from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Q
from .models import Product
from .serializers import ProductSerializer


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def product_autocomplete(request):
    query = request.GET.get('q', '').strip()
    qs = Product.objects.all()
    if query:
        qs = qs.filter(Q(name__icontains=query) | Q(item_code__icontains=query))
    qs = qs.order_by('name')[:20]
    data = [
        {
            "id": str(p.id),
            "name": p.name,
            "item_code": p.item_code,
            "price": str(p.price),
            "quantity": p.quantity,
        }
        for p in qs
    ]
    return Response(data)