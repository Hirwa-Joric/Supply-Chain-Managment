from django.contrib.auth.models import User
from django.db import models
from menuinst.platforms import MenuItem

from restaurant.models import Menu


class Customer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    location = models.CharField(max_length=255)

    def __str__(self):
        return self.user.username

    @property
    def is_customer(self):
        return True  # This property simply confirms this user is a customer


class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('preparation', 'In Preparation'),
        ('on_way', 'On the Way'),
        ('finished', 'Finished'),
        ('canceled', 'Canceled'),
    ]
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    menu_item = models.ForeignKey(Menu ,on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    order_time = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.menu_item} - {self.status}"
