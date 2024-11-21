from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from inventory.models import Product, Supplier, PurchaseOrder

def home(request):
    stats = {
        'products': Product.objects.count(),
        'suppliers': Supplier.objects.filter(is_active=True).count(),
        'orders': PurchaseOrder.objects.count()
    }
    return render(request, 'core/home.html', {'stats': stats})

def features(request):
    return render(request, 'core/features.html')

def about(request):
    return render(request, 'core/about.html')

def contact(request):
    return render(request, 'core/contact.html')