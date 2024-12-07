from django.db import models

class Restaurant(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)  # Added description field

    def __str__(self):
        return self.name

class Branch(models.Model):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE)
    location = models.CharField(max_length=255)
    image = models.CharField(max_length=255)  # Make non-nullable
    description = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.location


class Menu(models.Model):
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    image_url = models.CharField(null=True, max_length=255)
    description = models.TextField(null=True, blank=True)
    price = models.DecimalField(max_digits=6, decimal_places=2)

    def __str__(self):
        return f" {self.id}  {self.name} {self.branch}"
