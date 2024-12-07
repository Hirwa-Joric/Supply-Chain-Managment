from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from inventory.models import Supplier, Product, Warehouse, Order, OrderItem
from django.utils import timezone
import random
from datetime import timedelta

class Command(BaseCommand):
    help = 'Populates the database with sample data'

    def handle(self, *args, **kwargs):
        # Create suppliers
        suppliers = [
            {'name': 'TechPro Solutions', 'contact_name': 'John Smith', 'email': 'john@techpro.com', 'phone': '123-456-7890'},
            {'name': 'Global Electronics', 'contact_name': 'Sarah Johnson', 'email': 'sarah@globalelec.com', 'phone': '234-567-8901'},
            {'name': 'Quality Parts Inc', 'contact_name': 'Mike Brown', 'email': 'mike@qualityparts.com', 'phone': '345-678-9012'},
        ]
        
        for supplier_data in suppliers:
            Supplier.objects.get_or_create(**supplier_data)
        
        # Create warehouses
        warehouses = [
            {'name': 'North Distribution Center', 'location': 'New York', 'capacity': 10000},
            {'name': 'South Warehouse', 'location': 'Miami', 'capacity': 8000},
            {'name': 'West Coast Facility', 'location': 'Los Angeles', 'capacity': 12000},
        ]
        
        for warehouse_data in warehouses:
            Warehouse.objects.get_or_create(**warehouse_data)
        
        # Create products
        products = [
            {'name': 'Laptop Pro X1', 'description': 'High-performance laptop', 'price': 999.99, 'sku': 'LP001'},
            {'name': 'Smartphone Y2', 'description': '5G smartphone', 'price': 699.99, 'sku': 'SP001'},
            {'name': 'Tablet Z3', 'description': '10-inch tablet', 'price': 499.99, 'sku': 'TB001'},
            {'name': 'Wireless Earbuds', 'description': 'Bluetooth earbuds', 'price': 149.99, 'sku': 'WE001'},
            {'name': 'Smart Watch', 'description': 'Fitness tracker', 'price': 299.99, 'sku': 'SW001'},
        ]
        
        for product_data in products:
            supplier = Supplier.objects.order_by('?').first()
            product_data['supplier'] = supplier
            Product.objects.get_or_create(**product_data)
        
        # Create orders with random data
        statuses = ['pending', 'processing', 'shipped', 'delivered']
        
        # Create 50 orders over the last 30 days
        for _ in range(50):
            order_date = timezone.now() - timedelta(days=random.randint(0, 30))
            status = random.choice(statuses)
            delivery_issues = random.random() < 0.1  # 10% chance of delivery issues
            
            order = Order.objects.create(
                order_date=order_date,
                status=status,
                delivery_issues=delivery_issues
            )
            
            # Add 1-5 random products to each order
            for _ in range(random.randint(1, 5)):
                product = Product.objects.order_by('?').first()
                quantity = random.randint(1, 5)
                
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=quantity,
                    price=product.price
                )
        
        self.stdout.write(self.style.SUCCESS('Successfully populated sample data'))
