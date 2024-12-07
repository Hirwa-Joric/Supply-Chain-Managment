from django import forms
from .models import Order
from django.contrib.auth.models import User
from .models import Customer

class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['menu_item']


class CustomerRegistrationForm(forms.ModelForm):
    username = forms.CharField(max_length=150)
    password = forms.CharField(widget=forms.PasswordInput)
    email = forms.EmailField()

    class Meta:
        model = Customer
        fields = ['location']

    def save(self, commit=True):
        # Create the user first
        user = User.objects.create_user(
            username=self.cleaned_data['username'],
            password=self.cleaned_data['password'],
            email=self.cleaned_data['email']
        )

        # Create the customer and link it to the user
        customer = Customer(user=user, location=self.cleaned_data['location'])

        if commit:
            user.save()
            customer.save()

        return customer
