from django.core.management.base import BaseCommand
from django.db.models import Avg, Count, Sum, F, ExpressionWrapper, fields
from django.db.models.functions import ExtractDay
from django.utils import timezone
from inventory.models import Supplier, PurchaseOrder, Product
import csv
from datetime import timedelta

class Command(BaseCommand):
    help = 'Analyze supplier performance and generate reports'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=90,
            help='Number of days to analyze',
        )
        parser.add_argument(
            '--min-orders',
            type=int,
            default=5,
            help='Minimum number of orders for reliable metrics',
        )
        parser.add_argument(
            '--export',
            action='store_true',
            help='Export analysis to CSV',
        )

    def handle(self, *args, **options):
        try:
            days = options['days']
            min_orders = options['min_orders']
            start_date = timezone.now() - timedelta(days=days)
            
            self.stdout.write(f'Analyzing supplier performance over the last {days} days...')
            
            # Analyze each supplier
            analysis_results = []
            for supplier in Supplier.objects.filter(is_active=True):
                metrics = self.analyze_supplier(supplier, start_date, min_orders)
                if metrics:
                    analysis_results.append(metrics)
                    self.print_supplier_metrics(metrics)
            
            # Export if requested
            if options['export'] and analysis_results:
                self.export_analysis(analysis_results)
            
            self.stdout.write(self.style.SUCCESS('Supplier analysis completed successfully'))
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error analyzing suppliers: {str(e)}')
            )

    def analyze_supplier(self, supplier, start_date, min_orders):
        """Analyze individual supplier performance"""
        # Get completed orders for the period
        completed_orders = PurchaseOrder.objects.filter(
            supplier=supplier,
            status='COMPLETED',
            order_date__gte=start_date
        )
        
        order_count = completed_orders.count()
        if order_count < min_orders:
            return None
            
        # Calculate metrics
        metrics = {
            'supplier_name': supplier.name,
            'supplier_id': supplier.id,
            'order_count': order_count,
            'total_value': completed_orders.aggregate(
                total=Sum('total')
            )['total'] or 0,
        }
        
        # Calculate lead time metrics
        lead_time_expr = ExpressionWrapper(
            F('updated_at') - F('order_date'),
            output_field=fields.DurationField()
        )
        lead_time_metrics = completed_orders.aggregate(
            avg_lead_time=Avg(ExtractDay(lead_time_expr)),
            total_late_orders=Count('id', filter=F('updated_at') > F('expected_delivery'))
        )
        
        metrics.update({
            'avg_lead_time': round(lead_time_metrics['avg_lead_time'] or 0, 1),
            'late_orders': lead_time_metrics['total_late_orders'],
            'on_time_delivery_rate': round(
                (order_count - lead_time_metrics['total_late_orders']) / order_count * 100,
                1
            )
        })
        
        # Calculate quality metrics
        return_transactions = supplier.products.filter(
            transactions__transaction_type='RETURN',
            transactions__transaction_date__gte=start_date
        ).count()
        
        metrics['return_rate'] = round(
            (return_transactions / order_count) * 100 if order_count > 0 else 0,
            1
        )
        
        # Calculate pricing stability
        price_changes = Product.objects.filter(
            supplier=supplier,
            updated_at__gte=start_date
        ).exclude(
            price=F('price')
        ).count()
        
        metrics['price_changes'] = price_changes
        
        return metrics

    def print_supplier_metrics(self, metrics):
        """Print supplier metrics to console"""
        self.stdout.write('\n' + '=' * 50)
        self.stdout.write(f"Supplier: {metrics['supplier_name']}")
        self.stdout.write('-' * 50)
        self.stdout.write(f"Orders Completed: {metrics['order_count']}")
        self.stdout.write(f"Total Value: ${metrics['total_value']:,.2f}")
        self.stdout.write(f"Average Lead Time: {metrics['avg_lead_time']} days")
        self.stdout.write(f"On-Time Delivery Rate: {metrics['on_time_delivery_rate']}%")
        self.stdout.write(f"Return Rate: {metrics['return_rate']}%")
        self.stdout.write(f"Price Changes: {metrics['price_changes']}")

    def export_analysis(self, results):
        """Export analysis results to CSV"""
        filename = f'supplier_analysis_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv'
        
        with open(filename, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([
                'Supplier ID',
                'Supplier Name',
                'Orders Completed',
                'Total Value',
                'Avg Lead Time (days)',
                'On-Time Delivery Rate (%)',
                'Return Rate (%)',
                'Price Changes'
            ])
            
            for metrics in results:
                writer.writerow([
                    metrics['supplier_id'],
                    metrics['supplier_name'],
                    metrics['order_count'],
                    metrics['total_value'],
                    metrics['avg_lead_time'],
                    metrics['on_time_delivery_rate'],
                    metrics['return_rate'],
                    metrics['price_changes']
                ])
        
        self.stdout.write(f'Analysis exported to {filename}')