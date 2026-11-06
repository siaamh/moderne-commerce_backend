"""
Migration 0002: Add discount snapshot fields to OrderItem.

New fields added to OrderItem:
  - original_unit_price  (the product's regular price at purchase time)
  - discount_type        (snapshot of the discount type applied, blank if none)
  - discount_value       (the raw discount value field, nullable)
  - discount_amount      (actual money saved per unit)

Existing field kept:
  - unit_price           (now means the FINAL price after discount)

Existing rows get sensible defaults:
  - original_unit_price  ← copies unit_price (no discount was stored before)
  - discount_type        ← blank string
  - discount_value       ← null
  - discount_amount      ← 0.00
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0001_initial"),
        ("products", "0002_brands_subcategories_featured_discounts"),
    ]

    operations = [
        # original_unit_price: defaults to 0; we'll back-fill via RunPython.
        migrations.AddField(
            model_name="orderitem",
            name="original_unit_price",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="orderitem",
            name="discount_type",
            field=models.CharField(blank=True, default="", max_length=20),
        ),
        migrations.AddField(
            model_name="orderitem",
            name="discount_value",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name="orderitem",
            name="discount_amount",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        # Back-fill original_unit_price from the existing unit_price column
        # for all historical rows (they had no discount, so original == final).
        migrations.RunSQL(
            sql="UPDATE orders_orderitem SET original_unit_price = unit_price;",
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
