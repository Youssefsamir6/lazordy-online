# D:\lazordy\lazordy\inventory\serializers.py

from rest_framework import serializers
from .models import Category, Size, Product, Invoice, InvoiceItem # Ensure all models are imported
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _ # Import gettext_lazy

User = get_user_model() # Get the currently active User model

class CategorySerializer(serializers.ModelSerializer):
    """
    Serializer for the Category model.
    Converts Category instances to JSON and vice-versa.
    """
    class Meta:
        model = Category
        fields = '__all__' # Include all fields from the Category model

class SizeSerializer(serializers.ModelSerializer):
    """
    Serializer for the Size model.
    Converts Size instances to JSON and vice-versa.
    """
    class Meta:
        model = Size
        fields = '__all__' # Include all fields from the Size model

class ProductSerializer(serializers.ModelSerializer):
    """
    Serializer for the Product model.
    Handles nested relationships for Category and Size, and customizes field display.
    """
    # Read-only field to display category name (for GET requests)
    category = CategorySerializer(read_only=True)
    # Write-only field to accept category ID for creating/updating products (for POST/PUT/PATCH)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), source='category', write_only=True, required=False, allow_null=True
    )

    # Read-only field to display sizes (for GET requests)
    sizes = SizeSerializer(many=True, read_only=True)
    # Write-only field to accept a list of size IDs for creating/updating products
    size_ids = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Size.objects.all(), source='size', write_only=True, required=False
    )

    # Custom field to display the human-readable status (e.g., "Out of Stock" instead of "out_of_stock")
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'description', 'price', 'quantity', 'item_code',
            'color', 'measurements_cm', 'category', 'category_id', 'photo',
            'sizes', 'size_ids', 'status', 'status_display', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at'] # These fields are automatically set by Django

    def create(self, validated_data):
        """
        Custom create method to handle ManyToMany relationship for 'sizes'.
        """
        # Pop the 'size' data (which comes from 'size_ids' due to source='size')
        sizes_data = validated_data.pop('size', [])
        # Create the Product instance
        product = Product.objects.create(**validated_data)
        # Set the ManyToMany relationship
        product.sizes.set(sizes_data)
        return product

    def update(self, instance, validated_data):
        """
        Custom update method to handle ManyToMany relationship for 'sizes'.
        """
        # Pop the 'size' data
        sizes_data = validated_data.pop('size', [])

        # Update standard fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save() # Call model's save method to trigger any custom logic (e.g., status updates)

        # Update ManyToMany relationship
        instance.sizes.set(sizes_data)
        return instance

class InvoiceItemSerializer(serializers.ModelSerializer):
    """
    Serializer for the InvoiceItem model.
    Handles product association and displays calculated subtotal.
    """
    # Read-only fields that are set by the InvoiceItem model's save method
    product_name = serializers.CharField(read_only=True)
    unit_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    # Write-only field to accept product ID when creating/updating an invoice item
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(), source='product', write_only=True
    )

    class Meta:
        model = InvoiceItem
        fields = ['id', 'invoice', 'product_id', 'product_name', 'quantity', 'unit_price', 'subtotal']
        read_only_fields = ['subtotal'] # Subtotal is calculated automatically

class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for Django's built-in User model.
    Used for displaying user information in related fields (e.g., created_by, last_modified_by).
    """
    # Add a 'role' field dynamically based on user's superuser status or group membership
    # This matches the logic in your React frontend's useAuth hook
    role = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'is_staff', 'is_superuser', 'role']
        read_only_fields = ['is_staff', 'is_superuser'] # These are managed by Django admin or specific API endpoints

    def get_role(self, obj):
        """
        Determine the user's role based on superuser status or group membership.
        """
        if obj.is_superuser:
            return _('admin') # Wrapped for translation
        # Assuming you have a Django Group named 'Staff'
        elif obj.groups.filter(name='Staff').exists():
            return _('staff') # Wrapped for translation
        return _('user') # Wrapped for translation # Default role for other authenticated users

class InvoiceSerializer(serializers.ModelSerializer):
    """
    Serializer for the Invoice model.
    Includes nested InvoiceItems and displays related user information.
    """
    # Nested serializer for InvoiceItems (read-only for display)
    # If you want to create/update items when creating/updating an invoice,
    # you'd need to implement custom create/update methods for InvoiceSerializer
    items = InvoiceItemSerializer(many=True, read_only=True)

    # Read-only fields to display details of the user who created/modified the invoice
    created_by = UserSerializer(read_only=True)
    last_modified_by = UserSerializer(read_only=True)

    # Custom field to display the human-readable status (e.g., "Uncompleted" instead of "uncompleted")
    status_display = serializers.CharField(source='get_status_display', read_only=True)


    class Meta:
        model = Invoice
        fields = [
            'id', 'invoice_number', 'customer_name', 'home_address', 'customer_phone',
            'discount_amount', 'total_amount', 'amount_paid', 'amount_remaining',
            'status', 'status_display', 'invoice_date', 'created_at', 'updated_at',
            'created_by', 'last_modified_by', 'items' # Include 'items' here
        ]
        read_only_fields = [
            'invoice_number', 'total_amount', 'amount_remaining',
            'created_at', 'updated_at',
            # 'created_by', 'last_modified_by' are set in api_views.py perform_create/update
        ]

    # If you want to allow creating/updating InvoiceItems directly when creating/updating an Invoice,
    # you would uncomment and implement the create/update methods below.
    # This is more complex as it requires handling nested writes.
    # For now, we assume InvoiceItems are managed separately or are read-only nested.
    # def create(self, validated_data):
    #     items_data = validated_data.pop('items', [])
    #     invoice = Invoice.objects.create(**validated_data)
    #     for item_data in items_data:
    #         InvoiceItem.objects.create(invoice=invoice, **item_data)
    #     return invoice

    # def update(self, instance, validated_data):
    #     items_data = validated_data.pop('items', [])
    #     # Update invoice fields
    #     for attr, value in validated_data.items():
    #         setattr(instance, attr, value)
    #     instance.save()
    #     # Handle invoice items (add, update, delete existing)
    #     # This is a simplified example; real-world might use update_or_create/bulk_create
    #     # existing_items = {item.id: item for item in instance.items.all()}
    #     # for item_data in items_data:
    #     #     item_id = item_data.get('id')
    #     #     if item_id and item_id in existing_items:
    #     #         item = existing_items.pop(item_id)
    #     #         for attr, value in item_data.items():
    #     #             setattr(item, attr, value)
    #     #         item.save()
    #     #     else:
    #     #         InvoiceItem.objects.create(invoice=instance, **item_data)
    #     # # Delete items not present in the new data
    #     # for item in existing_items.values():
    #     #     item.delete()
    #     # return instance