from django.contrib import admin
from .models import (
    Category, Product, Order, OrderItem, Client,
    ProductVariant, ShippingCost, Commune,
    MainVariant, QuantityType
)

# Directly registered models
admin.site.register(Client)
admin.site.register(Category)
admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(ShippingCost)
admin.site.register(Commune)


# Inline for QuantityType inside MainVariant
class QuantityTypeInline(admin.TabularInline):
    model = QuantityType
    extra = 1


# Inline for MainVariant inside Product
class MainVariantInline(admin.StackedInline):
    model = MainVariant
    extra = 1
    show_change_link = True


# Inline for Optional Variants (ProductVariant)
class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1


# Product Admin with all inlines
class ProductAdmin(admin.ModelAdmin):
    inlines = [MainVariantInline, ProductVariantInline]
    list_display = ('name', 'category', 'disponibility', 'price', 'stock')
    search_fields = ('name',)
    list_filter = ('category', 'disponibility')

admin.site.register(Product, ProductAdmin)


# MainVariant Admin with QuantityType inline
class MainVariantAdmin(admin.ModelAdmin):
    inlines = [QuantityTypeInline]
    list_display = ('product', 'value')
    search_fields = ('product__name', 'value')

admin.site.register(MainVariant, MainVariantAdmin)
