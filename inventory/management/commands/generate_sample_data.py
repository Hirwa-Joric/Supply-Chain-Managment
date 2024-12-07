from django.core.management.base import BaseCommand
from django.utils import timezone
from inventory.models import Product, Supplier, PurchaseOrder, PurchaseOrderItem, Order, OrderItem
from decimal import Decimal
import random
from datetime import datetime, timedelta
import string

class Command(BaseCommand):
    help = 'Generates sample data for supply chain analytics'

    def generate_dates(self, start_year=2017):
        end_date = timezone.now()
        start_date = timezone.datetime(start_year, 1, 1, tzinfo=timezone.get_current_timezone())
        return start_date, end_date

    def generate_suppliers(self):
        supplier_names = [
            "Global Supply Co.", "Tech Components Ltd.", "Industrial Parts Inc.",
            "Quality Materials Corp.", "Precision Products", "Reliable Distributors",
            "Prime Manufacturing", "Elite Supply Chain", "Superior Components",
            "Advanced Materials Inc."
        ]
        
        suppliers = []
        for name in supplier_names:
            supplier, _ = Supplier.objects.get_or_create(
                name=name,
                defaults={
                    'contact_person': f"{name.split()[0]} Manager",
                    'email': f"contact@{name.lower().replace(' ', '')}.com",
                    'phone': f"+1-555-{random.randint(1000, 9999)}",
                    'address': f"{random.randint(100, 999)} Business Ave, Suite {random.randint(100, 999)}",
                    'rating': Decimal(str(round(random.uniform(3.5, 5.0), 2)))
                }
            )
            suppliers.append(supplier)
        return suppliers

    def generate_random_sku(self):
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

    def generate_products(self, suppliers):
        categories = ['electronics', 'clothing', 'food', 'accessories']
        products_data = []
        
        for category in categories:
            for i in range(5):
                name = f"{category.title()} Item {i+1}"
                sku = self.generate_random_sku()
                
                product, created = Product.objects.get_or_create(
                    name=name,
                    defaults={
                        'sku': sku,
                        'description': f"High-quality {category.lower()} item",
                        'category': category,
                        'unit_price': Decimal(str(round(random.uniform(50, 500), 2))),
                        'stock_quantity': random.randint(100, 1000),
                        'reorder_point': random.randint(20, 50),
                        'supplier': random.choice(suppliers)
                    }
                )
                products_data.append(product)

        return products_data

    def update_stock_levels(self, products, current_date, seasonal_multiplier, years_from_start):
        """Update stock levels based on seasonal demand and management improvements"""
        for product in products:
            # Base chance of stock-out increases in high-demand seasons
            base_stockout_chance = 0.05  # 5% base chance
            
            # Increase chance during high-demand seasons
            seasonal_chance = base_stockout_chance * (seasonal_multiplier ** 2)
            
            # Reduce chance based on years (better inventory management)
            final_chance = seasonal_chance * (0.7 ** years_from_start)  # 30% improvement per year
            
            if random.random() < final_chance:
                product.stock_quantity = 0
            else:
                # Normal stock level with seasonal variation
                base_stock = random.randint(50, 500)
                seasonal_stock = int(base_stock * (1 / seasonal_multiplier))  # Lower stock in high seasons
                product.stock_quantity = max(0, seasonal_stock)
            
            # Update the timestamp
            product.updated_at = current_date
            product.save()

    def generate_purchase_orders(self, start_date, end_date, products):
        suppliers = list(Supplier.objects.all())
        current_date = start_date
        
        # Create seasonal patterns
        seasonal_multipliers = {
            1: 0.8,  # January (post-holiday slowdown)
            2: 0.7,  # February
            3: 0.9,  # March
            4: 1.0,  # April
            5: 1.1,  # May
            6: 1.2,  # June
            7: 1.3,  # July
            8: 1.4,  # August (back to school)
            9: 1.2,  # September
            10: 1.3, # October
            11: 1.5, # November (holiday season)
            12: 1.8  # December (peak)
        }
        
        # Year-over-year growth
        base_yearly_growth = 1.15  # 15% yearly growth
        
        while current_date <= end_date:
            # Calculate yearly multiplier based on how many years from start
            years_from_start = (current_date.year - start_date.year)
            yearly_multiplier = base_yearly_growth ** years_from_start
            
            # Calculate seasonal multiplier
            seasonal_multiplier = seasonal_multipliers[current_date.month]
            
            # Update stock levels more frequently in recent years
            if current_date.day in [1, 15] or (years_from_start >= 2 and current_date.day in [7, 22]):
                self.update_stock_levels(list(Product.objects.all()), current_date, seasonal_multiplier, years_from_start)
            
            # Calculate final number of orders for this period
            base_orders = 3  # base number of orders per period
            num_orders = max(1, int(base_orders * yearly_multiplier * seasonal_multiplier))
            
            for _ in range(num_orders):
                supplier = random.choice(suppliers)
                delivery_days = random.randint(3, 15)
                expected_delivery = current_date + timedelta(days=delivery_days)
                
                # Simulate improved delivery performance over time
                late_delivery_chance = max(0.05, 0.15 - (years_from_start * 0.02))  # Improves by 2% each year
                if random.random() < late_delivery_chance:
                    actual_delivery = expected_delivery + timedelta(days=random.randint(1, 5))
                    status = 'delivered'
                else:
                    actual_delivery = expected_delivery - timedelta(days=random.randint(0, 2))
                    status = random.choice(['pending', 'approved', 'shipped', 'delivered'])

                po = PurchaseOrder.objects.create(
                    supplier=supplier,
                    order_date=current_date,
                    expected_delivery=expected_delivery,
                    actual_delivery=actual_delivery if status == 'delivered' else None,
                    status=status,
                    total_amount=Decimal('0')
                )

                # Add items to purchase order with seasonal variations
                total_amount = Decimal('0')
                num_items = random.randint(2, 6)  # More items per order
                for _ in range(num_items):
                    product = random.choice(products)
                    
                    # Seasonal quantity variations
                    base_quantity = random.randint(20, 200)
                    quantity = int(base_quantity * seasonal_multiplier)
                    
                    # Price variations with slight inflation
                    inflation_factor = 1 + (years_from_start * 0.03)  # 3% yearly inflation
                    base_price = product.unit_price * Decimal(str(inflation_factor))
                    unit_price = base_price * Decimal(str(round(random.uniform(0.95, 1.05), 2)))
                    
                    total_price = Decimal(str(quantity)) * unit_price
                    total_amount += total_price
                    
                    PurchaseOrderItem.objects.create(
                        purchase_order=po,
                        product=product,
                        quantity=quantity,
                        unit_price=unit_price,
                        total_price=total_price
                    )
                
                po.total_amount = total_amount
                po.save()

            # Progress time by 2-5 days in earlier years, 1-3 days in recent years
            day_increment = random.randint(2, 5) if years_from_start < 3 else random.randint(1, 3)
            current_date += timedelta(days=day_increment)

    def handle(self, *args, **kwargs):
        start_date, end_date = self.generate_dates()
        
        self.stdout.write('Generating suppliers...')
        suppliers = self.generate_suppliers()
        
        self.stdout.write('Generating products...')
        products = self.generate_products(suppliers)
        
        self.stdout.write('Generating purchase orders...')
        self.generate_purchase_orders(start_date, end_date, products)
        
        self.stdout.write(self.style.SUCCESS('Successfully generated sample data'))
