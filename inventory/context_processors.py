from django.db.models import Count, Q
from .models import Product, PurchaseOrder
from .utils import get_low_stock_alerts

def inventory_stats(request):
    """Add common inventory statistics to all templates"""
    if not request.user.is_authenticated:
        return {}
        
    low_stock_count = get_low_stock_alerts().count()
    pending_orders = PurchaseOrder.objects.filter(
        status__in=['PENDING', 'APPROVED', 'ORDERED']
    ).count()
    
    return {
        'inventory_stats': {
            'low_stock_count': low_stock_count,
            'pending_orders': pending_orders,
            'total_products': Product.objects.count(),
        }
    }