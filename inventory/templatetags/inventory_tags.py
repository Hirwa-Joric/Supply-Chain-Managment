from django import template
from django.template.defaultfilters import floatformat
from decimal import Decimal

register = template.Library()

@register.filter
def currency(value):
    """Format value as currency"""
    try:
        value = float(value)
        return f"${floatformat(value, 2)}"
    except (ValueError, TypeError):
        return ""

@register.filter
def percentage(value):
    """Format value as percentage"""
    try:
        value = float(value)
        return f"{floatformat(value, 1)}%"
    except (ValueError, TypeError):
        return ""

@register.filter
def multiply(value, arg):
    """Multiply the value by the argument"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0