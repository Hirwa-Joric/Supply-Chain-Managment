from django.contrib import admin
from .models import (
    Category,
    Product,
    Supplier,
    PurchaseOrder,
    PurchaseOrderItem,
    InventoryTransaction
)

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at', 'updated_at')
    search_fields = ('name',)
    ordering = ('name',)

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'contact_person', 'email', 'phone', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'contact_person', 'email')
    ordering = ('name',)

class PurchaseOrderItemInline(admin.TabularInline):
    model = PurchaseOrderItem
    extra = 1

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'sku', 'category', 'quantity', 'price', 'supplier', 'stock_status', 'is_active')
    list_filter = ('category', 'supplier', 'is_active')
    search_fields = ('name', 'sku', 'description')
    ordering = ('name',)
    readonly_fields = ('created_at', 'updated_at')
    list_editable = ('price', 'is_active')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('category', 'supplier')

@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ('po_number', 'supplier', 'order_date', 'expected_delivery', 'status', 'total')
    list_filter = ('status', 'supplier', 'order_date')
    search_fields = ('po_number', 'supplier__name')
    readonly_fields = ('po_number', 'subtotal', 'total')
    inlines = [PurchaseOrderItemInline]
    
    def save_model(self, request, obj, form, change):
        if not obj.created_by:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(InventoryTransaction)
class InventoryTransactionAdmin(admin.ModelAdmin):
    list_display = ('transaction_type', 'product', 'quantity', 'transaction_date', 'reference_number')
    list_filter = ('transaction_type', 'transaction_date', 'product')
    search_fields = ('product__name', 'reference_number', 'notes')
    readonly_fields = ('transaction_date',)
    
    def save_model(self, request, obj, form, change):
        if not obj.created_by:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)