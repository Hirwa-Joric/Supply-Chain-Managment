from rest_framework import serializers
from inventory.models import Category, Product, Supplier, PurchaseOrder, PurchaseOrderItem, InventoryTransaction

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'description']

class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = ['id', 'name', 'contact_person', 'email', 'phone', 'is_active']

class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    stock_status = serializers.CharField(read_only=True)
    stock_value = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'sku', 'category', 'category_name', 'description',
            'quantity', 'minimum_stock', 'reorder_point', 'price', 'supplier',
            'supplier_name', 'location', 'barcode', 'is_active', 'stock_status',
            'stock_value'
        ]

class PurchaseOrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = PurchaseOrderItem
        fields = ['id', 'product', 'product_name', 'quantity', 'unit_price', 'received_quantity', 'subtotal']

class PurchaseOrderSerializer(serializers.ModelSerializer):
    items = PurchaseOrderItemSerializer(many=True, read_only=True)
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = PurchaseOrder
        fields = [
            'id', 'po_number', 'supplier', 'supplier_name', 'order_date',
            'expected_delivery', 'status', 'status_display', 'subtotal',
            'tax', 'shipping', 'total', 'notes', 'items', 'created_by_username'
        ]
        read_only_fields = ['po_number', 'order_date', 'subtotal', 'total']

class InventoryTransactionSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    transaction_type_display = serializers.CharField(source='get_transaction_type_display', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    total_value = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = InventoryTransaction
        fields = [
            'id', 'product', 'product_name', 'transaction_type',
            'transaction_type_display', 'quantity', 'unit_price',
            'reference_number', 'transaction_date', 'notes',
            'created_by_username', 'total_value'
        ]
        read_only_fields = ['transaction_date']

    def validate(self, data):
        """
        Check that the transaction is valid (e.g., enough stock for sales)
        """
        if data['transaction_type'] in ['SALE', 'TRANSFER']:
            product = data['product']
            if data['quantity'] > product.quantity:
                raise serializers.ValidationError(
                    f"Insufficient stock. Available: {product.quantity}, Requested: {data['quantity']}"
                )
        return data

class DashboardStatsSerializer(serializers.Serializer):
    total_products = serializers.IntegerField()
    low_stock_products = serializers.IntegerField()
    out_of_stock_products = serializers.IntegerField()
    active_suppliers = serializers.IntegerField()
    total_inventory_value = serializers.DecimalField(max_digits=10, decimal_places=2)
    pending_orders = serializers.IntegerField()
    monthly_transactions = serializers.ListField()
    top_products = serializers.ListField()