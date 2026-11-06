"""
MCP tool implementations: get_cart, add_to_cart, update_cart_item, remove_from_cart
"""
from apps.cart.models import Cart, CartItem
from apps.products.models import Product
from apps.mcp_tools.utils import error, format_cart, success


def _get_or_create_cart(user):
    cart, _ = Cart.objects.get_or_create(customer=user)
    return cart


def get_cart(user) -> dict:
    """
    Get the authenticated customer's shopping cart. Use when the user asks to see
    their cart, what's in their bag, or their current items. Shows quantities,
    current prices (with any active discounts applied) and the server-calculated total.
    Never call this with a user_id argument — identity comes from authentication.
    """
    cart = _get_or_create_cart(user)
    return success(format_cart(cart))


def add_to_cart(user, product_id: int, quantity: int) -> dict:
    """
    Add a product to the authenticated customer's cart. Use when the user says
    'add to cart', 'I want to buy this', or 'put X in my bag'.
    Validates product availability and stock before adding.
    If the product is already in the cart, quantity is merged.
    Returns the updated cart with current prices.
    """
    if quantity < 1:
        return error("INVALID_INPUT", "Quantity must be at least 1.")

    try:
        product = (
            Product.objects.filter(is_active=True)
            .prefetch_related("discounts")
            .get(pk=product_id)
        )
    except Product.DoesNotExist:
        return error("PRODUCT_NOT_FOUND", f"Product {product_id} not found or unavailable.")

    if product.stock < 1:
        return error("OUT_OF_STOCK", f"'{product.name}' is out of stock.")

    cart = _get_or_create_cart(user)
    existing = cart.items.filter(product=product).first()

    if existing:
        new_qty = existing.quantity + quantity
        if new_qty > product.stock:
            available_more = product.stock - existing.quantity
            return error(
                "OUT_OF_STOCK",
                f"Cannot add {quantity} more of '{product.name}'. "
                f"Only {available_more} additional unit(s) available "
                f"({existing.quantity} already in cart).",
            )
        existing.quantity = new_qty
        existing.save(update_fields=["quantity", "updated_at"])
    else:
        if quantity > product.stock:
            return error(
                "OUT_OF_STOCK",
                f"Only {product.stock} unit(s) of '{product.name}' available.",
            )
        CartItem.objects.create(cart=cart, product=product, quantity=quantity)

    cart.refresh_from_db()
    return success({
        "message": f"Added {quantity}x '{product.name}' to cart.",
        "cart": format_cart(cart),
    })


def update_cart_item(user, cart_item_id: int, quantity: int) -> dict:
    """
    Update the quantity of an item already in the cart. Use when the user says
    'change quantity', 'I want 3 instead of 1', or 'update my cart'.
    Verifies the item belongs to the authenticated user and checks stock.
    Returns the updated cart.
    """
    if quantity < 1:
        return error("INVALID_INPUT", "Quantity must be at least 1.")

    try:
        item = CartItem.objects.select_related(
            "cart__customer", "product"
        ).prefetch_related("product__discounts").get(pk=cart_item_id)
    except CartItem.DoesNotExist:
        return error("NOT_FOUND", "Cart item not found.")

    if item.cart.customer_id != user.pk:
        return error("UNAUTHORIZED", "This cart item does not belong to you.")

    if quantity > item.product.stock:
        return error(
            "OUT_OF_STOCK",
            f"Only {item.product.stock} unit(s) of '{item.product.name}' available.",
        )

    item.quantity = quantity
    item.save(update_fields=["quantity", "updated_at"])

    cart = item.cart
    cart.refresh_from_db()
    return success({
        "message": f"Updated '{item.product.name}' quantity to {quantity}.",
        "cart": format_cart(cart),
    })


def remove_from_cart(user, cart_item_id: int) -> dict:
    """
    Remove an item from the cart. Use when the user says 'remove', 'delete from cart',
    or 'I don't want this anymore'. Verifies ownership before deletion.
    Returns the updated cart totals after removal.
    """
    try:
        item = CartItem.objects.select_related("cart__customer", "product").get(
            pk=cart_item_id
        )
    except CartItem.DoesNotExist:
        return error("NOT_FOUND", "Cart item not found.")

    if item.cart.customer_id != user.pk:
        return error("UNAUTHORIZED", "This cart item does not belong to you.")

    product_name = item.product.name
    cart = item.cart
    item.delete()

    cart.refresh_from_db()
    return success({
        "message": f"Removed '{product_name}' from cart.",
        "cart": format_cart(cart),
    })
