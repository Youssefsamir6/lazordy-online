from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.common.models import TimeStampedModel, UUIDModel


class Category(UUIDModel, TimeStampedModel):
    name = models.CharField(max_length=150)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='children')

    class Meta:
        verbose_name_plural = _('Categories')
        ordering = ['name']

    def __str__(self) -> str:
        return self.name


class Size(UUIDModel, TimeStampedModel):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self) -> str:
        return self.name


class ProductStatus(models.TextChoices):
    AVAILABLE = 'available', _('Available')
    SOLD = 'sold', _('Sold')
    RESERVED = 'reserved', _('Reserved')
    OUT_OF_STOCK = 'out_of_stock', _('Out of stock')


class Product(UUIDModel, TimeStampedModel):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='products')
    price = models.DecimalField(max_digits=12, decimal_places=2)
    cost = models.DecimalField(max_digits=12, decimal_places=2)
    quantity = models.IntegerField(default=0)
    item_code = models.CharField(max_length=100, unique=True)
    color = models.CharField(max_length=50, blank=True)
    measurements = models.CharField(max_length=100, blank=True)
    sizes = models.ManyToManyField(Size, blank=True, related_name='products')
    photo = models.ImageField(upload_to='products/', blank=True, null=True)
    status = models.CharField(max_length=20, choices=ProductStatus.choices, default=ProductStatus.AVAILABLE)
    low_stock_threshold = models.IntegerField(default=1)

    def __str__(self) -> str:
        return f"{self.name} ({self.item_code})"

    @property
    def is_low_stock(self) -> bool:
        return self.quantity <= self.low_stock_threshold


class StockMovementType(models.TextChoices):
    IN = 'in', _('In')
    OUT = 'out', _('Out')
    ADJUSTMENT = 'adjustment', _('Adjustment')


class StockMovement(UUIDModel, TimeStampedModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='movements')
    movement_type = models.CharField(max_length=20, choices=StockMovementType.choices)
    quantity = models.IntegerField()
    note = models.CharField(max_length=255, blank=True)
    performed_by = models.ForeignKey('auth.User', null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f"{self.movement_type} {self.quantity} for {self.product}"
