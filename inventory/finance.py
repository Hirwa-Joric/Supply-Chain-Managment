from decimal import Decimal, ROUND_HALF_UP
from django.db.models import Sum, F, ExpressionWrapper, DecimalField, Q
from django.utils import timezone
from datetime import timedelta
from .models import Product, InventoryTransaction, PurchaseOrder

class InventoryFinance:
    @staticmethod
    def calculate_inventory_value():
        """Calculate total current inventory value"""
        return Product.objects.aggregate(
            total_value=Sum(
                F('quantity') * F('price'),
                output_field=DecimalField(max_digits=10, decimal_places=2)
            )
        )['total_value'] or Decimal('0.00')

    @staticmethod
    def calculate_avg_cost(product, days=90):
        """Calculate average cost for a product over period"""
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        purchases = InventoryTransaction.objects.filter(
            product=product,
            transaction_type='PURCHASE',
            transaction_date__range=[start_date, end_date]
        )
        
        if not purchases.exists():
            return product.price
            
        total_cost = Decimal('0.00')
        total_quantity = 0
        
        for purchase in purchases:
            total_cost += purchase.quantity * purchase.unit_price
            total_quantity += purchase.quantity
            
        if total_quantity > 0:
            return (total_cost / total_quantity).quantize(
                Decimal('0.01'),
                rounding=ROUND_HALF_UP
            )
        return product.price

    @staticmethod
    def calculate_profit_margins(days=30):
        """Calculate profit margins for products"""
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        products = Product.objects.filter(
            transactions__transaction_date__range=[start_date, end_date]
        ).distinct()
        
        margins = []
        for product in products:
            sales = InventoryTransaction.objects.filter(
                product=product,
                transaction_type='SALE',
                transaction_date__range=[start_date, end_date]
            )
            
            if not sales.exists():
                continue
                
            avg_cost = InventoryFinance.calculate_avg_cost(product)
            total_revenue = Decimal('0.00')
            total_cost = Decimal('0.00')
            
            for sale in sales:
                total_revenue += sale.quantity * sale.unit_price
                total_cost += sale.quantity * avg_cost
            
            if total_revenue > 0:
                margin = ((total_revenue - total_cost) / total_revenue * 100).quantize(
                    Decimal('0.1'),
                    rounding=ROUND_HALF_UP
                )
            else:
                margin = Decimal('0.0')
                
            margins.append({
                'product': product,
                'revenue': total_revenue,
                'cost': total_cost,
                'margin': margin
            })
            
        return margins

    @staticmethod
    def calculate_carrying_costs():
        """Calculate inventory carrying costs"""
        CARRYING_COST_RATE = Decimal('0.25')  # 25% annual carrying cost rate
        
        inventory_value = InventoryFinance.calculate_inventory_value()
        annual_carrying_cost = inventory_value * CARRYING_COST_RATE
        
        return {
            'inventory_value': inventory_value,
            'annual_rate': CARRYING_COST_RATE,
            'annual_cost': annual_carrying_cost,
            'monthly_cost': annual_carrying_cost / 12
        }

    @staticmethod
    def calculate_turnover_metrics():
        """Calculate inventory turnover metrics"""
        end_date = timezone.now()
        start_date = end_date - timedelta(days=365)
        
        # Calculate COGS
        total_sales = InventoryTransaction.objects.filter(
            transaction_type='SALE',
            transaction_date__range=[start_date, end_date]
        ).aggregate(
            total=Sum(F('quantity') * F('unit_price'))
        )['total'] or Decimal('0.00')
        
        avg_inventory = Product.objects.aggregate(
            total=Sum(F('quantity') * F('price'))
        )['total'] or Decimal('0.00')
        
        if avg_inventory > 0:
            turnover_ratio = (total_sales / avg_inventory).quantize(
                Decimal('0.1'),
                rounding=ROUND_HALF_UP
            )
            days_inventory = (Decimal('365') / turnover_ratio).quantize(
                Decimal('0.1'),
                rounding=ROUND_HALF_UP
            )
        else:
            turnover_ratio = Decimal('0.0')
            days_inventory = Decimal('0.0')
            
        return {
            'turnover_ratio': turnover_ratio,
            'days_inventory': days_inventory,
            'total_sales': total_sales,
            'avg_inventory': avg_inventory
        }

    @staticmethod
    def generate_financial_summary(days=30):
        """Generate comprehensive financial summary"""
        summary = {
            'inventory_value': InventoryFinance.calculate_inventory_value(),
            'carrying_costs': InventoryFinance.calculate_carrying_costs(),
            'turnover_metrics': InventoryFinance.calculate_turnover_metrics(),
            'profit_margins': InventoryFinance.calculate_profit_margins(days),
        }
        
        # Calculate additional metrics
        total_margin = Decimal('0.00')
        total_revenue = Decimal('0.00')
        
        for product in summary['profit_margins']:
            total_margin += product['revenue'] - product['cost']
            total_revenue += product['revenue']
            
        summary['overall_margin'] = (
            (total_margin / total_revenue * 100).quantize(Decimal('0.1'))
            if total_revenue > 0 else Decimal('0.0')
        )
        
        return summary