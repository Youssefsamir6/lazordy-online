from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import InvoiceItem
from apps.inventory.models import Product


@receiver(post_save, sender=InvoiceItem)
def reduce_stock_on_item_save(sender, instance: InvoiceItem, created, **kwargs):
    product = instance.product
    if not product:
        return
    # For simplicity, on every save, recalc quantity from all items of open invoices
    # but to keep it efficient, adjust by delta if created or quantity changed
    try:
        old = sender.objects.get(pk=instance.pk)
        old_qty = old.quantity
    except sender.DoesNotExist:
        old_qty = 0
    delta = instance.quantity - old_qty
    if delta:
        product.quantity = max(product.quantity - delta, 0)
        product.save(update_fields=["quantity"])


@receiver(post_delete, sender=InvoiceItem)
def restore_stock_on_item_delete(sender, instance: InvoiceItem, **kwargs):
    product = instance.product
    if not product:
        return
    product.quantity = product.quantity + instance.quantity
    product.save(update_fields=["quantity"])