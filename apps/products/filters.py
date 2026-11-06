import django_filters
from django.db.models import Q
from django.utils import timezone

from .models import Product


class ProductFilter(django_filters.FilterSet):
    """
    Supports filtering by category (root or subcategory slug), brand slug,
    featured flag, discounted flag, and price range.
    """

    # Filter by root category slug — matches products in that category OR any of its children.
    category = django_filters.CharFilter(method="filter_category")

    # Filter by subcategory slug directly.
    subcategory = django_filters.CharFilter(
        field_name="category__slug", lookup_expr="iexact"
    )

    brand = django_filters.CharFilter(field_name="brand__slug", lookup_expr="iexact")
    is_featured = django_filters.BooleanFilter(field_name="is_featured")
    discounted = django_filters.BooleanFilter(method="filter_discounted")
    min_price = django_filters.NumberFilter(field_name="price", lookup_expr="gte")
    max_price = django_filters.NumberFilter(field_name="price", lookup_expr="lte")

    class Meta:
        model = Product
        fields = ["category", "subcategory", "brand", "is_featured", "discounted", "min_price", "max_price"]

    def filter_category(self, queryset, name, value):
        """
        When given a root category slug, return products in that root category
        OR any of its direct children (subcategories).
        """
        return queryset.filter(
            Q(category__slug__iexact=value) |
            Q(category__parent__slug__iexact=value)
        )

    def filter_discounted(self, queryset, name, value):
        """
        Filter products that currently have an active discount.
        """
        now = timezone.now()
        has_discount = queryset.filter(
            discounts__is_active=True,
            discounts__starts_at__lte=now,
            discounts__ends_at__gt=now,
        )
        no_discount = queryset.exclude(
            discounts__is_active=True,
            discounts__starts_at__lte=now,
            discounts__ends_at__gt=now,
        )
        if value:
            return has_discount.distinct()
        return no_discount.distinct()
