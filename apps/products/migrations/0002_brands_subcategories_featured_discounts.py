"""
Migration 0002: Brands, subcategories, featured products, discounts.

What changes from 0001:
- Category: add parent FK, image, order field; relax name unique to (parent, name);
  change ordering; drop top-level unique on name.
- Brand: new model.
- Product: add brand FK, is_featured, featured_order; update indexes.
- Discount: new model.
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0001_initial"),
    ]

    operations = [
        # ----------------------------------------------------------------
        # Brand
        # ----------------------------------------------------------------
        migrations.CreateModel(
            name="Brand",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=200, unique=True)),
                ("slug", models.SlugField(blank=True, max_length=220, unique=True)),
                ("logo", models.ImageField(blank=True, null=True, upload_to="brands/")),
                ("description", models.TextField(blank=True)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Brand",
                "verbose_name_plural": "Brands",
                "ordering": ["name"],
            },
        ),

        # ----------------------------------------------------------------
        # Category — add new columns first, then adjust constraints
        # ----------------------------------------------------------------
        migrations.AddField(
            model_name="category",
            name="parent",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="children",
                to="products.category",
            ),
        ),
        migrations.AddField(
            model_name="category",
            name="image",
            field=models.ImageField(blank=True, null=True, upload_to="categories/"),
        ),
        migrations.AddField(
            model_name="category",
            name="order",
            field=models.PositiveIntegerField(
                default=0,
                help_text="Display ordering; lower comes first.",
            ),
        ),
        # Remove the old global unique on name (we'll use unique_together instead).
        migrations.AlterField(
            model_name="category",
            name="name",
            field=models.CharField(max_length=200),
        ),
        # Add (parent, name) unique_together.
        migrations.AlterUniqueTogether(
            name="category",
            unique_together={("parent", "name")},
        ),
        # Update ordering to match new model Meta.
        migrations.AlterModelOptions(
            name="category",
            options={
                "ordering": ["order", "name"],
                "verbose_name": "Category",
                "verbose_name_plural": "Categories",
            },
        ),

        # ----------------------------------------------------------------
        # Product — add brand FK, featured fields, update indexes
        # ----------------------------------------------------------------
        migrations.AddField(
            model_name="product",
            name="brand",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="products",
                to="products.brand",
            ),
        ),
        migrations.AddField(
            model_name="product",
            name="is_featured",
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AddField(
            model_name="product",
            name="featured_order",
            field=models.PositiveIntegerField(
                default=0,
                help_text="Lower value appears first in featured listings.",
            ),
        ),
        # Replace old indexes with updated set.
        migrations.AlterModelOptions(
            name="product",
            options={
                "ordering": ["-created_at"],
                "verbose_name": "Product",
                "verbose_name_plural": "Products",
            },
        ),
        migrations.AddIndex(
            model_name="product",
            index=models.Index(
                fields=["is_active", "is_featured", "featured_order"],
                name="products_pr_is_acti_feat_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="product",
            index=models.Index(
                fields=["is_active", "brand"],
                name="products_pr_is_acti_brand_idx",
            ),
        ),

        # ----------------------------------------------------------------
        # Discount
        # ----------------------------------------------------------------
        migrations.CreateModel(
            name="Discount",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=200)),
                ("description", models.TextField(blank=True)),
                (
                    "discount_type",
                    models.CharField(
                        choices=[("percentage", "Percentage"), ("fixed", "Fixed Amount")],
                        max_length=20,
                    ),
                ),
                ("value", models.DecimalField(decimal_places=2, max_digits=10)),
                ("starts_at", models.DateTimeField()),
                ("ends_at", models.DateTimeField()),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "product",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="discounts",
                        to="products.product",
                    ),
                ),
            ],
            options={
                "verbose_name": "Discount",
                "verbose_name_plural": "Discounts",
                "ordering": ["-starts_at"],
            },
        ),
        migrations.AddIndex(
            model_name="discount",
            index=models.Index(
                fields=["product", "is_active", "starts_at", "ends_at"],
                name="products_di_product_active_idx",
            ),
        ),
    ]
