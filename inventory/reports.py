import csv
import xlsxwriter
from io import BytesIO
from datetime import datetime, timedelta
from decimal import Decimal
from django.db.models import Sum, Count, F, Q, ExpressionWrapper, DecimalField
from django.db.models.functions import TruncDate, ExtractMonth
from django.utils import timezone
from .models import Product, Supplier, PurchaseOrder, InventoryTransaction
from .finance import InventoryFinance

class ReportGenerator:
    @staticmethod
    def generate_stock_report(format='csv'):
        """Generate current stock levels report"""
        products = Product.objects.select_related('category', 'supplier').all()
        
        headers = [
            'SKU',
            'Product Name',
            'Category',
            'Current Stock',
            'Minimum Stock',
            'Reorder Point',
            'Unit Price',
            'Stock Value',
            'Supplier',
            'Status'
        ]
        
        data = []
        for product in products:
            data.append([
                product.sku,
                product.name,
                product.category.name if product.category else 'N/A',
                product.quantity,
                product.minimum_stock,
                product.reorder_point,
                float(product.price),
                float(product.stock_value),
                product.supplier.name if product.supplier else 'N/A',
                product.stock_status
            ])
            
        return ReportGenerator._format_report(headers, data, 'stock_levels', format)

    @staticmethod
    def generate_movement_report(start_date=None, end_date=None, format='csv'):
        """Generate inventory movement report"""
        if not start_date:
            start_date = timezone.now() - timedelta(days=30)
        if not end_date:
            end_date = timezone.now()
            
        movements = InventoryTransaction.objects.filter(
            transaction_date__range=[start_date, end_date]
        ).select_related('product', 'created_by')
        
        headers = [
            'Date',
            'Product SKU',
            'Product Name',
            'Transaction Type',
            'Quantity',
            'Unit Price',
            'Total Value',
            'Reference',
            'Created By'
        ]
        
        data = []
        for movement in movements:
            data.append([
                movement.transaction_date.strftime('%Y-%m-%d %H:%M'),
                movement.product.sku,
                movement.product.name,
                movement.get_transaction_type_display(),
                movement.quantity,
                float(movement.unit_price),
                float(movement.quantity * movement.unit_price),
                movement.reference_number or 'N/A',
                movement.created_by.username if movement.created_by else 'System'
            ])
            
        return ReportGenerator._format_report(headers, data, 'inventory_movements', format)

    @staticmethod
    def generate_supplier_performance_report(days=90, format='csv'):
        """Generate supplier performance report"""
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        suppliers = Supplier.objects.filter(is_active=True)
        
        headers = [
            'Supplier Name',
            'Total Orders',
            'Order Value',
            'On-Time Delivery Rate',
            'Average Lead Time',
            'Quality Issues',
            'Performance Rating'
        ]
        
        data = []
        for supplier in suppliers:
            orders = PurchaseOrder.objects.filter(
                supplier=supplier,
                order_date__range=[start_date, end_date]
            )
            
            total_orders = orders.count()
            if total_orders == 0:
                continue
                
            on_time = orders.filter(
                status='COMPLETED',
                updated_at__lte=F('expected_delivery')
            ).count()
            
            on_time_rate = (on_time / total_orders * 100) if total_orders > 0 else 0
            
            lead_time = orders.filter(
                status='COMPLETED'
            ).aggregate(
                avg_lead_time=Avg(F('updated_at') - F('order_date'))
            )['avg_lead_time']
            
            quality_issues = supplier.products.filter(
                transactions__transaction_type='RETURN',
                transactions__transaction_date__range=[start_date, end_date]
            ).count()
            
            data.append([
                supplier.name,
                total_orders,
                float(orders.aggregate(total=Sum('total'))['total'] or 0),
                round(on_time_rate, 1),
                lead_time.days if lead_time else 'N/A',
                quality_issues,
                ReportGenerator._calculate_performance_rating(on_time_rate, quality_issues)
            ])
            
        return ReportGenerator._format_report(headers, data, 'supplier_performance', format)

    @staticmethod
    def generate_financial_report(days=30, format='csv'):
        """Generate financial performance report"""
        finance = InventoryFinance()
        summary = finance.generate_financial_summary(days)
        
        # Overall metrics
        headers_overall = [
            'Metric',
            'Value'
        ]
        
        data_overall = [
            ['Total Inventory Value', float(summary['inventory_value'])],
            ['Annual Carrying Cost', float(summary['carrying_costs']['annual_cost'])],
            ['Monthly Carrying Cost', float(summary['carrying_costs']['monthly_cost'])],
            ['Inventory Turnover Ratio', float(summary['turnover_metrics']['turnover_ratio'])],
            ['Days Inventory Outstanding', float(summary['turnover_metrics']['days_inventory'])],
            ['Overall Profit Margin (%)', float(summary['overall_margin'])]
        ]
        
        # Product-specific metrics
        headers_products = [
            'Product SKU',
            'Product Name',
            'Revenue',
            'Cost',
            'Margin (%)'
        ]
        
        data_products = [
            [
                product['product'].sku,
                product['product'].name,
                float(product['revenue']),
                float(product['cost']),
                float(product['margin'])
            ]
            for product in summary['profit_margins']
        ]
        
        if format == 'xlsx':
            return ReportGenerator._format_multi_sheet_excel(
                [
                    ('Overall Metrics', headers_overall, data_overall),
                    ('Product Metrics', headers_products, data_products)
                ],
                'financial_report'
            )
        else:
            # For CSV, combine both reports with a separator
            return ReportGenerator._format_report(
                headers_overall,
                data_overall + [['', '']] + [headers_products] + data_products,
                'financial_report',
                format
            )

    @staticmethod
    def _calculate_performance_rating(on_time_rate, quality_issues):
        """Calculate supplier performance rating"""
        if on_time_rate >= 95 and quality_issues == 0:
            return 'Excellent'
        elif on_time_rate >= 85 and quality_issues <= 2:
            return 'Good'
        else:
            return 'Needs Improvement'

    @staticmethod
    def _format_report(headers, data, report_name, format):
        """Format report in specified format"""
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{report_name}_{timestamp}"
        
        if format == 'csv':
            output = BytesIO()
            writer = csv.writer(output)
            writer.writerow(headers)
            writer.writerows(data)
            output.seek(0)
            return {
                'filename': f'{filename}.csv',
                'content': output,
                'content_type': 'text/csv'
            }
            
        elif format == 'xlsx':
            output = BytesIO()
            workbook = xlsxwriter.Workbook(output)
            worksheet = workbook.add_worksheet()
            
            # Add headers
            for col, header in enumerate(headers):
                worksheet.write(0, col, header)
                
            # Add data
            for row_idx, row in enumerate(data, start=1):
                for col_idx, value in enumerate(row):
                    worksheet.write(row_idx, col_idx, value)
                    
            workbook.close()
            output.seek(0)
            return {
                'filename': f'{filename}.xlsx',
                'content': output,
                'content_type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            }

    @staticmethod
    def _format_multi_sheet_excel(sheets, report_name):
        """Format multi-sheet Excel report"""
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{report_name}_{timestamp}.xlsx"
        
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output)
        
        # Add each sheet
        for sheet_name, headers, data in sheets:
            worksheet = workbook.add_worksheet(sheet_name)
            
            # Add headers
            for col, header in enumerate(headers):
                worksheet.write(0, col, header)
                
            # Add data
            for row_idx, row in enumerate(data, start=1):
                for col_idx, value in enumerate(row):
                    worksheet.write(row_idx, col_idx, value)
        
        workbook.close()
        output.seek(0)
        return {
            'filename': filename,
            'content': output,
            'content_type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        }