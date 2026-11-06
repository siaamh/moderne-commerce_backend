import uuid

from django.conf import settings
from django.db import models


def generate_order_number():
    return uuid.uuid4().hex[:12].upper()


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        CONFIRMED = "confirmed", "Confirmed"
        SHIPPED = "shipped", "Shipped"
        DELIVERED = "delivered", "Delivered"
        CANCELLED = "cancelled", "Cancelled"

    class PaymentMethod(models.TextChoices):
        CASH_ON_DELIVERY = "cash_on_delivery", "Cash on Delivery"

    class PaymentStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        PAID = "paid", "Paid"
        FAILED = "failed", "Failed"
        REFUNDED = "refunded", "Refunded"

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="orders",
    )
    order_number = models.CharField(
        max_length=20,
        unique=True,
        default=generate_order_number,
        editable=False,
    )
    full_name = models.CharField(max_length=200)
    phone = models.CharField(max_length=30)
    delivery_address = models.TextField()

    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    delivery_fee = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)

    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    payment_method = models.CharField(
        max_length=30,
        choices=PaymentMethod.choices,
        default=PaymentMethod.CASH_ON_DELIVERY,
    )
    payment_status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Order"
        verbose_name_plural = "Orders"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order #{self.order_number} — {self.customer.username}"


class OrderItem(models.Model):
    """
    Immutable snapshot of one line in an order.

    Pricing fields are frozen at the moment of purchase.
    Historical orders are never affected by later price/discount changes.
    """

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(
        "products.Product",
        on_delete=models.SET_NULL,
        null=True,
        related_name="order_items",
    )

    # ── Product snapshot ──────────────────────────────────────────────────
    product_name = models.CharField(max_length=300)

    # ── Price snapshot ────────────────────────────────────────────────────
    # original_unit_price: the product's regular price at time of purchase
    original_unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    # discount snapshot (nullable — no discount at purchase time means all null/zero)
    discount_type = models.CharField(max_length=20, blank=True, default="")
    discount_value = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    discount_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=0
    )
    # unit_price: final price per unit after discount (what was actually charged)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)

    quantity = models.PositiveIntegerField()
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        verbose_name = "Order Item"
        verbose_name_plural = "Order Items"

    def __str__(self):
        return f"{self.quantity}x {self.product_name}"
