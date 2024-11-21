from celery import shared_task
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from .models import Product, PurchaseOrder, Supplier
from .services import InventoryService
from .utils import (
    get_low_stock_alerts,
    calculate_reorder_quantities,
    get_order_fulfillment_metrics
)

@shared_task
def check_stock_levels():
    """Check stock levels and send notifications"""
    low_stock_products = get_low_stock_alerts()
    
    if low_stock_products:
        context = {
            'products': low_stock_products,
            'timestamp': timezone.now()
        }
        
        message = render_to_string('inventory/emails/low_stock_report.html', context)
        
        send_mail(
            subject='Low Stock Alert Report',
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.INVENTORY_NOTIFICATION_EMAIL],
            html_message=message
        )
    
    return len(low_stock_products)

@shared_task
def generate_purchase_orders():
    """Generate purchase orders for low stock items"""
    suggestions = calculate_reorder_quantities()
    orders_created = 0
    
    for suggestion in suggestions:
        product = suggestion['product']
        if not InventoryService._has_pending_order(product):
            InventoryService._create_reorder_draft(
                product,
                suggestion['suggested_reorder'],
                suggestion['avg_daily_usage']
            )
            orders_created += 1
    
    return orders_created

@shared_task
def check_overdue_orders():
    """Check for overdue purchase orders"""
    overdue_orders = PurchaseOrder.objects.filter(
        status__in=['ORDERED', 'APPROVED'],
        expected_delivery__lt=timezone.now()
    ).select_related('supplier')
    
    if overdue_orders:
        context = {
            'orders': overdue_orders,
            'timestamp': timezone.now()
        }
        
        message = render_to_string('inventory/emails/overdue_orders_report.html', context)
        
        send_mail(
            subject='Overdue Purchase Orders Report',
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.INVENTORY_NOTIFICATION_EMAIL],
            html_message=message
        )
    
    return overdue_orders.count()

@shared_task
def analyze_inventory_metrics():
    """Analyze inventory metrics and generate reports"""
    end_date = timezone.now()
    start_date = end_date - timedelta(days=30)
    
    metrics = get_order_fulfillment_metrics()
    
    # Additional metrics calculation
    product_metrics = Product.objects.filter(
        is_active=True
    ).annotate(
        stock_value=F('quantity') * F('price'),
        turnover_rate=Sum(
            'transactions__quantity',
            filter=Q(
                transactions__transaction_type='SALE',
                transactions__transaction_date__range=[start_date, end_date]
            )
        ) / F('quantity')
    )
    
    high_value_items = product_metrics.order_by('-stock_value')[:10]
    high_turnover_items = product_metrics.order_by('-turnover_rate')[:10]
    
    context = {
        'metrics': metrics,
        'high_value_items': high_value_items,
        'high_turnover_items': high_turnover_items,
        'period_days': 30,
        'timestamp': timezone.now()
    }
    
    message = render_to_string('inventory/emails/inventory_metrics_report.html', context)
    
    send_mail(
        subject='Monthly Inventory Metrics Report',
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[settings.INVENTORY_NOTIFICATION_EMAIL],
        html_message=message
    )
    
    return True

@shared_task
def supplier_performance_review():
    """Review supplier performance and generate report"""
    end_date = timezone.now()
    start_date = end_date - timedelta(days=90)
    
    suppliers = Supplier.objects.filter(is_active=True)
    performance_data = []
    
    for supplier in suppliers:
        orders = PurchaseOrder.objects.filter(
            supplier=supplier,
            order_date__range=[start_date, end_date]
        )
        
        if orders.exists():
            on_time_delivery = orders.filter(
                status='COMPLETED',
                updated_at__lte=F('expected_delivery')
            ).count() / orders.count() * 100
            
            quality_issues = supplier.products.filter(
                transactions__transaction_type='RETURN',
                transactions__transaction_date__range=[start_date, end_date]
            ).count()
            
            performance_data.append({
                'supplier': supplier,
                'order_count': orders.count(),
                'on_time_delivery': on_time_delivery,
                'quality_issues': quality_issues,
                'total_value': orders.aggregate(total=Sum('total'))['total']
            })
    
    if performance_data:
        context = {
            'performance_data': performance_data,
            'period_days': 90,
            'timestamp': timezone.now()
        }
        
        message = render_to_string('inventory/emails/supplier_performance_report.html', context)
        
        send_mail(
            subject='Quarterly Supplier Performance Report',
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.INVENTORY_NOTIFICATION_EMAIL],
            html_message=message
        )
    
    return len(performance_data)