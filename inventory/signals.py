from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone
from .models import Product, PurchaseOrder, InventoryTransaction
from .utils import get_low_stock_alerts, generate_sku

@receiver(post_save, sender=Product)
def handle_product_save(sender, instance, created, **kwargs):
    """Handle product creation and updates"""
    if created:
        # Generate SKU if not provided
        if not instance.sku:
            instance.sku = generate_sku(
                instance.category.name if instance.category else 'MISC',
                instance.name
            )
            instance.save()
    
    # Check stock levels
    if instance.quantity <= instance.minimum_stock:
        notify_low_stock(instance)

@receiver(post_save, sender=InventoryTransaction)
def handle_transaction_save(sender, instance, created, **kwargs):
    """Handle inventory transaction creation"""
    if created:
        # Update product quantity
        product = instance.product
        
        # Check if stock level is low after transaction
        if product.quantity <= product.minimum_stock:
            notify_low_stock(product)
        
        # Create purchase order suggestion if needed
        if product.quantity <= product.reorder_point:
            suggest_purchase_order(product)

@receiver(post_save, sender=PurchaseOrder)
def handle_purchase_order_save(sender, instance, created, **kwargs):
    """Handle purchase order status changes"""
    if not created and instance.status == 'RECEIVED':
        # Create inventory transactions for received items
        for item in instance.items.all():
            InventoryTransaction.objects.create(
                product=item.product,
                transaction_type='PURCHASE',
                quantity=item.received_quantity,
                unit_price=item.unit_price,
                reference_number=instance.po_number,
                created_by=instance.created_by,
                notes=f"Received from PO: {instance.po_number}"
            )

def notify_low_stock(product):
    """Send low stock notification"""
    if not settings.EMAIL_HOST:  # Skip if email is not configured
        return
        
    context = {
        'product': product,
        'timestamp': timezone.now(),
    }
    
    subject = f"Low Stock Alert: {product.name}"
    message = render_to_string('inventory/emails/low_stock_alert.html', context)
    
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[settings.INVENTORY_NOTIFICATION_EMAIL],
        html_message=message,
    )

def suggest_purchase_order(product):
    """Create purchase order suggestion for low stock product"""
    if not product.supplier:
        return
        
    # Check if there's already a pending order for this product
    existing_order = PurchaseOrder.objects.filter(
        supplier=product.supplier,
        status__in=['DRAFT', 'PENDING', 'APPROVED'],
        items__product=product
    ).exists()
    
    if not existing_order:
        # Calculate suggested order quantity
        suggested_quantity = (product.reorder_point - product.quantity) + product.minimum_stock
        
        # Create draft purchase order
        po = PurchaseOrder.objects.create(
            supplier=product.supplier,
            status='DRAFT',
            expected_delivery=timezone.now() + timezone.timedelta(days=7),
            created_by=product.created_by,
            notes=f"Auto-generated order for low stock product: {product.name}"
        )
        
        # Add order item
        po.items.create(
            product=product,
            quantity=suggested_quantity,
            unit_price=product.price  # Use current product price as default
        )