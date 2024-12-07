from django.db.models import Count
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from customers.decorators import customer_required
from customers.models import Order, Customer
from .froms import BranchForm, MenuForm
from .models import Restaurant, Branch, Menu

def restaurant_dashboard(request):
    restaurants = Restaurant.objects.all()
    branches = Branch.objects.select_related('restaurant').all()
    customers = Customer.objects.select_related('user').all()
    orders = Order.objects.select_related('customer', 'menu_item').all()

    context = {
        'restaurants': restaurants,
        'branches': branches,
        'customers': customers,
        'orders': orders,
    }
    return render(request, 'restaurant/dashboard.html', context)


def analytics_dashboard(request):
    # Top branches based on the number of menus
    branches_with_menu_count = (
        Branch.objects.annotate(menu_count=Count('menu')).order_by('-menu_count')
    )

    # Top menus based on "likes" (replace `like_count` with the actual field if you have it)
    top_menus = (
        Menu.objects.filter(branch__restaurant__isnull=False)
        .annotate(like_count=Count('id'))  # Replace 'id' with actual likes tracking
        .order_by('-like_count')[:5]
    )

    context = {
        'branches_with_menu_count': list(
            branches_with_menu_count.values('location', 'menu_count')
        ),
        'top_menus': list(top_menus.values('name', 'like_count')),
    }
    return render(request, 'restaurant/analytics_dashboard.html', context)


def add_branch(request):
    if request.method == 'POST':
        form = BranchForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('branch_list')  # Redirect to the branch list or any other page
    else:
        form = BranchForm()

    return render(request, 'restaurant/add_branch.html', {'form': form})

def add_menu(request, branch_id=None):
    branch = None
    if branch_id:
        branch = get_object_or_404(Branch, id=branch_id)

    if request.method == 'POST':
        form = MenuForm(request.POST)
        if form.is_valid():
            menu = form.save(commit=False)
            if branch:
                menu.branch = branch
            menu.save()
            return redirect('branch_list')  # Redirect to branch list or desired page
    else:
        form = MenuForm(initial={'branch': branch} if branch else None)

    return render(request, 'restaurant/add_menu.html', {'form': form, 'branch': branch})
@customer_required
def branch_menus(request, branch_id):
    branch = Branch.objects.get(id=branch_id)
    menus = Menu.objects.filter(branch=branch)

    if request.method == 'POST':
        menu_item = request.POST.get('menu_item')
        menu = Menu.objects.get(id=menu_item)
        # print(menu)
        # Create and save the order
        order = Order.objects.create(
            customer=request.user.customer,
            menu_item=menu,
            status='pending',
        )
        messages.success(request, f"Order placed for {menu_item}!")
        return redirect('branch_menus', branch_id=branch_id)

    return render(request, 'restaurant/branch_menus.html', {'branch': branch, 'menus': menus})


def branch_list(request):
    branches = Branch.objects.all()
    return render(request, 'restaurant/branch_list.html', {'branches': branches})