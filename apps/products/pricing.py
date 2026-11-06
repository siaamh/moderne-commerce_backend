"""
Central pricing service.

This is the single source of truth for computing a product's effective price.
It is used by:
  - Product serializers (display)
  - Cart serializers (cart totals)
  - Order service (order creation snapshots)

Never compute prices anywhere else. Never trust client-submitted prices.
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Optional

from django.utils import timezone


@dataclass(frozen=True)
class PriceInfo:
    original_price: Decimal
    discount_type: Optional[str]       # "percentage" | "fixed" | None
    discount_value: Optional[Decimal]  # the raw discount value field
    discount_amount: Decimal           # actual money saved
    final_price: Decimal
    is_discounted: bool
    offer_title: Optional[str]
    offer_description: Optional[str]
    offer_start: Optional[object]      # datetime | None
    offer_end: Optional[object]        # datetime | None


def get_price_info(product) -> PriceInfo:
    """
    Compute the effective price for a product at the current moment.

    Looks up any applicable active discount whose time window includes now.
    Returns a fully populated PriceInfo regardless of whether a discount exists.

    Parameters
    ----------
    product : Product instance (must have .price and .discounts related manager)
    """
    now = timezone.now()
    original = Decimal(str(product.price))

    # Find the first applicable active discount for this product right now.
    # We use the ORM directly to ensure timezone-aware comparison happens in
    # the database, not in Python.
    applicable = (
        product.discounts
        .filter(
            is_active=True,
            starts_at__lte=now,
            ends_at__gt=now,
        )
        .order_by("-starts_at")  # most-recently-started wins if somehow multiple slip through
        .first()
    )

    if applicable is None:
        return PriceInfo(
            original_price=original,
            discount_type=None,
            discount_value=None,
            discount_amount=Decimal("0.00"),
            final_price=original,
            is_discounted=False,
            offer_title=None,
            offer_description=None,
            offer_start=None,
            offer_end=None,
        )

    discount_value = Decimal(str(applicable.value))

    if applicable.discount_type == "percentage":
        discount_amount = (original * discount_value / Decimal("100")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
    else:  # fixed
        discount_amount = discount_value

    # Guard: final price is never negative.
    final_price = max(original - discount_amount, Decimal("0.00"))

    return PriceInfo(
        original_price=original,
        discount_type=applicable.discount_type,
        discount_value=discount_value,
        discount_amount=discount_amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        final_price=final_price.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        is_discounted=True,
        offer_title=applicable.title,
        offer_description=applicable.description,
        offer_start=applicable.starts_at,
        offer_end=applicable.ends_at,
    )


def get_price_info_for_queryset(products):
    """
    Bulk-compute PriceInfo for an iterable of products.

    Expects products to have been prefetched with their discounts
    (prefetch_related("discounts")) to avoid N+1 queries.

    Returns a dict mapping product.pk → PriceInfo.
    """
    return {p.pk: get_price_info(p) for p in products}
