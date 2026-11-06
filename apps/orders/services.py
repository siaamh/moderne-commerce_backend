"""
Order business logic.

All mutating operations run inside atomic transactions with SELECT FOR UPDATE
to prevent overselling and race conditions.

Pricing is delegated entirely to apps.products.pricing.get_price_info —
the single source of truth. Client-submitted prices are never trusted.
"""

from decimal import Decimal

from django.db import transaction
from django.db.models import F

from apps.cart.models import Cart
from apps.products.models import Product
from apps.products.pricing import get_price_info
from .models import Order, OrderItem


DELIVERY_FEE = Decimal("60.00")  # Fixed fee in BDT; make configurable later.


class OrderCreationError(Exception):
    """Raised when order creation fails for a business rule reason."""
    pass


def create_order_from_cart(user, full_name: str, phone: str, delivery_address: str) -> Order:
    """
    Create an Order from the user's current cart inside a single transaction.

    Steps:
    1. Lock all relevant product rows (SELECT FOR UPDATE) to prevent overselling.
    2. Validate stock for every item.
    3. Compute prices via the central pricing service (no client prices trusted).
    4. Deduct stock atomically.
    5. Build Order + fully-snapshotted OrderItems.
    6. Clear the cart only after everything succeeds.

    Raises OrderCreationError for any business rule violation.
    """
    with transaction.atomic():
        # Retrieve cart.
        try:
            cart = Cart.objects.get(customer=user)
        except Cart.DoesNotExist:
            raise OrderCreationError("Your cart is empty.")

        cart_items = list(
            cart.items.select_related("product").prefetch_related("product__discounts")
        )
        if not cart_items:
            raise OrderCreationError("Your cart is empty.")

        # Lock product rows to prevent concurrent overselling.
        product_ids = [item.product_id for item in cart_items]
        locked_products = {
            p.pk: p
            for p in Product.objects.select_for_update()
                             .prefetch_related("discounts")
                             .filter(pk__in=product_ids)
        }

        # Validate availability and stock for every item.
        for item in cart_items:
            product = locked_products.get(item.product_id)
            if not product or not product.is_active:
                raise OrderCreationError(
                    f"'{item.product.name}' is no longer available."
                )
            if item.quantity > product.stock:
                raise OrderCreationError(
                    f"Insufficient stock for '{product.name}'. "
                    f"Available: {product.stock}, requested: {item.quantity}."
                )

        # Compute pricing for every product via the central service.
        price_infos = {pid: get_price_info(p) for pid, p in locked_products.items()}

        # Deduct stock atomically.
        for item in cart_items:
            product = locked_products[item.product_id]
            product.stock -= item.quantity
            product.save(update_fields=["stock"])

        # Calculate order totals from server-side final prices.
        subtotal = sum(
            price_infos[item.product_id].final_price * item.quantity
            for item in cart_items
        )
        delivery_fee = DELIVERY_FEE
        total_amount = subtotal + delivery_fee

        # Create the Order record.
        order = Order.objects.create(
            customer=user,
            full_name=full_name,
            phone=phone,
            delivery_address=delivery_address,
            subtotal=subtotal,
            delivery_fee=delivery_fee,
            total_amount=total_amount,
        )

        # Build immutable OrderItem snapshots.
        order_items = []
        for item in cart_items:
            product = locked_products[item.product_id]
            info = price_infos[item.product_id]
            line_subtotal = info.final_price * item.quantity
            order_items.append(
                OrderItem(
                    order=order,
                    product=product,
                    product_name=product.name,
                    original_unit_price=info.original_price,
                    discount_type=info.discount_type or "",
                    discount_value=info.discount_value,
                    discount_amount=info.discount_amount,
                    unit_price=info.final_price,
                    quantity=item.quantity,
                    subtotal=line_subtotal,
                )
            )
        OrderItem.objects.bulk_create(order_items)

        # Clear the cart only after all DB writes succeed.
        cart.items.all().delete()

    return order


def cancel_order(order: Order, user) -> Order:
    """
    Cancel an order and restore stock.

    Rules:
    - Terminal orders (delivered, already cancelled) cannot be cancelled.
    - Customers may only cancel PENDING or CONFIRMED orders.
    - ADMIN/STAFF may cancel any non-terminal order.
    - Stock is restored exactly once (idempotent via status check under lock).
    """
    terminal_statuses = {Order.Status.DELIVERED, Order.Status.CANCELLED}
    if order.status in terminal_statuses:
        raise OrderCreationError(
            f"Cannot cancel an order with status '{order.get_status_display()}'."
        )

    customer_cancellable = {Order.Status.PENDING, Order.Status.CONFIRMED}
    if user.role == "customer" and order.status not in customer_cancellable:
        raise OrderCreationError("You can only cancel pending or confirmed orders.")

    with transaction.atomic():
        locked_order = Order.objects.select_for_update().get(pk=order.pk)
        if locked_order.status == Order.Status.CANCELLED:
            raise OrderCreationError("Order is already cancelled.")

        # Restore stock using F() for safe concurrent updates.
        for item in locked_order.items.all():
            if item.product_id:
                Product.objects.filter(pk=item.product_id).update(
                    stock=F("stock") + item.quantity
                )

        locked_order.status = Order.Status.CANCELLED
        locked_order.save(update_fields=["status", "updated_at"])

    return locked_order
