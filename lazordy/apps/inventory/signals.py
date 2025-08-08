from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import StockMovement, StockMovementType


@receiver(post_save, sender=StockMovement)
def apply_stock_movement(sender, instance: StockMovement, created, **kwargs):
    if not created:
        return
    product = instance.product
    if instance.movement_type == StockMovementType.IN:
        product.quantity = product.quantity + instance.quantity
    elif instance.movement_type == StockMovementType.OUT:
        product.quantity = max(product.quantity - instance.quantity, 0)
    # ADJUSTMENT type means set to quantity amount
    elif instance.movement_type == StockMovementType.ADJUSTMENT:
        product.quantity = max(instance.quantity, 0)
    product.save(update_fields=["quantity"])