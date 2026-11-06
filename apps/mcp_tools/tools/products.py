"""
MCP tool implementations: search_products, get_product_details
"""
from django.db.models import Q
from django.utils import timezone

from apps.products.models import Product
from apps.products.pricing import get_price_info
from apps.mcp_tools.utils import error, format_product, success


def search_products(
    query: str | None = None,
    brand_slug: str | None = None,
    category_slug: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    discounted_only: bool = False,
    featured_only: bool = False,
    limit: int = 10,
) -> dict:
    """
    Search the product catalog. Use when the user asks to find, browse or search
    for products by name, category, brand, price range, or discount status.
    Returns products with current backend-calculated prices and stock status.
    Supports: query (text search), brand_slug, category_slug, min_price, max_price,
    discounted_only (only items currently on sale), featured_only (curated picks).
    """
    limit = min(max(1, int(limit)), 20)

    qs = (
        Product.objects.filter(is_active=True)
        .select_related("category", "category__parent", "brand")
        .prefetch_related("discounts")
    )

    if query:
        qs = qs.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        )

    if brand_slug:
        qs = qs.filter(brand__slug__iexact=brand_slug)

    if category_slug:
        qs = qs.filter(
            Q(category__slug__iexact=category_slug) |
            Q(category__parent__slug__iexact=category_slug)
        )

    if min_price is not None:
        qs = qs.filter(price__gte=min_price)

    if max_price is not None:
        qs = qs.filter(price__lte=max_price)

    if featured_only:
        qs = qs.filter(is_featured=True, stock__gt=0)

    if discounted_only:
        now = timezone.now()
        qs = qs.filter(
            discounts__is_active=True,
            discounts__starts_at__lte=now,
            discounts__ends_at__gt=now,
        ).distinct()

    qs = qs[:limit]
    products = list(qs)

    results = []
    for product in products:
        info = get_price_info(product)
        results.append(format_product(product, info))

    return success({
        "count": len(results),
        "products": results,
    })


def get_product_details(
    product_id: int | None = None,
    slug: str | None = None,
) -> dict:
    """
    Get full details for a single product. Use when the user asks about a specific
    product, wants to see its description, price, stock, brand, category, or
    current discount/offer details. Requires either product_id or slug.
    """
    if not product_id and not slug:
        return error("INVALID_INPUT", "Provide either product_id or slug.")

    try:
        qs = (
            Product.objects.filter(is_active=True)
            .select_related("category", "category__parent", "brand")
            .prefetch_related("discounts")
        )
        if product_id:
            product = qs.get(pk=product_id)
        else:
            product = qs.get(slug=slug)
    except Product.DoesNotExist:
        return error("PRODUCT_NOT_FOUND", f"Product not found.")

    info = get_price_info(product)

    category_data = None
    if product.category:
        category_data = {
            "id": product.category.id,
            "name": product.category.name,
            "slug": product.category.slug,
            "parent_name": product.category.parent.name if product.category.parent else None,
            "parent_slug": product.category.parent.slug if product.category.parent else None,
        }

    brand_data = None
    if product.brand:
        brand_data = {
            "id": product.brand.id,
            "name": product.brand.name,
            "slug": product.brand.slug,
        }

    from apps.mcp_tools.utils import fmt, image_url, format_pricing
    return success({
        "id": product.id,
        "name": product.name,
        "slug": product.slug,
        "description": product.description,
        "image_url": image_url(product.image.name if product.image else None),
        "stock": product.stock,
        "in_stock": product.stock > 0,
        "is_featured": product.is_featured,
        "brand": brand_data,
        "category": category_data,
        "price": fmt(product.price),
        **format_pricing(info),
    })
