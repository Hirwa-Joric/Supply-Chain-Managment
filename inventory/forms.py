from django import forms
from django.core.exceptions import ValidationError
from .models import (
    Category, 
    Product, 
    Supplier, 
    PurchaseOrder, 
    PurchaseOrderItem,
    InventoryTransaction
)

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = [
            'name', 
            'contact_person', 
            'email', 
            'phone',
            'address',
            'tax_number',
            'is_active',
            'notes'
        ]
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'name',
            'sku',
            'category',
            'description',
            'minimum_stock',
            'reorder_point',
            'price',
            'supplier',
            'location',
            'barcode',
            'is_active'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'price': forms.NumberInput(attrs={'step': '0.01'}),
        }

    def clean_sku(self):
        sku = self.cleaned_data['sku']
        if Product.objects.filter(sku=sku).exclude(pk=self.instance.pk).exists():
            raise ValidationError('This SKU is already in use.')
        return sku

class PurchaseOrderForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrder
        fields = ['supplier', 'expected_delivery', 'notes']
        widgets = {
            'expected_delivery': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

class PurchaseOrderItemForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrderItem
        fields = ['product', 'quantity', 'unit_price']
        widgets = {
            'unit_price': forms.NumberInput(attrs={'step': '0.01'})
        }

    def clean(self):
        cleaned_data = super().clean()
        product = cleaned_data.get('product')
        quantity = cleaned_data.get('quantity')
        
        if product and quantity:
            if quantity < 1:
                raise ValidationError('Quantity must be greater than 0')
        return cleaned_data

class InventoryTransactionForm(forms.ModelForm):
    class Meta:
        model = InventoryTransaction
        fields = ['product', 'transaction_type', 'quantity', 'reference_number', 'notes', 'unit_price']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3}),
            'unit_price': forms.NumberInput(attrs={'step': '0.01'})
        }

    def clean(self):
        cleaned_data = super().clean()
        transaction_type = cleaned_data.get('transaction_type')
        quantity = cleaned_data.get('quantity')
        product = cleaned_data.get('product')

        if product and quantity and transaction_type:
            if transaction_type in ['SALE', 'TRANSFER'] and quantity > product.quantity:
                raise ValidationError(
                    f'Cannot remove {quantity} units. Only {product.quantity} available.'
                )
        return cleaned_data

class ProductSearchForm(forms.Form):
    query = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Search products...'})
    )
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        required=False,
        empty_label="All Categories"
    )
    supplier = forms.ModelChoiceField(
        queryset=Supplier.objects.all(),
        required=False,
        empty_label="All Suppliers"
    )
    stock_status = forms.ChoiceField(
        choices=[('', 'All Status')] + Product.STOCK_STATUS_CHOICES,
        required=False
    )

class DateRangeForm(forms.Form):
    start_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=False
    )
    end_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=False
    )