from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
import os
import django

# Set up Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "scm_system.settings")
django.setup()

# Import Django models after setup
from inventory.models import Product, Category, Supplier, PurchaseOrder, InventoryTransaction
from django.db.models import Sum, F, Q
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal

# Create FastAPI app
app = FastAPI(title="SCM System API", description="Supply Chain Management System API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for request/response
from pydantic import BaseModel, condecimal
from datetime import datetime
from typing import Optional, List

class ProductBase(BaseModel):
    name: str
    sku: str
    description: Optional[str] = None
    quantity: int
    minimum_stock: int
    price: condecimal(max_digits=10, decimal_places=2)
    category_id: int
    supplier_id: Optional[int] = None

class ProductCreate(ProductBase):
    pass

class ProductResponse(ProductBase):
    id: int
    stock_status: str
    created_at: datetime
    
    class Config:
        orm_mode = True

# API Routes
@app.get("/products/", response_model=List[ProductResponse])
async def get_products(
    skip: int = 0,
    limit: int = 10,
    search: Optional[str] = None,
    category: Optional[int] = None,
    supplier: Optional[int] = None,
    stock_status: Optional[str] = None
):
    """
    Get list of products with optional filtering
    """
    query = Product.objects.all()

    if search:
        query = query.filter(
            Q(name__icontains=search) |
            Q(sku__icontains=search) |
            Q(description__icontains=search)
        )

    if category:
        query = query.filter(category_id=category)

    if supplier:
        query = query.filter(supplier_id=supplier)

    if stock_status:
        if stock_status == 'OUT_OF_STOCK':
            query = query.filter(quantity=0)
        elif stock_status == 'LOW_STOCK':
            query = query.filter(quantity__lte=F('minimum_stock'))
        elif stock_status == 'IN_STOCK':
            query = query.filter(quantity__gt=F('minimum_stock'))

    total = await query.count()
    products = await query.select_related('category', 'supplier')[skip:skip + limit]

    return products

@app.get("/products/{product_id}", response_model=ProductResponse)
async def get_product(product_id: int):
    """
    Get detailed information about a specific product
    """
    try:
        product = await Product.objects.select_related(
            'category', 'supplier'
        ).get(id=product_id)
        return product
    except Product.DoesNotExist:
        raise HTTPException(status_code=404, detail="Product not found")

@app.get("/dashboard/stats/")
async def get_dashboard_stats():
    """
    Get dashboard statistics
    """
    end_date = timezone.now()
    start_date = end_date - timedelta(days=30)

    stats = {
        "total_products": await Product.objects.count(),
        "low_stock_products": await Product.objects.filter(
            quantity__lte=F('minimum_stock')
        ).count(),
        "out_of_stock": await Product.objects.filter(quantity=0).count(),
        "total_inventory_value": await Product.objects.aggregate(
            total=Sum(F('quantity') * F('price'))
        ),
        "recent_transactions": await InventoryTransaction.objects.select_related(
            'product'
        ).order_by('-transaction_date')[:10],
        "pending_orders": await PurchaseOrder.objects.filter(
            status__in=['PENDING', 'APPROVED', 'ORDERED']
        ).count()
    }

    return stats

@app.get("/analytics/stock-movements/")
async def get_stock_movements(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    product_id: Optional[int] = None
):
    """
    Get stock movement analytics
    """
    query = InventoryTransaction.objects.all()

    if start_date and end_date:
        query = query.filter(transaction_date__range=[start_date, end_date])
    
    if product_id:
        query = query.filter(product_id=product_id)

    movements = await query.values(
        'transaction_type'
    ).annotate(
        total_quantity=Sum('quantity'),
        total_value=Sum(F('quantity') * F('unit_price'))
    )

    return movements

# Add more endpoints for other functionality
# ... (Purchase Orders, Suppliers, etc.)