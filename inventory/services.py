from django.db import transaction
from django.db.models import F, Sum, Q
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
from .models import Product, Supplier, PurchaseOrder, InventoryTransaction
from .utils import calculate_reorder_quantities, get_supplier_lead_time

class InventoryService:
    @staticmethod
    @transaction.atomic
    def create_purchase_order(supplier_id, items, notes=None, created_by=None):
        """
        Create a purchase order with multiple items
        
        Args:
            supplier_id (int): ID of the supplier
            items (list): List of dictionaries containing product_id, quantity, and unit_price
            notes (str, optional): Notes for the purchase order
            created_by (User): User creating the order
        """
        try:
            supplier = Supplier.objects.get(pk=supplier_id)
            
            # Create purchase order
            po = PurchaseOrder.objects.create(
                supplier=supplier,
                notes=notes,
                created_by=created_by,
                status='DRAFT',
                expected_delivery=timezone.now() + timedelta(
                    days=get_supplier_lead_time(supplier)
                )
            )
            
            # Add items to the purchase order
            for item in items:
                product = Product.objects.get(pk=item['product_id'])
                po.items.create(
                    product=product,
                    quantity=item['quantity'],
                    unit_price=item['unit_price']
                )
            
            # Calculate totals
            po.save()  # This triggers the save method which updates totals
            
            return po
            
        except Exception as e:
            raise ValidationError(f"Error creating purchase order: {str(e)}")

    @staticmethod
    @transaction.atomic
    def receive_purchase_order(po_id, received_items, received_by):
        """
        Process receipt of purchase order items
        
        Args:
            po_id (int): Purchase order ID
            received_items (list): List of dictionaries containing item_id and received_quantity
            received_by (User): User processing the receipt
        """
        try:
            po = PurchaseOrder.objects.select_for_update().get(pk=po_id)
            
            if po.status not in ['ORDERED', 'PARTIALLY_RECEIVED']:
                raise ValidationError("Purchase order is not in a receivable state")
            
            total_received = 0
            total_expected = 0
            
            for received_item in received_items:
                po_item = po.items.get(pk=received_item['item_id'])
                received_qty = received_item['received_quantity']
                
                # Create inventory transaction
                InventoryTransaction.objects.create(
                    product=po_item.product,
                    transaction_type='PURCHASE',
                    quantity=received_qty,
                    unit_price=po_item.unit_price,
                    reference_number=po.po_number,
                    created_by=received_by,
                    notes=f"Received from PO: {po.po_number}"
                )
                
                # Update received quantity
                po_item.received_quantity = F('received_quantity') + received_qty
                po_item.save()
                
                total_received += received_qty
                total_expected += po_item.quantity
            
            # Update PO status
            if total_received >= total_expected:
                po.status = 'COMPLETED'
            else:
                po.status = 'PARTIALLY_RECEIVED'
            
            po.save()
            
            return po
            
        except Exception as e:
            raise ValidationError(f"Error processing receipt: {str(e)}")

    @staticmethod
    @transaction.atomic
    def process_stock_adjustment(product_id, quantity, adjustment_type, notes=None, created_by=None):
        """
        Process stock adjustment (damage, loss, return, etc.)
        
        Args:
            product_id (int): Product ID
            quantity (int): Adjustment quantity
            adjustment_type (str): Type of adjustment
            notes (str, optional): Notes for the adjustment
            created_by (User): User making the adjustment
        """
        try:
            product = Product.objects.select_for_update().get(pk=product_id)
            
            if adjustment_type not in dict(InventoryTransaction.TRANSACTION_TYPES):
                raise ValidationError("Invalid adjustment type")
            
            # Create transaction
            transaction = InventoryTransaction.objects.create(
                product=product,
                transaction_type=adjustment_type,
                quantity=quantity,
                reference_number=f"ADJ-{timezone.now().strftime('%Y%m%d%H%M%S')}",
                notes=notes,
                created_by=created_by,
                unit_price=product.price
            )
            
            return transaction
            
        except Exception as e:
            raise ValidationError(f"Error processing adjustment: {str(e)}")

    @classmethod
    def check_reorder_levels(cls):
        """Check and generate reorder suggestions"""
        suggestions = calculate_reorder_quantities()
        
        for suggestion in suggestions:
            product = suggestion['product']
            if not cls._has_pending_order(product):
                cls._create_reorder_draft(
                    product,
                    suggestion['suggested_reorder'],
                    suggestion['avg_daily_usage']
                )
        
        return suggestions

    @staticmethod
    def _has_pending_order(product):
        """Check if product has pending orders"""
        return PurchaseOrder.objects.filter(
            items__product=product,
            status__in=['DRAFT', 'PENDING', 'APPROVED', 'ORDERED']
        ).exists()

    @staticmethod
    def _create_reorder_draft(product, quantity, daily_usage):
        """Create draft purchase order for reorder"""
        if not product.supplier:
            return None
            
        po = PurchaseOrder.objects.create(
            supplier=product.supplier,
            status='DRAFT',
            notes=f"Auto-generated reorder. Daily usage: {daily_usage:.2f} units",
            created_by=None  # System generated
        )
        
        po.items.create(
            product=product,
            quantity=quantity,
            unit_price=product.price
        )
        
        return po

    @staticmethod
    def get_product_insights(product_id, days=90):
        """Get detailed insights for a product"""
        product = Product.objects.get(pk=product_id)
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        # Get transactions
        transactions = InventoryTransaction.objects.filter(
            product=product,
            transaction_date__range=[start_date, end_date]
        )
        
        # Calculate metrics
        sales = transactions.filter(transaction_type='SALE')
        purchases = transactions.filter(transaction_type='PURCHASE')
        
        metrics = {
            'total_sales': sales.aggregate(total=Sum('quantity'))['total'] or 0,
            'total_purchases': purchases.aggregate(total=Sum('quantity'))['total'] or 0,
            'avg_sale_price': sales.aggregate(
                avg=Sum(F('quantity') * F('unit_price')) / Sum('quantity')
            )['avg'] or 0,
            'stock_turns': len(sales) / days * 365 if days > 0 else 0,
            'stockout_days': cls._calculate_stockout_days(product, start_date, end_date),
        }
        
        return metrics

    @staticmethod
    def _calculate_stockout_days(product, start_date, end_date):
        """Calculate number of days product was out of stock"""
        stockout_transactions = InventoryTransaction.objects.filter(
            product=product,
            transaction_date__range=[start_date, end_date]
        ).order_by('transaction_date')
        
        stockout_days = 0
        current_quantity = product.quantity
        current_date = start_date
        
        for transaction in stockout_transactions:
            if current_quantity <= 0:
                stockout_days += (transaction.transaction_date - current_date).days
            
            if transaction.transaction_type in ['PURCHASE', 'RETURN']:
                current_quantity += transaction.quantity
            else:
                current_quantity -= transaction.quantity
            
            current_date = transaction.transaction_date
        
        if current_quantity <= 0:
            stockout_days += (end_date - current_date).days
        
        return stockout_days