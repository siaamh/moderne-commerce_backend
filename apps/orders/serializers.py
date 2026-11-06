from rest_framework import serializers
from .models import Order, OrderItem


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = (
            "id",
            "product",
            "product_name",
            "original_unit_price",
            "discount_type",
            "discount_value",
            "discount_amount",
            "unit_price",
            "quantity",
            "subtotal",
        )
        read_only_fields = fields


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    payment_status_display = serializers.CharField(
        source="get_payment_status_display", read_only=True
    )

    class Meta:
        model = Order
        fields = (
            "id",
            "order_number",
            "full_name",
            "phone",
            "delivery_address",
            "subtotal",
            "delivery_fee",
            "total_amount",
            "status",
            "status_display",
            "payment_method",
            "payment_status",
            "payment_status_display",
            "items",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class OrderCreateSerializer(serializers.Serializer):
    """Input serializer for placing a new order."""

    full_name = serializers.CharField(max_length=200)
    phone = serializers.CharField(max_length=30)
    delivery_address = serializers.CharField()
