from django import template

register = template.Library()

@register.filter
def add_price(price, additional_price):
    return price + additional_price

@register.filter
def split(value, delimiter=","):
    return value.split(delimiter)