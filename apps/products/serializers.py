from rest_framework import serializers

from .models import Brand, Category, Discount, Product
from .pricing import get_price_info


# ---------------------------------------------------------------------------
# Category
# ---------------------------------------------------------------------------

class SubcategorySerializer(serializers.ModelSerializer):
    """Lightweight serializer for children shown inside a parent category."""

    class Meta:
        model = Category
        fields = ("id", "name", "slug", "description", "image", "is_active", "order")


class CategorySerializer(serializers.ModelSerializer):
    children = SubcategorySerializer(many=True, read_only=True)
    parent_name = serializers.CharField(source="parent.name", read_only=True, default=None)
    parent_slug = serializers.CharField(source="parent.slug", read_only=True, default=None)

    class Meta:
        model = Category
        fields = (
            "id",
            "parent",
            "parent_name",
            "parent_slug",
            "name",
            "slug",
            "description",
            "image",
            "is_active",
            "order",
            "children",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class CategoryWriteSerializer(serializers.ModelSerializer):
    """Used for create/update; includes parent validation."""

    class Meta:
        model = Category
        fields = ("id", "parent", "name", "slug", "description", "image", "is_active", "order")
        read_only_fields = ("id",)

    def validate_parent(self, value):
        if value and value.parent is not None:
            raise serializers.ValidationError(
                "Only one level of subcategories is supported. "
                "The selected parent is already a subcategory."
            )
        return value

    def validate(self, attrs):
        # Prevent a category from becoming its own parent.
        if self.instance and attrs.get("parent") and attrs["parent"].pk == self.instance.pk:
            raise serializers.ValidationError({"parent": "A category cannot be its own parent."})
        return attrs


# ---------------------------------------------------------------------------
# Brand
# ---------------------------------------------------------------------------

class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ("id", "name", "slug", "logo", "description", "is_active", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")


class BrandWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ("id", "name", "slug", "logo", "description", "is_active")
        read_only_fields = ("id",)


# ---------------------------------------------------------------------------
# Discount
# ---------------------------------------------------------------------------

class DiscountSerializer(serializers.ModelSerializer):
    discount_type_display = serializers.CharField(source="get_discount_type_display", read_only=True)
    is_currently_active = serializers.BooleanField(read_only=True)
    product_name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = Discount
        fields = (
            "id",
            "product",
            "product_name",
            "title",
            "description",
            "discount_type",
            "discount_type_display",
            "value",
            "starts_at",
            "ends_at",
            "is_active",
            "is_currently_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def validate(self, attrs):
        # Delegate deep validation to model.clean() via save().
        return attrs


# ---------------------------------------------------------------------------
# Pricing mixin — attached to read serializers
# ---------------------------------------------------------------------------

class PricingMixin:
    """
    Adds computed pricing fields to a product serializer.
    Expects the product instance to have .discounts prefetched.
    """

    def get_pricing(self, obj):
        info = get_price_info(obj)
        return {
            "original_price": str(info.original_price),
            "discount_type": info.discount_type,
            "discount_value": str(info.discount_value) if info.discount_value is not None else None,
            "discount_amount": str(info.discount_amount),
            "final_price": str(info.final_price),
            "is_discounted": info.is_discounted,
            "offer_title": info.offer_title,
            "offer_description": info.offer_description,
            "offer_start": info.offer_start,
            "offer_end": info.offer_end,
        }


# ---------------------------------------------------------------------------
# Product
# ---------------------------------------------------------------------------

class ProductSerializer(PricingMixin, serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True, default=None)
    category_slug = serializers.CharField(source="category.slug", read_only=True, default=None)
    brand_name = serializers.CharField(source="brand.name", read_only=True, default=None)
    brand_slug = serializers.CharField(source="brand.slug", read_only=True, default=None)
    pricing = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = (
            "id",
            "category",
            "category_name",
            "category_slug",
            "brand",
            "brand_name",
            "brand_slug",
            "name",
            "slug",
            "description",
            "price",
            "stock",
            "image",
            "is_active",
            "is_featured",
            "featured_order",
            "pricing",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class ProductWriteSerializer(serializers.ModelSerializer):
    """Used for create / update operations by admin/staff."""

    class Meta:
        model = Product
        fields = (
            "id",
            "category",
            "brand",
            "name",
            "slug",
            "description",
            "price",
            "stock",
            "image",
            "is_active",
            "is_featured",
            "featured_order",
        )
        read_only_fields = ("id",)

    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError("Price must be greater than zero.")
        return value


# ---------------------------------------------------------------------------
# Offer (public view of a Discount — limited-time offers)
# ---------------------------------------------------------------------------

class OfferSerializer(serializers.ModelSerializer):
    """
    Public-facing serializer for active and upcoming limited-time offers.
    Shows only offer metadata; final prices are resolved via the pricing service.
    """

    product_name = serializers.CharField(source="product.name", read_only=True)
    product_slug = serializers.CharField(source="product.slug", read_only=True)
    product_image = serializers.ImageField(source="product.image", read_only=True)
    discount_type_display = serializers.CharField(source="get_discount_type_display", read_only=True)
    is_currently_active = serializers.BooleanField(read_only=True)
    remaining_seconds = serializers.SerializerMethodField()

    class Meta:
        model = Discount
        fields = (
            "id",
            "product",
            "product_name",
            "product_slug",
            "product_image",
            "title",
            "description",
            "discount_type",
            "discount_type_display",
            "value",
            "starts_at",
            "ends_at",
            "is_currently_active",
            "remaining_seconds",
        )

    def get_remaining_seconds(self, obj):
        from django.utils import timezone
        now = timezone.now()
        if obj.ends_at > now > obj.starts_at:
            return max(int((obj.ends_at - now).total_seconds()), 0)
        return 0
