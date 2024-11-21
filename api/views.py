from rest_framework import viewsets, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Sum, Count, F, Q, ExpressionWrapper, DecimalField
from django.db.models.functions import TruncMonth
from django.utils import timezone
from datetime import timedelta
from .serializers import (
    CategorySerializer,
    ProductSerializer,
    SupplierSerializer,
    PurchaseOrderSerializer,
    InventoryTransactionSerializer,
    DashboardStatsSerializer
)
from inventory.models import (
    Category,
    Product,
    Supplier,
    PurchaseOrder,
    InventoryTransaction
)

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'sku', 'description']
    ordering_fields = ['name', 'quantity', 'price', 'created_at']
    ordering = ['name']

    def get_queryset(self):
        queryset = super().get_queryset().select_related('category', 'supplier')
        category = self.request.query_params.get('category', None)
        supplier = self.request.query_params.get('supplier', None)
        stock_status = self.request.query_params.get('stock_status', None)

        if category:
            queryset = queryset.filter(category_id=category)
        if supplier:
            queryset = queryset.filter(supplier_id=supplier)
        if stock_status:
            if stock_status == 'OUT_OF_STOCK':
                queryset = queryset.filter(quantity=0)
            elif stock_status == 'LOW_STOCK':
                queryset = queryset.filter(quantity__lte=F('minimum_stock'))
            elif stock_status == 'IN_STOCK':
                queryset = queryset.filter(quantity__gt=F('minimum_stock'))

        return queryset

    @action(detail=True)
    def stock_history(self, request, pk=None):
        product = self.get_object()
        transactions = InventoryTransaction.objects.filter(
            product=product
        ).order_by('-transaction_date')[:30]
        serializer = InventoryTransactionSerializer(transactions, many=True)
        return Response(serializer.data)

class SupplierViewSet(viewsets.ModelViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'contact_person', 'email', 'phone']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']

    @action(detail=True)
    def products(self, request, pk=None):
        supplier = self.get_object()
        products = Product.objects.filter(supplier=supplier)
        serializer = ProductSerializer(products, many=True)
        return Response(serializer.data)

class PurchaseOrderViewSet(viewsets.ModelViewSet):
    queryset = PurchaseOrder.objects.all()
    serializer_class = PurchaseOrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['po_number', 'supplier__name']
    ordering_fields = ['order_date', 'expected_delivery', 'total']
    ordering = ['-order_date']

    def get_queryset(self):
        queryset = super().get_queryset().select_related('supplier', 'created_by')
        status = self.request.query_params.get('status', None)
        if status:
            queryset = queryset.filter(status=status)
        return queryset

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        order = self.get_object()
        new_status = request.data.get('status')
        
        if new_status not in dict(PurchaseOrder.STATUS_CHOICES):
            return Response({'error': 'Invalid status'}, status=400)
            
        order.status = new_status
        order.save()
        return Response(self.get_serializer(order).data)

class InventoryTransactionViewSet(viewsets.ModelViewSet):
    queryset = InventoryTransaction.objects.all()
    serializer_class = InventoryTransactionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['product__name', 'reference_number']
    ordering_fields = ['transaction_date', 'quantity']
    ordering = ['-transaction_date']

    def get_queryset(self):
        queryset = super().get_queryset().select_related('product', 'created_by')
        product = self.request.query_params.get('product', None)
        transaction_type = self.request.query_params.get('transaction_type', None)
        
        if product:
            queryset = queryset.filter(product_id=product)
        if transaction_type:
            queryset = queryset.filter(transaction_type=transaction_type)
            
        return queryset

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

class DashboardViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        # Date range
        end_date = timezone.now()
        start_date = end_date - timedelta(days=30)
        
        # Calculate statistics
        stats = {
            'total_products': Product.objects.count(),
            'low_stock_products': Product.objects.filter(quantity__lte=F('minimum_stock')).count(),
            'out_of_stock_products': Product.objects.filter(quantity=0).count(),
            'active_suppliers': Supplier.objects.filter(is_active=True).count(),
            'total_inventory_value': Product.objects.aggregate(
                total=Sum(F('quantity') * F('price'), output_field=DecimalField())
            )['total'] or 0,
            'pending_orders': PurchaseOrder.objects.filter(
                status__in=['PENDING', 'APPROVED', 'ORDERED']
            ).count(),
            'monthly_transactions': InventoryTransaction.objects.filter(
                transaction_date__range=[start_date, end_date]
            ).annotate(
                month=TruncMonth('transaction_date')
            ).values('month').annotate(
                total_value=Sum(F('quantity') * F('unit_price'))
            ).order_by('month'),
            'top_products': Product.objects.annotate(
                total_sales=Sum('transactions__quantity',
                    filter=Q(
                        transactions__transaction_type='SALE',
                        transactions__transaction_date__range=[start_date, end_date]
                    )
                )
            ).exclude(total_sales=None).order_by('-total_sales')[:5]
        }
        
        serializer = DashboardStatsSerializer(stats)
        return Response(serializer.data)