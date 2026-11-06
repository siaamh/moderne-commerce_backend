from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsCustomer
from apps.products.models import Product
from .models import Cart, CartItem
from .serializers import (
    CartItemAddSerializer,
    CartItemSerializer,
    CartItemUpdateSerializer,
    CartSerializer,
)


def success_response(message, data=None, status_code=status.HTTP_200_OK):
    payload = {"success": True, "message": message}
    if data is not None:
        payload["data"] = data
    return Response(payload, status=status_code)


def error_response(message, errors=None, status_code=status.HTTP_400_BAD_REQUEST):
    payload = {"success": False, "message": message}
    if errors is not None:
        payload["errors"] = errors
    return Response(payload, status=status_code)


def get_or_create_cart(user):
    cart, _ = Cart.objects.get_or_create(customer=user)
    return cart


class CartView(APIView):
    """
    GET /api/v1/cart/ — retrieve the authenticated customer's cart.

    The cart is created on first access.
    """

    permission_classes = [IsCustomer]

    def get(self, request):
        cart = get_or_create_cart(request.user)
        serializer = CartSerializer(cart)
        return success_response("Cart retrieved successfully.", serializer.data)


class CartItemAddView(APIView):
    """
    POST /api/v1/cart/items/ — add a product to the cart.

    If the product already exists in the cart, quantities are merged.
    """

    permission_classes = [IsCustomer]

    def post(self, request):
        serializer = CartItemAddSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("Invalid cart item data.", serializer.errors)

        product = Product.objects.get(pk=serializer.validated_data["product_id"])
        quantity = serializer.validated_data["quantity"]
        cart = get_or_create_cart(request.user)

        existing = cart.items.filter(product=product).first()
        if existing:
            new_qty = existing.quantity + quantity
            if new_qty > product.stock:
                return error_response(
                    f"Cannot add {quantity} more unit(s). "
                    f"Only {product.stock - existing.quantity} additional unit(s) available."
                )
            existing.quantity = new_qty
            existing.save()
            item = existing
        else:
            item = CartItem.objects.create(cart=cart, product=product, quantity=quantity)

        return success_response(
            "Item added to cart.",
            CartItemSerializer(item).data,
            status.HTTP_201_CREATED,
        )


class CartItemDetailView(APIView):
    """
    PATCH  /api/v1/cart/items/<id>/ — update quantity of a cart item
    DELETE /api/v1/cart/items/<id>/ — remove a cart item
    """

    permission_classes = [IsCustomer]

    def _get_item(self, request, pk):
        """Return the cart item only if it belongs to the requesting customer."""
        try:
            return CartItem.objects.select_related("product", "cart__customer").get(
                pk=pk, cart__customer=request.user
            )
        except CartItem.DoesNotExist:
            return None

    def patch(self, request, pk):
        item = self._get_item(request, pk)
        if item is None:
            return error_response("Cart item not found.", status_code=status.HTTP_404_NOT_FOUND)

        serializer = CartItemUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("Invalid data.", serializer.errors)

        quantity = serializer.validated_data["quantity"]
        if quantity > item.product.stock:
            return error_response(
                f"Only {item.product.stock} unit(s) available in stock.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        item.quantity = quantity
        item.save()
        return success_response("Cart item updated.", CartItemSerializer(item).data)

    def delete(self, request, pk):
        item = self._get_item(request, pk)
        if item is None:
            return error_response("Cart item not found.", status_code=status.HTTP_404_NOT_FOUND)
        item.delete()
        return success_response("Cart item removed.", status_code=status.HTTP_204_NO_CONTENT)
