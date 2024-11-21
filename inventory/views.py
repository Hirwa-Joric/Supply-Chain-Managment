from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count, Q, F, ExpressionWrapper, DecimalField
from django.db.models.functions import TruncMonth
from django.forms import inlineformset_factory
from django.utils import timezone
from decimal import Decimal
from datetime import datetime, timedelta
from .models import (
    Category,
    Product,
    Supplier,
    PurchaseOrder,
    PurchaseOrderItem,
    InventoryTransaction
)
from .forms import (
    CategoryForm,
    ProductForm,
    SupplierForm,
    PurchaseOrderForm,
    PurchaseOrderItemForm,
    InventoryTransactionForm,
    ProductSearchForm,
    DateRangeForm
)

@login_required
def dashboard(request):
    # Get date range from form
    date_form = DateRangeForm(request.GET)
    end_date = timezone.now()
    start_date = end_date - timedelta(days=30)
    
    if date_form.is_valid():
        if date_form.cleaned_data['start_date']:
            start_date = date_form.cleaned_data['start_date']
        if date_form.cleaned_data['end_date']:
            end_date = date_form.cleaned_data['end_date']

    # Calculate key metrics
    total_products = Product.objects.count()
    low_stock_products = Product.objects.filter(quantity__lte=F('minimum_stock')).count()
    out_of_stock = Product.objects.filter(quantity=0).count()
    active_suppliers = Supplier.objects.filter(is_active=True).count()

    # Calculate inventory value
    inventory_value = Product.objects.aggregate(
        total=Sum(F('quantity') * F('price'), output_field=DecimalField())
    )['total'] or Decimal('0')

    # Get recent transactions
    recent_transactions = InventoryTransaction.objects.select_related(
        'product', 'created_by'
    ).order_by('-transaction_date')[:10]

    # Get pending purchase orders
    pending_orders = PurchaseOrder.objects.filter(
        status__in=['PENDING', 'APPROVED', 'ORDERED']
    ).select_related('supplier').order_by('expected_delivery')[:5]

    # Calculate monthly transaction trends
    monthly_transactions = InventoryTransaction.objects.annotate(
        month=TruncMonth('transaction_date')
    ).values('month', 'transaction_type').annotate(
        total_quantity=Sum('quantity'),
        total_value=Sum(F('quantity') * F('unit_price'))
    ).order_by('month')

    # Top selling products
    top_products = Product.objects.annotate(
        total_sales=Sum('transactions__quantity',
            filter=Q(
                transactions__transaction_type='SALE',
                transactions__transaction_date__range=[start_date, end_date]
            )
        )
    ).exclude(total_sales=None).order_by('-total_sales')[:5]

    context = {
        'date_form': date_form,
        'total_products': total_products,
        'low_stock_products': low_stock_products,
        'out_of_stock': out_of_stock,
        'active_suppliers': active_suppliers,
        'inventory_value': inventory_value,
        'recent_transactions': recent_transactions,
        'pending_orders': pending_orders,
        'monthly_transactions': monthly_transactions,
        'top_products': top_products,
    }
    
    return render(request, 'inventory/dashboard.html', context)

@login_required
def product_list(request):
    search_form = ProductSearchForm(request.GET)
    products = Product.objects.select_related('category', 'supplier')

    if search_form.is_valid():
        if search_form.cleaned_data['query']:
            query = search_form.cleaned_data['query']
            products = products.filter(
                Q(name__icontains=query) |
                Q(sku__icontains=query) |
                Q(description__icontains=query)
            )
        
        if search_form.cleaned_data['category']:
            products = products.filter(category=search_form.cleaned_data['category'])
        
        if search_form.cleaned_data['supplier']:
            products = products.filter(supplier=search_form.cleaned_data['supplier'])
        
        if search_form.cleaned_data['stock_status']:
            status = search_form.cleaned_data['stock_status']
            if status == 'OUT_OF_STOCK':
                products = products.filter(quantity=0)
            elif status == 'LOW_STOCK':
                products = products.filter(quantity__lte=F('minimum_stock'))

    context = {
        'products': products,
        'search_form': search_form
    }
    return render(request, 'inventory/product_list.html', context)

@login_required
def product_detail(request, pk):
    product = get_object_or_404(Product.objects.select_related('category', 'supplier'), pk=pk)
    transactions = product.transactions.select_related('created_by').order_by('-transaction_date')[:10]
    
    context = {
        'product': product,
        'transactions': transactions,
    }
    return render(request, 'inventory/product_detail.html', context)

@login_required
def product_create(request):
    if request.method == 'POST':
        form = ProductForm(request.POST)
        if form.is_valid():
            product = form.save(commit=False)
            product.created_by = request.user
            product.save()
            messages.success(request, 'Product created successfully.')
            return redirect('product_detail', pk=product.pk)
    else:
        form = ProductForm()
    
    return render(request, 'inventory/product_form.html', {
        'form': form,
        'title': 'Create Product'
    })

@login_required
def product_create(request):
    if request.method == 'POST':
        form = ProductForm(request.POST)
        if form.is_valid():
            product = form.save(commit=False)
            product.created_by = request.user
            product.save()
            messages.success(request, 'Product created successfully.')
            return redirect('inventory:product_detail', pk=product.pk)
    else:
        form = ProductForm()
    
    return render(request, 'inventory/product_form.html', {
        'form': form,
        'title': 'Create Product'
    })
@login_required
def purchase_order_list(request):
    orders = PurchaseOrder.objects.select_related('supplier', 'created_by').order_by('-order_date')
    return render(request, 'inventory/purchase_order_list.html', {'orders': orders})

@login_required
def purchase_order_create(request):
    PurchaseOrderItemFormSet = inlineformset_factory(
        PurchaseOrder,
        PurchaseOrderItem,
        form=PurchaseOrderItemForm,
        extra=1,
        can_delete=True
    )
    
    if request.method == 'POST':
        form = PurchaseOrderForm(request.POST)
        if form.is_valid():
            po = form.save(commit=False)
            po.created_by = request.user
            po.save()
            
            formset = PurchaseOrderItemFormSet(request.POST, instance=po)
            if formset.is_valid():
                formset.save()
                messages.success(request, 'Purchase order created successfully.')
                return redirect('purchase_order_detail', pk=po.pk)
    else:
        form = PurchaseOrderForm()
        formset = PurchaseOrderItemFormSet()
    
    return render(request, 'inventory/purchase_order_form.html', {
        'form': form,
        'formset': formset,
        'title': 'Create Purchase Order'
    })

@login_required
def inventory_transaction_create(request):
    if request.method == 'POST':
        form = InventoryTransactionForm(request.POST)
        if form.is_valid():
            transaction = form.save(commit=False)
            transaction.created_by = request.user
            transaction.save()
            messages.success(request, 'Inventory transaction recorded successfully.')
            return redirect('product_detail', pk=transaction.product.pk)
    else:
        form = InventoryTransactionForm()
    
    return render(request, 'inventory/transaction_form.html', {
        'form': form,
        'title': 'Record Inventory Transaction'
    })
    
    
@login_required
def product_update(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            product = form.save()
            messages.success(request, 'Product updated successfully.')
            return redirect('inventory:product_detail', pk=product.pk)
    else:
        form = ProductForm(instance=product)
    return render(request, 'inventory/product_form.html', {'form': form, 'title': 'Update Product'})
    
    
@login_required
def purchase_order_detail(request, pk):
    purchase_order = get_object_or_404(PurchaseOrder, pk=pk)
    # Add your purchase order detail view logic here
    return render(request, 'inventory/purchase_order_detail.html', {'purchase_order': purchase_order})