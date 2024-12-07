from django.contrib import admin
from .models import (
    Supplier,
    Product,
    PurchaseOrder,
    PurchaseOrderItem,
    Warehouse,
    InventoryMovement
)

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'contact_person', 'email', 'phone', 'rating', 'active')
    list_filter = ('active', 'rating')
    search_fields = ('name', 'contact_person', 'email')

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'sku', 'unit_price', 'stock_quantity', 'supplier')
    list_filter = ('supplier', 'stock_quantity')
    search_fields = ('name', 'sku')

@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ('supplier', 'order_date', 'status', 'total_amount', 'expected_delivery')
    list_filter = ('status', 'supplier')
    search_fields = ('supplier__name',)

@admin.register(PurchaseOrderItem)
class PurchaseOrderItemAdmin(admin.ModelAdmin):
    list_display = ('purchase_order', 'product', 'quantity', 'unit_price', 'total_price')
    list_filter = ('purchase_order', 'product')
    search_fields = ('product__name',)

@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ('name', 'location', 'capacity', 'manager', 'active')
    list_filter = ('active',)
    search_fields = ('name', 'location', 'manager')

@admin.register(InventoryMovement)
class InventoryMovementAdmin(admin.ModelAdmin):
    list_display = ('product', 'warehouse', 'movement_type', 'quantity', 'movement_date')
    list_filter = ('movement_type', 'warehouse', 'movement_date')
    search_fields = ('product__name', 'reference_number')
