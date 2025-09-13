from django import template

register = template.Library()

@register.filter(name='check_value')
def check_value(value, threshold):
    """Checks if value is greater than threshold"""
    return value > threshold