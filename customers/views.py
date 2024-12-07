from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import UserCreationForm

from restaurant.models import Menu
from .decorators import customer_required
from .models import Order
from .forms import OrderForm, CustomerRegistrationForm


def register(request):
    if request.method == 'POST':
        form = CustomerRegistrationForm(request.POST)
        if form.is_valid():
            form.save()  # This will save both the User and Customer
            return redirect('login')  # Redirect to login after registration
    else:
        form = CustomerRegistrationForm()
    return render(request, 'customers/register.html', {'form': form})

def login_user(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('branch_list')
    return render(request, 'customers/login.html')

def logout_user(request):
    logout(request)
    return redirect('login')

@customer_required
def order_history(request):
    orders = Order.objects.filter(customer=request.user.customer)
    return render(request, 'customers/order_history.html', {'orders': orders})