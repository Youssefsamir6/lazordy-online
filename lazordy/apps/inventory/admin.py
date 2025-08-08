from django.contrib import admin
from .models import Category, Size, Product, StockMovement


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "parent", "created_at")
    search_fields = ("name",)


@admin.register(Size)
class SizeAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "item_code", "category", "price", "quantity", "status")
    list_filter = ("status", "category")
    search_fields = ("name", "item_code")


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ("product", "movement_type", "quantity", "created_at")
    list_filter = ("movement_type",)
