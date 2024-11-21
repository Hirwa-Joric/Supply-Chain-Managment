from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import F, Sum, Q
from inventory.models import Product, InventoryTransaction, PurchaseOrder
from inventory.utils import calculate_reorder_quantities
import csv
from datetime import datetime, timedelta

class Command(BaseCommand):
    help = 'Update stock levels and generate inventory reports'

    def add_arguments(self, parser):
        parser.add_argument(
            '--export',
            action='store_true',
            help='Export stock levels to CSV',
        )
        parser.add_argument(
            '--check-reorder',
            action='store_true',
            help='Check and suggest reorder quantities',
        )
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Number of days for historical analysis',
        )

    def handle(self, *args, **options):
        try:
            self.stdout.write('Starting stock level update...')
            
            # Get current time for reporting
            current_time = timezone.now()
            
            # Update all product quantities based on transactions
            updated_products = self.update_stock_levels()
            self.stdout.write(f'Updated {updated_products} product stock levels')
            
            # Check for low stock items
            low_stock = Product.objects.filter(quantity__lte=F('minimum_stock'))
            self.stdout.write(f'Found {low_stock.count()} products with low stock')
            
            # Generate reorder suggestions if requested
            if options['check_reorder']:
                reorder_suggestions = calculate_reorder_quantities()
                self.stdout.write('\nReorder Suggestions:')
                for suggestion in reorder_suggestions:
                    self.stdout.write(
                        f"- {suggestion['product'].name}: "
                        f"Order {suggestion['suggested_reorder']} units "
                        f"(Current: {suggestion['current_quantity']}, "
                        f"Daily Usage: {suggestion['avg_daily_usage']:.2f})"
                    )
            
            # Export to CSV if requested
            if options['export']:
                self.export_stock_report(current_time)
            
            self.stdout.write(self.style.SUCCESS('Stock level update completed successfully'))
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error updating stock levels: {str(e)}')
            )

    def update_stock_levels(self):
        """Update all product stock levels based on transactions"""
        updated_count = 0
        
        for product in Product.objects.all():
            # Calculate total quantity from transactions
            transactions_total = InventoryTransaction.objects.filter(
                product=product
            ).aggregate(
                total=Sum(
                    Case(
                        When(transaction_type='PURCHASE', then='quantity'),
                        When(transaction_type='SALE', then=-F('quantity')),
                        default='quantity',
                        output_field=IntegerField(),
                    )
                )
            )['total'] or 0
            
            # Update product quantity if different
            if product.quantity != transactions_total:
                product.quantity = transactions_total
                product.save()
                updated_count += 1
        
        return updated_count

    def export_stock_report(self, timestamp):
        """Export current stock levels to CSV"""
        filename = f'stock_levels_{timestamp.strftime("%Y%m%d_%H%M%S")}.csv'
        
        with open(filename, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([
                'SKU',
                'Product Name',
                'Category',
                'Current Stock',
                'Minimum Stock',
                'Reorder Point',
                'Stock Value',
                'Status',
                'Last Updated'
            ])
            
            for product in Product.objects.select_related('category'):
                writer.writerow([
                    product.sku,
                    product.name,
                    product.category.name if product.category else 'N/A',
                    product.quantity,
                    product.minimum_stock,
                    product.reorder_point,
                    product.stock_value,
                    product.stock_status,
                    product.updated_at.strftime("%Y-%m-%d %H:%M:%S")
                ])
        
        self.stdout.write(f'Stock report exported to {filename}')