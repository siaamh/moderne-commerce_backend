"""
MCP tool implementations: get_my_orders, get_order_details, create_order
"""
from apps.orders.models import Order
from apps.orders.services import OrderCreationError, create_order_from_cart
from apps.mcp_tools.utils import error, format_order, success

SUPPORTED_PAYMENT_METHODS = {"cash_on_delivery"}


def get_my_orders(user, status: str | None = None, limit: int = 10) -> dict:
    """
    Get the authenticated customer's order history. Use when the user asks about
    their past orders, order status, recent purchases, or order history.
    Optionally filter by status: pending, confirmed, shipped, delivered, cancelled.
    Returns order summaries ordered by most recent first.
    Never returns another customer's orders.
    """
    limit = min(max(1, int(limit)), 50)

    qs = Order.objects.filter(customer=user).order_by("-created_at")

    if status:
        valid_statuses = [s.value for s in Order.Status]
        if status not in valid_statuses:
            return error(
                "INVALID_INPUT",
                f"Invalid status '{status}'. Choose from: {', '.join(valid_statuses)}",
            )
        qs = qs.filter(status=status)

    orders = []
    for order in qs[:limit]:
        orders.append({
            "order_number": order.order_number,
            "status": order.status,
            "status_display": order.get_status_display(),
            "total_amount": str(order.total_amount),
            "delivery_fee": str(order.delivery_fee),
            "item_count": order.items.count(),
            "payment_method": order.payment_method,
            "payment_status": order.payment_status,
            "created_at": order.created_at.isoformat(),
        })

    return success({"count": len(orders), "orders": orders})


def get_order_details(
    user,
    order_number: str | None = None,
    order_id: int | None = None,
) -> dict:
    """
    Get full details for a specific order. Use when the user asks about a particular
    order, wants to check what they ordered, track status, see the breakdown of
    costs, or review shipping information.
    Requires order_number or order_id. Enforces ownership — customers only see
    their own orders. Staff/admin can view any order.
    """
    if not order_number and not order_id:
        return error("INVALID_INPUT", "Provide either order_number or order_id.")

    try:
        qs = Order.objects.prefetch_related("items")
        if order_number:
            order = qs.get(order_number=order_number.upper())
        else:
            order = qs.get(pk=order_id)
    except Order.DoesNotExist:
        return error("NOT_FOUND", "Order not found.")

    # Enforce ownership unless staff/admin
    if user.role == "customer" and order.customer_id != user.pk:
        return error("UNAUTHORIZED", "You do not have access to this order.")

    return success(format_order(order))


def create_order(
    user,
    full_name: str,
    phone: str,
    delivery_address: str,
    payment_method: str,
    customer_confirmation: bool,
) -> dict:
    """
    Place a new order using the customer's current cart contents.

    IMPORTANT — ONLY call this tool after ALL of the following steps:
    1. You called get_cart to retrieve the current cart.
    2. You presented a clear summary to the customer showing: each item name,
       quantity, unit price, any discounts applied, subtotal, delivery fee
       (৳60.00), and the grand total.
    3. The customer has explicitly confirmed they want to place the order.
    4. You set customer_confirmation=True based on that explicit confirmation.

    If customer_confirmation is False, the order will NOT be created.

    Supported payment_method values: cash_on_delivery

    Uses atomic transaction with row-level stock locking to prevent overselling.
    Prices are recalculated server-side at order time — never trust AI-provided prices.
    """
    # Server-side enforcement of explicit confirmation
    if not customer_confirmation:
        return error(
            "CONFIRMATION_REQUIRED",
            "Order not placed. You must present the cart summary to the customer "
            "and receive explicit confirmation before placing the order.",
        )

    if not full_name or not full_name.strip():
        return error("INVALID_INPUT", "full_name is required.")

    if not phone or not phone.strip():
        return error("INVALID_INPUT", "phone is required.")

    if not delivery_address or not delivery_address.strip():
        return error("INVALID_INPUT", "delivery_address is required.")

    if payment_method not in SUPPORTED_PAYMENT_METHODS:
        return error(
            "INVALID_INPUT",
            f"Unsupported payment method '{payment_method}'. "
            f"Supported: {', '.join(SUPPORTED_PAYMENT_METHODS)}",
        )

    try:
        order = create_order_from_cart(
            user=user,
            full_name=full_name.strip(),
            phone=phone.strip(),
            delivery_address=delivery_address.strip(),
        )
    except OrderCreationError as exc:
        return error("ORDER_CREATION_FAILED", str(exc))
    except Exception as exc:
        # Log but don't expose internals
        import logging
        logging.getLogger("mcp_tools.orders").error("create_order failed: %s", exc)
        return error("ORDER_CREATION_FAILED", "Order could not be placed. Please try again.")

    return success({
        "message": "Order placed successfully!",
        "order_number": order.order_number,
        "status": order.status,
        "subtotal": str(order.subtotal),
        "delivery_fee": str(order.delivery_fee),
        "total_amount": str(order.total_amount),
        "item_count": order.items.count(),
        "payment_method": order.payment_method,
        "estimated_delivery": "3-5 business days",
        "created_at": order.created_at.isoformat(),
    })
