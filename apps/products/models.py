from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


class Category(models.Model):
    """
    Supports a maximum of two levels: parent categories and subcategories.
    A subcategory has parent != None. A root category has parent == None.
    """

    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
    )
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="categories/", blank=True, null=True)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0, help_text="Display ordering; lower comes first.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"
        ordering = ["order", "name"]
        # Same name is allowed if under different parents.
        unique_together = [("parent", "name")]

    def __str__(self):
        if self.parent:
            return f"{self.parent.name} › {self.name}"
        return self.name

    def clean(self):
        # Prevent more than two levels deep.
        if self.parent:
            if self.parent.parent is not None:
                raise ValidationError(
                    "Only two levels of categories are supported. "
                    "The selected parent is already a subcategory."
                )
            # Prevent circular reference.
            if self.pk and self.parent_id == self.pk:
                raise ValidationError("A category cannot be its own parent.")

    def save(self, *args, **kwargs):
        self.full_clean()
        if not self.slug:
            base = slugify(self.name)
            slug = base
            n = 1
            while Category.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{n}"
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)

    @property
    def is_subcategory(self):
        return self.parent_id is not None


class Brand(models.Model):
    name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    logo = models.ImageField(upload_to="brands/", blank=True, null=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Brand"
        verbose_name_plural = "Brands"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Product(models.Model):
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
    )
    brand = models.ForeignKey(
        Brand,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
    )
    name = models.CharField(max_length=300)
    slug = models.SlugField(max_length=320, unique=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    image = models.ImageField(upload_to="products/", blank=True, null=True)
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False, db_index=True)
    featured_order = models.PositiveIntegerField(
        default=0, help_text="Lower value appears first in featured listings."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Product"
        verbose_name_plural = "Products"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["is_active", "category"]),
            models.Index(fields=["is_active", "is_featured", "featured_order"]),
            models.Index(fields=["is_active", "brand"]),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Discount(models.Model):
    """
    A time-bounded discount attached to a single product.

    Rules enforced at the model level:
    - Only one active discount per product at any moment (enforced in clean()).
    - Percentage discounts cannot exceed 100.
    - Fixed discounts cannot exceed the product's regular price.
    - value must be non-negative.
    - ends_at must be after starts_at.
    - A discount whose window is in the future does not apply yet.
    - An expired discount stops applying automatically (time-based, no cron needed).
    """

    class DiscountType(models.TextChoices):
        PERCENTAGE = "percentage", "Percentage"
        FIXED = "fixed", "Fixed Amount"

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="discounts",
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    discount_type = models.CharField(max_length=20, choices=DiscountType.choices)
    value = models.DecimalField(max_digits=10, decimal_places=2)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Discount"
        verbose_name_plural = "Discounts"
        ordering = ["-starts_at"]
        indexes = [
            models.Index(fields=["product", "is_active", "starts_at", "ends_at"]),
        ]

    def __str__(self):
        return f"{self.title} — {self.product.name}"

    def clean(self):
        from decimal import Decimal

        errors = {}

        if self.value is not None and self.value < 0:
            errors["value"] = "Discount value cannot be negative."

        if self.discount_type == self.DiscountType.PERCENTAGE:
            if self.value is not None and self.value > 100:
                errors["value"] = "Percentage discount cannot exceed 100."

        if self.discount_type == self.DiscountType.FIXED and self.product_id and self.value is not None:
            try:
                product = self.product
                if self.value > product.price:
                    errors["value"] = (
                        f"Fixed discount ({self.value}) cannot exceed "
                        f"the product price ({product.price})."
                    )
            except Product.DoesNotExist:
                pass

        if self.starts_at and self.ends_at:
            if self.ends_at <= self.starts_at:
                errors["ends_at"] = "End time must be after start time."

        if errors:
            raise ValidationError(errors)

        # Enforce only one active, overlapping discount per product at a time.
        if self.is_active and self.starts_at and self.ends_at and self.product_id:
            qs = Discount.objects.filter(
                product_id=self.product_id,
                is_active=True,
                starts_at__lt=self.ends_at,
                ends_at__gt=self.starts_at,
            )
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                raise ValidationError(
                    "An active discount already covers part or all of this time window "
                    "for the selected product."
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def is_currently_active(self) -> bool:
        """True only if is_active and the current time is within the window."""
        if not self.starts_at or not self.ends_at:
            return False
        now = timezone.now()
        return bool(self.is_active and self.starts_at <= now < self.ends_at)
