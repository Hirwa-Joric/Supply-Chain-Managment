from django.db.models import Sum, F, Q, ExpressionWrapper, DecimalField
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
from .models import Product, PurchaseOrder, InventoryTransaction

def generate_sku(category_name, product_name):
    """Generate SKU based on category and product name"""
    category_prefix = ''.join(word[0].upper() for word in category_name.split())[:3]
    product_part = ''.join(word[0].upper() for word in product_name.split())[:3]
    timestamp = datetime.now().strftime('%y%m%d')
    return f"{category_prefix}{product_part}{timestamp}"

def calculate_stock_value(product_queryset=None):
    """Calculate total stock value for given products"""
    if product_queryset is None:
        product_queryset = Product.objects.all()
    
    return product_queryset.aggregate(
        total_value=Sum(
            F('quantity') * F('price'),
            output_field=DecimalField(max_digits=10, decimal_places=2)
        )
    )['total_value'] or Decimal('0.00')

def get_low_stock_alerts():
    """Get products that are low in stock"""
    return Product.objects.filter(
        quantity__lte=F('minimum_stock'),
        is_active=True
    ).select_related('supplier')

def get_stock_movement_summary(start_date=None, end_date=None, product=None):
    """Get summary of stock movements for given period"""
    queryset = InventoryTransaction.objects.all()
    
    if start_date and end_date:
        queryset = queryset.filter(transaction_date__range=[start_date, end_date])
    if product:
        queryset = queryset.filter(product=product)
        
    return queryset.values('transaction_type').annotate(
        total_quantity=Sum('quantity'),
        total_value=Sum(F('quantity') * F('unit_price'))
    )

def get_product_performance(days=30):
    """Get product performance metrics"""
    end_date = timezone.now()
    start_date = end_date - timedelta(days=days)
    
    return Product.objects.annotate(
        sales_quantity=Sum(
            'transactions__quantity',
            filter=Q(
                transactions__transaction_type='SALE',
                transactions__transaction_date__range=[start_date, end_date]
            )
        ),
        sales_value=Sum(
            F('transactions__quantity') * F('transactions__unit_price'),
            filter=Q(
                transactions__transaction_type='SALE',
                transactions__transaction_date__range=[start_date, end_date]
            )
        ),
        purchase_quantity=Sum(
            'transactions__quantity',
            filter=Q(
                transactions__transaction_type='PURCHASE',
                transactions__transaction_date__range=[start_date, end_date]
            )
        ),
        purchase_value=Sum(
            F('transactions__quantity') * F('transactions__unit_price'),
            filter=Q(
                transactions__transaction_type='PURCHASE',
                transactions__transaction_date__range=[start_date, end_date]
            )
        )
    )

def get_order_fulfillment_metrics():
    """Calculate order fulfillment metrics"""
    total_orders = PurchaseOrder.objects.exclude(status='DRAFT').count()
    completed_orders = PurchaseOrder.objects.filter(status='COMPLETED').count()
    cancelled_orders = PurchaseOrder.objects.filter(status='CANCELLED').count()
    
    if total_orders > 0:
        fulfillment_rate = (completed_orders / total_orders) * 100
        cancellation_rate = (cancelled_orders / total_orders) * 100
    else:
        fulfillment_rate = cancellation_rate = 0
        
    return {
        'total_orders': total_orders,
        'completed_orders': completed_orders,
        'cancelled_orders': cancelled_orders,
        'fulfillment_rate': fulfillment_rate,
        'cancellation_rate': cancellation_rate
    }

def calculate_reorder_quantities():
    """Calculate suggested reorder quantities for products"""
    low_stock_products = get_low_stock_alerts()
    reorder_suggestions = []
    
    for product in low_stock_products:
        avg_daily_usage = calculate_average_daily_usage(product)
        lead_time_days = get_supplier_lead_time(product.supplier) if product.supplier else 14
        safety_stock = calculate_safety_stock(product, avg_daily_usage)
        
        reorder_quantity = (avg_daily_usage * lead_time_days) + (product.reorder_point - product.quantity)
        
        reorder_suggestions.append({
            'product': product,
            'current_quantity': product.quantity,
            'suggested_reorder': max(reorder_quantity, 0),
            'avg_daily_usage': avg_daily_usage,
            'safety_stock': safety_stock
        })
    
    return reorder_suggestions

def calculate_average_daily_usage(product, days=90):
    """Calculate average daily usage for a product"""
    end_date = timezone.now()
    start_date = end_date - timedelta(days=days)
    
    total_usage = InventoryTransaction.objects.filter(
        product=product,
        transaction_type='SALE',
        transaction_date__range=[start_date, end_date]
    ).aggregate(
        total=Sum('quantity')
    )['total'] or 0
    
    return total_usage / days if total_usage > 0 else 0

def get_supplier_lead_time(supplier):
    """Calculate average supplier lead time based on past orders"""
    completed_orders = PurchaseOrder.objects.filter(
        supplier=supplier,
        status='COMPLETED'
    ).annotate(
        lead_time=ExpressionWrapper(
            F('updated_at') - F('order_date'),
            output_field=DecimalField()
        )
    )
    
    avg_lead_time = completed_orders.aggregate(
        avg_lead_time=Sum('lead_time') / completed_orders.count()
    )['avg_lead_time']
    
    return avg_lead_time.days if avg_lead_time else 14  # Default to 14 days if no data

def calculate_safety_stock(product, avg_daily_usage):
    """Calculate safety stock level based on usage patterns"""
    service_factor = 1.96  # 95% service level
    lead_time = get_supplier_lead_time(product.supplier) if product.supplier else 14
    
    # Calculate standard deviation of daily usage
    end_date = timezone.now()
    start_date = end_date - timedelta(days=90)
    
    daily_usage = InventoryTransaction.objects.filter(
        product=product,
        transaction_type='SALE',
        transaction_date__range=[start_date, end_date]
    ).values('transaction_date').annotate(
        daily_usage=Sum('quantity')
    )
    
    if not daily_usage:
        return product.minimum_stock
    
    # Calculate standard deviation
    usage_values = [d['daily_usage'] for d in daily_usage]
    mean = sum(usage_values) / len(usage_values)
    variance = sum((x - mean) ** 2 for x in usage_values) / len(usage_values)
    std_dev = variance ** 0.5
    
    safety_stock = service_factor * std_dev * (lead_time ** 0.5)
    return max(int(safety_stock), product.minimum_stock)