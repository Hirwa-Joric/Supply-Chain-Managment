# Generated by Django 4.2.7 on 2024-12-02 11:25

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0002_order_orderitem"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="category",
            field=models.CharField(
                choices=[
                    ("electronics", "Electronics"),
                    ("clothing", "Clothing"),
                    ("food", "Food"),
                    ("accessories", "Accessories"),
                    ("other", "Other"),
                ],
                default="other",
                max_length=50,
            ),
        ),
    ]
