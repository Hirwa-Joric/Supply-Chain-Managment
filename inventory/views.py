from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import (
    Sum, Count, F, Q, FloatField, DecimalField,
    ExpressionWrapper, Avg, Case, When, Value
)
from django.db.models.functions import TruncMonth, Cast
from django.utils import timezone
from datetime import timedelta
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
import random
from .models import (
    Supplier, Product, PurchaseOrder, PurchaseOrderItem,
    Warehouse, InventoryMovement, Order
)
from .forms import (
    SupplierForm, ProductForm, PurchaseOrderForm,
    WarehouseForm, InventoryMovementForm, OrderForm
)
from decimal import Decimal

def landing_page(request):
    if request.user.is_authenticated:
        return redirect('inventory:dashboard')
    return render(request, 'inventory/landing.html')

@login_required
def dashboard(request):
    # Get counts for dashboard stats
    total_products = Product.objects.count()
    total_suppliers = Supplier.objects.count()
    pending_orders = Order.objects.filter(status='pending').count()
    low_stock_count = Product.objects.filter(stock_quantity__lte=F('reorder_point')).count()

    # Get recent activities
    recent_activities = []
    
    # Recent orders
    recent_orders = Order.objects.order_by('-created_at')[:5]
    for order in recent_orders:
        recent_activities.append({
            'type': 'order',
            'description': f'New order created with {order.items.count()} items',
            'timestamp': order.created_at
        })
    
    # Recent products
    recent_products = Product.objects.order_by('-created_at')[:5]
    for product in recent_products:
        recent_activities.append({
            'type': 'product',
            'description': f'New product added: {product.name}',
            'timestamp': product.created_at
        })
    
    # Recent suppliers
    recent_suppliers = Supplier.objects.order_by('-created_at')[:5]
    for supplier in recent_suppliers:
        recent_activities.append({
            'type': 'supplier',
            'description': f'New supplier added: {supplier.name}',
            'timestamp': supplier.created_at
        })
    
    # Sort activities by timestamp
    recent_activities.sort(key=lambda x: x['timestamp'], reverse=True)
    recent_activities = recent_activities[:10]  # Show only 10 most recent activities

    context = {
        'total_products': total_products,
        'total_suppliers': total_suppliers,
        'pending_orders': pending_orders,
        'low_stock_count': low_stock_count,
        'recent_activities': recent_activities,
    }
    
    return render(request, 'inventory/dashboard.html', context)

@login_required
def low_stock(request):
    low_stock_items = Product.objects.filter(stock_quantity__lte=F('reorder_point'))
    return render(request, 'inventory/low_stock.html', {'products': low_stock_items})

@login_required
def order_list(request):
    orders = Order.objects.all().order_by('-created_at')
    return render(request, 'inventory/order_list.html', {'orders': orders})

@login_required
def order_create(request):
    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            order = form.save()
            messages.success(request, 'Order created successfully.')
            return redirect('inventory:order_list')
    else:
        form = OrderForm()
    return render(request, 'inventory/order_form.html', {'form': form})

@login_required
def order_detail(request, pk):
    order = get_object_or_404(Order, pk=pk)
    return render(request, 'inventory/order_detail.html', {'order': order})

@login_required
def order_edit(request, pk):
    order = get_object_or_404(Order, pk=pk)
    if request.method == 'POST':
        form = OrderForm(request.POST, instance=order)
        if form.is_valid():
            order = form.save()
            messages.success(request, 'Order updated successfully.')
            return redirect('inventory:order_detail', pk=order.pk)
    else:
        form = OrderForm(instance=order)
    return render(request, 'inventory/order_form.html', {'form': form})

class AnalyticsView(LoginRequiredMixin, TemplateView):
    template_name = 'inventory/analytics.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Calculate total revenue from all orders
        total_revenue = PurchaseOrder.objects.aggregate(
            total=Sum('total_amount')
        )['total'] or 0
        
        # Calculate fulfillment rate (delivered orders / total orders)
        total_orders = PurchaseOrder.objects.count()
        fulfilled_orders = PurchaseOrder.objects.filter(status='delivered').count()
        fulfillment_rate = (fulfilled_orders / total_orders * 100) if total_orders > 0 else 0
        
        # Calculate average order value
        avg_order_value = total_revenue / total_orders if total_orders > 0 else 0
        
        # Get actual categories and their stock levels
        categories = list(set(Product.objects.values_list('category', flat=True)))
        if not categories:  # If no products exist yet
            categories = [choice[0] for choice in Product.CATEGORY_CHOICES]
        
        stock_levels = []
        for category in categories:
            stock = Product.objects.filter(category=category).aggregate(
                total_stock=Sum('stock_quantity')
            )['total_stock'] or 0
            stock_levels.append(stock)
        
        # Get order trends for last 6 months
        six_months_ago = timezone.now() - timedelta(days=180)
        order_trends = PurchaseOrder.objects.filter(
            order_date__gte=six_months_ago
        ).annotate(
            month=TruncMonth('order_date')
        ).values('month').annotate(
            count=Count('id')
        ).order_by('month')
        
        order_dates = []
        order_counts = []
        if order_trends:
            for trend in order_trends:
                order_dates.append(trend['month'].strftime('%b'))
                order_counts.append(trend['count'])
        else:
            # If no orders exist, show last 6 months with zero counts
            for i in range(6):
                month = timezone.now() - timedelta(days=30 * i)
                order_dates.insert(0, month.strftime('%b'))
                order_counts.insert(0, 0)
        
        # Get category performance over last 5 months
        five_months_ago = timezone.now() - timedelta(days=150)
        category_data = {}
        for category in categories[:2]:  # Get top 2 categories
            monthly_sales = PurchaseOrderItem.objects.filter(
                product__category=category,
                purchase_order__order_date__gte=five_months_ago
            ).annotate(
                month=TruncMonth('purchase_order__order_date')
            ).values('month').annotate(
                total=Sum('total_price')
            ).order_by('month')
            
            # If no sales data exists, create empty dataset
            if not monthly_sales:
                sales_data = [0] * 5
            else:
                sales_data = [sale['total'] or 0 for sale in monthly_sales]
            
            category_data[category] = {
                'data': sales_data,
                'borderColor': f'rgb({random.randint(0, 255)}, {random.randint(0, 255)}, {random.randint(0, 255)})',
                'fill': True
            }
        
        # Get top suppliers with actual metrics
        top_suppliers = Supplier.objects.annotate(
            total_orders=Count('purchaseorder'),
            on_time_orders=Count('purchaseorder', filter=Q(
                purchaseorder__actual_delivery__lte=F('purchaseorder__expected_delivery')
            ))
        ).annotate(
            on_time_delivery=ExpressionWrapper(
                100.0 * F('on_time_orders') / Case(
                    When(total_orders=0, then=1),
                    default=F('total_orders')
                ),
                output_field=FloatField()
            )
        ).order_by('-total_orders')[:3]
        
        top_suppliers_data = []
        for supplier in top_suppliers:
            top_suppliers_data.append({
                'name': supplier.name,
                'on_time_delivery': round(supplier.on_time_delivery, 1),
                'quality_score': round(supplier.rating * 20, 1),  # Convert 0-5 rating to percentage
                'cost_efficiency': round(
                    PurchaseOrderItem.objects.filter(
                        purchase_order__supplier=supplier
                    ).aggregate(
                        efficiency=Avg(F('total_price') / F('quantity'))
                    )['efficiency'] or 90, 1
                )
            })
        
        # If no suppliers exist, provide empty data
        if not top_suppliers_data:
            top_suppliers_data = [
                {'name': 'No suppliers yet', 'on_time_delivery': 0, 'quality_score': 0, 'cost_efficiency': 0}
            ]
        
        # Calculate cost components
        total_orders = PurchaseOrder.objects.count()
        total_cost = PurchaseOrder.objects.aggregate(
            total=Sum('total_amount')
        )['total'] or 0
        
        # Calculate various cost components with proper type casting
        cost_components = {
            'risk': PurchaseOrder.objects.filter(status='cancelled').aggregate(
                risk_cost=Cast(Sum('total_amount'), FloatField())
            )['risk_cost'] or 0,
            
            'freight': PurchaseOrderItem.objects.filter(
                purchase_order__status='delivered'
            ).aggregate(
                freight_cost=ExpressionWrapper(
                    Sum('total_price') * Value(Decimal('0.10')),
                    output_field=DecimalField(max_digits=10, decimal_places=2)
                )
            )['freight_cost'] or Decimal('0'),
            
            'service': PurchaseOrderItem.objects.filter(
                purchase_order__status='delivered'
            ).aggregate(
                service_cost=ExpressionWrapper(
                    Sum('total_price') * Value(Decimal('0.05')),
                    output_field=DecimalField(max_digits=10, decimal_places=2)
                )
            )['service_cost'] or Decimal('0'),
            
            'storage': Product.objects.aggregate(
                storage_cost=ExpressionWrapper(
                    Sum(F('stock_quantity') * F('unit_price')) * Value(Decimal('0.02')),
                    output_field=DecimalField(max_digits=10, decimal_places=2)
                )
            )['storage_cost'] or Decimal('0'),
            
            'admin': (total_cost * Decimal('0.03')) if total_cost else Decimal('0')
        }
        
        # Calculate percentages
        total_costs = sum(cost_components.values())
        cost_percentages = {
            key: round((value / total_costs * 100) if total_costs else 0, 1)
            for key, value in cost_components.items()
        }
        
        # Calculate perfect order rate
        perfect_orders = PurchaseOrder.objects.filter(
            status='delivered',
            actual_delivery__lte=F('expected_delivery')
        ).count()
        perfect_order_rate = round((perfect_orders / total_orders * 100) if total_orders else 0, 2)
        
        # Calculate stock out percentage by month
        current_year = timezone.now().year
        stock_out_data = []
        
        for month in range(1, 13):
            month_start = timezone.datetime(current_year, month, 1)
            month_end = (month_start + timezone.timedelta(days=32)).replace(day=1) - timezone.timedelta(days=1)
            
            # Get all products that existed during this month
            total_products = Product.objects.filter(
                created_at__lte=month_end
            ).count()
            
            # Count products that had a stock-out during this month
            stock_out_products = Product.objects.filter(
                created_at__lte=month_end,
                stock_quantity=0,
                updated_at__range=(month_start, month_end)
            ).count()
            
            percentage = round((stock_out_products / total_products * 100) if total_products else 0, 1)
            stock_out_data.append(percentage)
        
        # Calculate inventory turnover by year
        current_year = timezone.now().year
        turnover_data = []
        turnover_labels = []
        
        for year in range(current_year - 7, current_year + 1):
            # Calculate COGS (Cost of Goods Sold)
            cogs = PurchaseOrderItem.objects.filter(
                purchase_order__order_date__year=year
            ).aggregate(
                total=ExpressionWrapper(
                    Sum(F('quantity') * F('unit_price')),
                    output_field=FloatField()
                )
            )['total'] or 0
            
            # Calculate average inventory value
            avg_inventory = Product.objects.filter(
                updated_at__year=year
            ).aggregate(
                value=ExpressionWrapper(
                    Avg(F('stock_quantity') * F('unit_price')),
                    output_field=FloatField()
                )
            )['value'] or 1  # Avoid division by zero
            
            turnover = round(cogs / avg_inventory, 1) if avg_inventory else 0
            turnover_data.append(turnover)
            turnover_labels.append(f'{year}FY')
        
        # Add the new metrics to context
        context.update({
            'total_revenue': f"{total_revenue:,.2f}",
            'fulfillment_rate': round(fulfillment_rate, 1),
            'avg_order_value': f"{avg_order_value:,.2f}",
            'inventory_turnover': round(float(total_revenue / (Product.objects.aggregate(
                total_value=ExpressionWrapper(
                    Sum(F('stock_quantity') * F('unit_price')),
                    output_field=DecimalField(max_digits=10, decimal_places=2)
                )
            )['total_value'] or Decimal('1'))), 1),
            'categories': list(categories),
            'stock_levels': stock_levels,
            'order_dates': order_dates,
            'order_counts': order_counts,
            'category_performance': [
                {'label': category, **data}
                for category, data in category_data.items()
            ],
            'top_suppliers': top_suppliers_data,
            'cost_percentages': cost_percentages,
            'perfect_order_rate': perfect_order_rate,
            'stock_out_data': stock_out_data,
            'turnover_data': turnover_data,
            'turnover_labels': turnover_labels,
        })
        return context

@login_required
def analytics_view(request):
    # Get analytics data for the last year
    current_date = timezone.now()
    start_date = current_date - timedelta(days=365)
    
    # Calculate Perfect Order Rate from real orders
    total_orders = Order.objects.filter(created_at__gte=start_date).count()
    perfect_orders = Order.objects.filter(
        created_at__gte=start_date,
        status='delivered',
        delivery_issues=False
    ).count()
    
    # Calculate POR (Perfect Order Rate)
    por = (perfect_orders / total_orders * 100) if total_orders > 0 else 0
    
    # Calculate Inventory Turnover by year
    inventory_turnover = []
    current_year = timezone.now().year
    
    for year in range(current_year - 7, current_year + 1):
        year_start = timezone.datetime(year, 1, 1, tzinfo=timezone.get_current_timezone())
        year_end = timezone.datetime(year + 1, 1, 1, tzinfo=timezone.get_current_timezone())
        
        # Calculate COGS (Cost of Goods Sold) for the year
        cogs = PurchaseOrderItem.objects.filter(
            purchase_order__order_date__gte=year_start,
            purchase_order__order_date__lt=year_end
        ).aggregate(
            total_cogs=Sum(F('quantity') * F('unit_price'))
        )['total_cogs'] or 0
        
        # Calculate average inventory value for the year
        avg_inventory = Product.objects.aggregate(
            avg_value=ExpressionWrapper(
                Sum(F('stock_quantity') * F('unit_price')),
                output_field=DecimalField(max_digits=10, decimal_places=2)
            )
        )['avg_value'] or 1  # Use 1 to avoid division by zero
        
        # Calculate turnover ratio
        turnover = float(cogs) / float(avg_inventory)
        
        inventory_turnover.append({
            'year': f'{year}FY',
            'turnover': round(turnover, 2)
        })
    
    # Calculate Stock Out Percentage by Month
    months = []
    stock_out_data = []
    
    for i in range(12):
        month_start = current_date - timedelta(days=365-i*30)
        month_end = month_start + timedelta(days=30)
        
        total_products = Product.objects.count()
        stock_out_products = Product.objects.filter(
            stock_quantity=0,
            created_at__lte=month_end
        ).count()
        
        stock_out_percentage = (stock_out_products / total_products * 100) if total_products > 0 else 0
        
        months.append(month_start.strftime('%b'))
        stock_out_data.append(round(stock_out_percentage, 2))
    
    # Calculate Cost Components
    total_cost = PurchaseOrder.objects.aggregate(
        total=Sum('total_amount')
    )['total'] or 0
    
    risk_cost = PurchaseOrder.objects.filter(status='cancelled').aggregate(
        risk=Sum('total_amount')
    )['risk'] or 0
    
    freight_cost = PurchaseOrder.objects.aggregate(
        freight=Sum('shipping_cost')
    )['freight'] or 0
    
    # Calculate cost percentages
    cost_carry = {
        'risk': round((risk_cost / total_cost * 100) if total_cost > 0 else 0, 1),
        'freight': round((freight_cost / total_cost * 100) if total_cost > 0 else 0, 1),
        'service': 15,  # These could be calculated from service-related costs
        'storage': 15,  # These could be calculated from warehouse costs
        'admin': 10     # These could be calculated from administrative costs
    }
    
    context = {
        'por': round(por, 2),
        'inventory_turnover': inventory_turnover,
        'stock_out_data': list(zip(months, stock_out_data)),
        'cost_carry': cost_carry,
    }
    
    return render(request, 'inventory/analytics.html', context)

@login_required
def supplier_list(request):
    suppliers = Supplier.objects.all()
    return render(request, 'inventory/supplier_list.html', {'suppliers': suppliers})

@login_required
def supplier_create(request):
    if request.method == 'POST':
        form = SupplierForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Supplier created successfully.')
            return redirect('supplier_list')
    else:
        form = SupplierForm()
    return render(request, 'inventory/supplier_form.html', {'form': form})

@login_required
def supplier_detail(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    products = supplier.product_set.all()
    return render(request, 'inventory/supplier_detail.html', {
        'supplier': supplier,
        'products': products
    })

@login_required
def supplier_edit(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    if request.method == 'POST':
        form = SupplierForm(request.POST, instance=supplier)
        if form.is_valid():
            supplier = form.save()
            messages.success(request, 'Supplier updated successfully.')
            return redirect('inventory:supplier_detail', pk=supplier.pk)
    else:
        form = SupplierForm(instance=supplier)
    return render(request, 'inventory/supplier_form.html', {'form': form})

@login_required
def product_list(request):
    products = Product.objects.select_related('supplier').all()
    return render(request, 'inventory/product_list.html', {'products': products})

@login_required
def product_create(request):
    if request.method == 'POST':
        form = ProductForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Product created successfully.')
            return redirect('product_list')
    else:
        form = ProductForm()
    return render(request, 'inventory/product_form.html', {'form': form})

@login_required
def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    return render(request, 'inventory/product_detail.html', {'product': product})

@login_required
def product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            product = form.save()
            messages.success(request, 'Product updated successfully.')
            return redirect('inventory:product_detail', pk=product.pk)
    else:
        form = ProductForm(instance=product)
    return render(request, 'inventory/product_form.html', {'form': form})

@login_required
def purchase_order_list(request):
    purchase_orders = PurchaseOrder.objects.select_related('supplier').all()
    return render(request, 'inventory/purchase_order_list.html', {'purchase_orders': purchase_orders})

@login_required
def purchase_order_create(request):
    if request.method == 'POST':
        form = PurchaseOrderForm(request.POST)
        if form.is_valid():
            order = form.save(commit=False)
            order.total_amount = 0  # Will be updated when items are added
            order.save()
            messages.success(request, 'Purchase Order created successfully.')
            return redirect('purchase_order_detail', pk=order.pk)
    else:
        form = PurchaseOrderForm()
    return render(request, 'inventory/purchase_order_form.html', {'form': form})

@login_required
def warehouse_list(request):
    warehouses = Warehouse.objects.all()
    return render(request, 'inventory/warehouse_list.html', {'warehouses': warehouses})

@login_required
def warehouse_create(request):
    if request.method == 'POST':
        form = WarehouseForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Warehouse created successfully.')
            return redirect('warehouse_list')
    else:
        form = WarehouseForm()
    return render(request, 'inventory/warehouse_form.html', {'form': form})

@login_required
def inventory_movement_list(request):
    movements = InventoryMovement.objects.select_related('product', 'warehouse').all()
    return render(request, 'inventory/movement_list.html', {'movements': movements})

@login_required
def inventory_movement_create(request):
    if request.method == 'POST':
        form = InventoryMovementForm(request.POST)
        if form.is_valid():
            movement = form.save(commit=False)
            product = movement.product
            
            # Update product stock quantity based on movement type
            if movement.movement_type == 'in':
                product.stock_quantity += movement.quantity
            elif movement.movement_type == 'out':
                if product.stock_quantity >= movement.quantity:
                    product.stock_quantity -= movement.quantity
                else:
                    messages.error(request, 'Insufficient stock quantity.')
                    return render(request, 'inventory/movement_form.html', {'form': form})
            
            product.save()
            movement.save()
            messages.success(request, 'Inventory movement recorded successfully.')
            return redirect('inventory_movement_list')
    else:
        form = InventoryMovementForm()
    return render(request, 'inventory/movement_form.html', {'form': form})

@login_required
def stock_alerts(request):
    low_stock_products = Product.objects.filter(
        stock_quantity__lte=F('reorder_point')
    ).select_related('supplier')
    return render(request, 'inventory/stock_alerts.html', 
                 {'low_stock_products': low_stock_products})
