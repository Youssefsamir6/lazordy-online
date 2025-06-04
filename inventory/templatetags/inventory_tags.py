# inventory/templatetags/inventory_tags.py
from django import template
from decimal import Decimal
from django.db.models import Sum

register = template.Library()

@register.filter
def lineitems_subtotal(items):
    """Calculates the sum of subtotals for a queryset of invoice items."""
    return items.aggregate(total_sub=Sum('subtotal'))['total_sub'] or Decimal('0.00')

# This filter and its decorator must be at the same level as lineitems_subtotal
@register.filter
def custom_replace(value, arg):
    """
    Replaces all occurrences of a substring with another.
    Usage: {{ value|custom_replace:"old_substring,new_substring" }}
    Example: {{ product.status|custom_replace:"_, " }}
    """
    try:
        old_char, new_char = arg.split(',')
        return value.replace(old_char, new_char)
    except ValueError:
        return value # Return original value if arg is malformed or not enough parts
    except AttributeError:
        return value # Return original value if 'value' is not a string