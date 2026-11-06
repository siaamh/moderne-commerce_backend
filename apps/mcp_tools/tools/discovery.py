"""
MCP tool implementations: list_categories, search_brands,
get_featured_products, get_active_offers
"""
from django.db.models import Count, Q
from django.utils import timezone

from apps.products.models import Brand, Category, Discount, Product
from apps.products.pricing import get_price_info
from apps.mcp_tools.utils import error, fmt, format_product, image_url, success


def list_categories(
    parent_id: int | None = None,
    include_subcategories: bool = True,
) -> dict:
    """
    List product categories. Use when the user asks to browse, explore or see
    available categories or product types. Returns the active category hierarchy.
    Set parent_id to get subcategories of a specific category.
    Set include_subcategories=True (default) to nest child categories.
    """
    qs = Category.objects.filter(is_active=True).prefetch_related("children")

    if parent_id is not None:
        qs = qs.filter(parent_id=parent_id)
    else:
        qs = qs.filter(parent__isnull=True)

    qs = qs.order_by("order", "name")

    categories = []
    for cat in qs:
        entry = {
            "id": cat.id,
            "name": cat.name,
            "slug": cat.slug,
            "description": cat.description,
            "image_url": image_url(cat.image.name if cat.image else None),
            "order": cat.order,
            "children": [],
        }
        if include_subcategories:
            for child in cat.children.filter(is_active=True).order_by("order", "name"):
                entry["children"].append({
                    "id": child.id,
                    "name": child.name,
                    "slug": child.slug,
                    "description": child.description,
                    "image_url": image_url(child.image.name if child.image else None),
                    "order": child.order,
                })
        categories.append(entry)

    return success({"count": len(categories), "categories": categories})


def search_brands(
    query: str | None = None,
    limit: int = 20,
) -> dict:
    """
    Search or list brands. Use when the user asks about brands, mentions a brand
    name, or wants to browse by brand. Returns active brands with product counts.
    After finding a brand, use search_products with brand_slug to get its products.
    """
    limit = min(max(1, int(limit)), 50)

    qs = Brand.objects.filter(is_active=True).annotate(
        product_count=Count("products", filter=Q(products__is_active=True))
    )

    if query:
        qs = qs.filter(name__icontains=query)

    qs = qs.order_by("name")[:limit]

    brands = []
    for brand in qs:
        brands.append({
            "id": brand.id,
            "name": brand.name,
            "slug": brand.slug,
            "description": brand.description,
            "logo_url": image_url(brand.logo.name if brand.logo else None),
            "product_count": brand.product_count,
        })

    return success({"count": len(brands), "brands": brands})


def get_featured_products(
    limit: int = 8,
    category_slug: str | None = None,
) -> dict:
    """
    Get featured/curated products. Use when the user asks for recommended products,
    featured items, top picks, or bestsellers. Returns active in-stock featured
    products in configured display order.
    """
    limit = min(max(1, int(limit)), 20)

    qs = (
        Product.objects.filter(is_active=True, is_featured=True, stock__gt=0)
        .select_related("category", "category__parent", "brand")
        .prefetch_related("discounts")
    )

    if category_slug:
        qs = qs.filter(
            Q(category__slug__iexact=category_slug) |
            Q(category__parent__slug__iexact=category_slug)
        )

    qs = qs.order_by("featured_order", "-created_at")[:limit]

    results = []
    for product in qs:
        info = get_price_info(product)
        results.append(format_product(product, info))

    return success({"count": len(results), "products": results})


def get_active_offers(
    category_slug: str | None = None,
    brand_slug: str | None = None,
    limit: int = 10,
) -> dict:
    """
    Get current limited-time discount offers. Use when the user asks about sales,
    discounts, deals, promotions, or what's on offer. Returns only currently active
    offers with real expiration timestamps and discounted prices.
    Do NOT use this for general product search — use search_products instead.
    """
    limit = min(max(1, int(limit)), 50)
    now = timezone.now()

    qs = (
        Discount.objects.filter(
            is_active=True,
            starts_at__lte=now,
            ends_at__gt=now,
            product__is_active=True,
        )
        .select_related(
            "product", "product__brand", "product__category", "product__category__parent"
        )
        .prefetch_related("product__discounts")
    )

    if category_slug:
        qs = qs.filter(
            Q(product__category__slug__iexact=category_slug) |
            Q(product__category__parent__slug__iexact=category_slug)
        )

    if brand_slug:
        qs = qs.filter(product__brand__slug__iexact=brand_slug)

    qs = qs.order_by("ends_at")[:limit]

    offers = []
    for discount in qs:
        product = discount.product
        info = get_price_info(product)
        remaining = max(int((discount.ends_at - now).total_seconds()), 0)
        offers.append({
            "offer_id": discount.id,
            "title": discount.title,
            "description": discount.description,
            "product_id": product.id,
            "product_name": product.name,
            "product_slug": product.slug,
            "product_image": image_url(product.image.name if product.image else None),
            "brand_name": product.brand.name if product.brand else None,
            "category_name": product.category.name if product.category else None,
            "discount_type": discount.discount_type,
            "discount_value": fmt(discount.value),
            "original_price": fmt(info.original_price),
            "final_price": fmt(info.final_price),
            "discount_amount": fmt(info.discount_amount),
            "starts_at": discount.starts_at.isoformat(),
            "ends_at": discount.ends_at.isoformat(),
            "remaining_seconds": remaining,
            "stock": product.stock,
            "in_stock": product.stock > 0,
        })

    return success({"count": len(offers), "offers": offers})
