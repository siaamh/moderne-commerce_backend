from decimal import Decimal

from rest_framework import serializers

from apps.products.models import Product
from apps.products.pricing import get_price_info
from .models import Cart, CartItem


class CartItemSerializer(serializers.ModelSerializer):
    """
    Read serializer for a cart item.
    All prices are computed server-side via the pricing service.
    """

    product_name = serializers.CharField(source="product.name", read_only=True)
    product_image = serializers.ImageField(source="product.image", read_only=True)
    original_price = serializers.SerializerMethodField()
    discount_type = serializers.SerializerMethodField()
    discount_amount = serializers.SerializerMethodField()
    final_unit_price = serializers.SerializerMethodField()
    subtotal = serializers.SerializerMethodField()
    is_discounted = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = (
            "id",
            "product",
            "product_name",
            "product_image",
            "original_price",
            "discount_type",
            "discount_amount",
            "final_unit_price",
            "quantity",
            "subtotal",
            "is_discounted",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def _price_info(self, obj):
        # Cache per-instance to avoid multiple calls within one serialization.
        if not hasattr(obj, "_cached_price_info"):
            obj._cached_price_info = get_price_info(obj.product)
        return obj._cached_price_info

    def get_original_price(self, obj):
        return str(self._price_info(obj).original_price)

    def get_discount_type(self, obj):
        return self._price_info(obj).discount_type

    def get_discount_amount(self, obj):
        return str(self._price_info(obj).discount_amount)

    def get_final_unit_price(self, obj):
        return str(self._price_info(obj).final_price)

    def get_subtotal(self, obj):
        return str(self._price_info(obj).final_price * obj.quantity)

    def get_is_discounted(self, obj):
        return self._price_info(obj).is_discounted


class CartItemAddSerializer(serializers.Serializer):
    """Validates the payload when adding an item to the cart."""

    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)

    def validate_product_id(self, value):
        try:
            product = Product.objects.get(pk=value, is_active=True)
        except Product.DoesNotExist:
            raise serializers.ValidationError("Product not found or not available.")
        self._product = product
        return value

    def validate(self, attrs):
        product = getattr(self, "_product", None)
        if product and attrs["quantity"] > product.stock:
            raise serializers.ValidationError(
                {"quantity": f"Only {product.stock} unit(s) available in stock."}
            )
        return attrs


class CartItemUpdateSerializer(serializers.Serializer):
    """Validates the payload when updating an existing cart item's quantity."""

    quantity = serializers.IntegerField(min_value=1)


class CartSerializer(serializers.ModelSerializer):
    """
    Full cart serializer.
    total is computed from final (discounted) prices, not original prices.
    """

    items = CartItemSerializer(many=True, read_only=True)
    total = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ("id", "items", "total", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")

    def get_total(self, obj):
        total = Decimal("0.00")
        for item in obj.items.select_related("product").prefetch_related("product__discounts"):
            info = get_price_info(item.product)
            total += info.final_price * item.quantity
        return str(total)
