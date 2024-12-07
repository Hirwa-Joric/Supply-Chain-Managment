from django import forms
from restaurant.models import Branch
from restaurant.models import Menu

class BranchForm(forms.ModelForm):
    class Meta:
        model = Branch
        fields = ['restaurant', 'location', 'image', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'w-full rounded-md border-gray-300'}),
        }
        labels = {
            'restaurant': 'Select Restaurant',
            'location': 'Branch Location',
            'image': 'Branch Image URL',
            'description': 'Description (optional)',
        }


class MenuForm(forms.ModelForm):
    class Meta:
        model = Menu
        fields = ['branch', 'name', 'image_url', 'description', 'price']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'w-full rounded-md border-gray-300'}),
            'price': forms.NumberInput(attrs={'step': '0.01', 'class': 'w-full rounded-md border-gray-300'}),
        }
        labels = {
            'branch': 'Select Branch',
            'name': 'Menu Item Name',
            'image_url': 'Image URL',
            'description': 'Description',
            'price': 'Price (RWF)',
        }