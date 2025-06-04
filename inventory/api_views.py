# D:\lazordy\lazordy\inventory\api_views.py

from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from django.db.models import Sum, F, ExpressionWrapper, DecimalField
from django.db.models.functions import Coalesce
from django.utils import timezone
from .models import Category, Size, Product, Invoice, InvoiceItem
from .serializers import (
    CategorySerializer, SizeSerializer, ProductSerializer,
    InvoiceSerializer, InvoiceItemSerializer, UserSerializer
)
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group # Import Group for user roles

User = get_user_model()


# --- Authentication Views (Basic for now, will enhance with JWT) ---
class CurrentUserView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        # Add a 'role' field based on group membership or is_superuser
        user_data = serializer.data
        if request.user.is_superuser:
            user_data['role'] = 'admin'
        elif request.user.groups.filter(name='Staff').exists(): # Assuming a 'Staff' group
            user_data['role'] = 'staff'
        else:
            user_data['role'] = 'user' # Default role
        return Response(user_data)


# --- User Management Views ---
class UserListCreateAPIView(generics.ListCreateAPIView):
    queryset = User.objects.all().order_by('username')
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAdminUser] # Only admins can list/create users

    def perform_create(self, serializer):
        # When creating a new user, password should be hashed
        user = serializer.save()
        user.set_password(self.request.data.get('password'))
        user.save()
        # Assign roles based on incoming data if needed, e.g., if 'role' is in request.data
        # For simplicity, default to staff for new users if not specified, or you can require a 'role' field in serializer
        # if self.request.data.get('role') == 'admin':
        #     user.is_staff = True
        #     user.is_superuser = True
        # elif self.request.data.get('role') == 'staff':
        #     user.is_staff = True
        # user.save()

class UserRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAdminUser] # Only admins can modify/delete users
    lookup_field = 'pk' # Or 'username' if you prefer fetching by username


# --- Category Views ---
class CategoryListCreateAPIView(generics.ListCreateAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly] # Authenticated can create, anyone can read

class CategoryRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAdminUser] # Only admins can modify/delete categories


# --- Size Views ---
class SizeListCreateAPIView(generics.ListCreateAPIView):
    queryset = Size.objects.all()
    serializer_class = SizeSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

class SizeRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Size.objects.all()
    serializer_class = SizeSerializer
    permission_classes = [permissions.IsAdminUser]


# --- Product Views ---
class ProductListCreateAPIView(generics.ListCreateAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly] # Adjust permissions as needed

    def get_queryset(self):
        # Optional: Allow filtering by category or search term
        queryset = super().get_queryset()
        category_name = self.request.query_params.get('category', None)
        search_term = self.request.query_params.get('search', None)

        if category_name:
            queryset = queryset.filter(category__name__icontains=category_name)
        if search_term:
            queryset = queryset.filter(name__icontains=search_term) # Or other fields
        return queryset

class ProductRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly] # Adjust permissions as needed


# --- Invoice Views ---
class InvoiceListCreateAPIView(generics.ListCreateAPIView):
    queryset = Invoice.objects.all().order_by('-invoice_date', '-created_at')
    serializer_class = InvoiceSerializer
    permission_classes = [permissions.IsAuthenticated] # Only authenticated users can list/create invoices

    def perform_create(self, serializer):
        # Set created_by and last_modified_by on creation
        serializer.save(created_by=self.request.user, last_modified_by=self.request.user)

class InvoiceRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer
    permission_classes = [permissions.IsAuthenticated] # Only authenticated users can modify/delete invoices

    def perform_update(self, serializer):
        # Set last_modified_by on update
        serializer.save(last_modified_by=self.request.user)


# --- Invoice Item Views (Often managed via nested serializers or separate API) ---
class InvoiceItemListCreateAPIView(generics.ListCreateAPIView):
    queryset = InvoiceItem.objects.all()
    serializer_class = InvoiceItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Filter invoice items by invoice_id if passed in URL
        invoice_id = self.kwargs.get('invoice_pk') # Assuming nested URL
        if invoice_id:
            return InvoiceItem.objects.filter(invoice__pk=invoice_id)
        return super().get_queryset()

    def perform_create(self, serializer):
        # Associate item with an invoice (if not done via nested serializer)
        invoice_id = self.request.data.get('invoice') # Expect invoice ID in payload
        invoice = Invoice.objects.get(pk=invoice_id)
        serializer.save(invoice=invoice)


class InvoiceItemRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = InvoiceItem.objects.all()
    serializer_class = InvoiceItemSerializer
    permission_classes = [permissions.IsAuthenticated]


# --- Dashboard and Reporting Views ---
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def dashboard_overview(request):
    total_products = Product.objects.count()
    total_value = Product.objects.aggregate(
        total=Coalesce(Sum(F('price') * F('quantity')), Decimal('0.00'), output_field=DecimalField())
    )['total']

    low_stock_threshold = 20 # Define your low stock threshold
    low_stock_items_count = Product.objects.filter(quantity__lte=low_stock_threshold).count()

    # Mock monthly sales data (replace with real data from your sales/invoice history)
    # For real data, you'd aggregate InvoiceItem data by month
    today = timezone.now()
    current_month_sales = InvoiceItem.objects.filter(
        invoice__invoice_date__year=today.year,
        invoice__invoice_date__month=today.month,
        invoice__status__in=['paid', 'uncompleted'] # Only count sales from certain invoice statuses
    ).aggregate(
        total_sales=Coalesce(Sum('subtotal'), Decimal('0.00'), output_field=DecimalField())
    )['total_sales']

    # Example: Low Stock Items list
    low_stock_items_list = Product.objects.filter(quantity__lte=low_stock_threshold).order_by('quantity')[:10]
    low_stock_serializer = ProductSerializer(low_stock_items_list, many=True) # Re-use ProductSerializer

    return Response({
        'total_products': total_products,
        'total_value': total_value,
        'low_stock_items_count': low_stock_items_count,
        'monthly_sales': current_month_sales,
        'low_stock_items': low_stock_serializer.data,
        # Placeholder for sales data over time (you'd need to aggregate this monthly/weekly)
        'sales_data_history': [
            {"month": "Jan", "sales": 4000, "products": 240},
            {"month": "Feb", "sales": 3000, "products": 198},
            {"month": "Mar", "sales": 5000, "products": 300},
            {"month": "Apr", "sales": 4500, "products": 278},
            {"month": "May", "sales": 6000, "products": 359},
            {"month": "Jun", "sales": 5500, "products": 325},
        ]
    })

# Utility API for product price lookup (for InvoiceItem forms)
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_product_price(request, pk):
    try:
        product = Product.objects.get(pk=pk)
        return Response({'price': product.price})
    except Product.DoesNotExist:
        return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)