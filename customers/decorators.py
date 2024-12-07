from django.shortcuts import redirect
from django.contrib.auth.decorators import user_passes_test

from customers.models import Customer


def customer_required(view_func):
    def wrapper(request, *args, **kwargs):
        if request.user.is_superuser:
            return redirect('restaurant_dashboard')  # Redirect admin users to the admin page
        try:
            # Ensure the user has a customer profile
            request.user.customer
        except Customer.DoesNotExist:
            return redirect('customer_registration')  # Redirect to customer registration if no customer profile

        return view_func(request, *args, **kwargs)

    return wrapper
