"""
Shared helpers for MCP tool responses.
"""
from decimal import Decimal
from django.conf import settings


def image_url(path: str | None) -> str | None:
    """Prepend MEDIA_URL base to a relative image path."""
    if not path:
        return None
    if str(path).startswith("http"):
        return str(path)
    media_base = getattr(settings, "MCP_MEDIA_BASE_URL", "http://localhost:8742")
    return f"{media_base.rstrip('/')}/media/{str(path).lstrip('/')}"


def fmt(value) -> str:
    """Format a Decimal or numeric value as a 2-decimal string."""
    if value is None:
        return "0.00"
    return f"{Decimal(str(value)):.2f}"


def success(data: dict) -> dict:
    return {"status": "success", "data": data}


def error(code: str, message: str) -> dict:
    return {"status": "error", "code": code, "message": message}


def format_pricing(info) -> dict:
    """Serialize a PriceInfo dataclass to a plain dict."""
    return {
        "original_price": fmt(info.original_price),
        "final_price": fmt(info.final_price),
        "discount_amount": fmt(info.discount_amount),
        "discount_type": info.discount_type,
        "discount_value": fmt(info.discount_value) if info.discount_value is not None else None,
        "is_discounted": info.is_discounted,
        "offer_title": info.offer_title,
        "offer_description": info.offer_description,
        "offer_start": info.offer_start.isoformat() if info.offer_start else None,
        "offer_end": info.offer_end.isoformat() if info.offer_end else None,
    }


def format_product(product, price_info) -> dict:
    return {
        "id": product.id,
        "name": product.name,
        "slug": product.slug,
        "brand_name": product.brand.name if product.brand else None,
        "brand_slug": product.brand.slug if product.brand else None,
        "category_name": product.category.name if product.category else None,
        "category_slug": product.category.slug if product.category else None,
        "image_url": image_url(product.image.name if product.image else None),
        "stock": product.stock,
        "in_stock": product.stock > 0,
        **format_pricing(price_info),
    }


def format_cart(cart) -> dict:
    from apps.products.pricing import get_price_info
    from decimal import Decimal

    items = []
    total = Decimal("0.00")

    for item in cart.items.select_related("product").prefetch_related("product__discounts"):
        info = get_price_info(item.product)
        subtotal = info.final_price * item.quantity
        total += subtotal
        items.append({
            "item_id": item.id,
            "product_id": item.product_id,
            "product_name": item.product.name,
            "image_url": image_url(item.product.image.name if item.product.image else None),
            "quantity": item.quantity,
            "original_price": fmt(info.original_price),
            "final_unit_price": fmt(info.final_price),
            "discount_amount": fmt(info.discount_amount),
            "is_discounted": info.is_discounted,
            "subtotal": fmt(subtotal),
        })

    return {
        "cart_id": cart.id,
        "item_count": sum(i["quantity"] for i in items),
        "items": items,
        "total": fmt(total),
    }


def format_order(order) -> dict:
    items = []
    for item in order.items.all():
        items.append({
            "product_name": item.product_name,
            "original_unit_price": fmt(item.original_unit_price),
            "discount_type": item.discount_type or None,
            "discount_value": fmt(item.discount_value) if item.discount_value else None,
            "discount_amount": fmt(item.discount_amount),
            "unit_price": fmt(item.unit_price),
            "quantity": item.quantity,
            "subtotal": fmt(item.subtotal),
        })
    return {
        "order_number": order.order_number,
        "status": order.status,
        "status_display": order.get_status_display(),
        "payment_method": order.payment_method,
        "payment_status": order.payment_status,
        "payment_status_display": order.get_payment_status_display(),
        "full_name": order.full_name,
        "phone": order.phone,
        "delivery_address": order.delivery_address,
        "subtotal": fmt(order.subtotal),
        "delivery_fee": fmt(order.delivery_fee),
        "total_amount": fmt(order.total_amount),
        "items": items,
        "item_count": len(items),
        "created_at": order.created_at.isoformat(),
        "updated_at": order.updated_at.isoformat(),
    }
