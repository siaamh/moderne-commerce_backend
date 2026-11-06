from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsCustomer, IsStaffOrAdminRole
from .models import Order
from .serializers import OrderCreateSerializer, OrderSerializer
from .services import OrderCreationError, cancel_order, create_order_from_cart


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


class OrderListCreateView(APIView):
    """
    POST /api/v1/orders/ — place a new order from the cart (customers only)
    GET  /api/v1/orders/ — list orders
        - Customers see only their own orders.
        - Staff/Admin see all orders.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if user.role in ("admin", "staff"):
            queryset = Order.objects.prefetch_related("items").all()
        else:
            queryset = Order.objects.prefetch_related("items").filter(customer=user)
        serializer = OrderSerializer(queryset, many=True)
        return success_response("Orders retrieved successfully.", serializer.data)

    def post(self, request):
        if request.user.role != "customer":
            return error_response(
                "Only customers can place orders.",
                status_code=status.HTTP_403_FORBIDDEN,
            )

        serializer = OrderCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("Invalid order data.", serializer.errors)

        try:
            order = create_order_from_cart(
                user=request.user,
                full_name=serializer.validated_data["full_name"],
                phone=serializer.validated_data["phone"],
                delivery_address=serializer.validated_data["delivery_address"],
            )
        except OrderCreationError as exc:
            return error_response(str(exc), status_code=status.HTTP_400_BAD_REQUEST)

        return success_response(
            "Order placed successfully.",
            OrderSerializer(order).data,
            status.HTTP_201_CREATED,
        )


class OrderDetailView(APIView):
    """
    GET /api/v1/orders/<order_number>/ — retrieve a single order.

    Customers may only see their own orders. Staff/Admin may see any order.
    """

    permission_classes = [IsAuthenticated]

    def _get_order(self, request, order_number):
        try:
            order = Order.objects.prefetch_related("items").get(order_number=order_number)
        except Order.DoesNotExist:
            return None
        user = request.user
        if user.role in ("admin", "staff"):
            return order
        if order.customer == user:
            return order
        return None

    def get(self, request, order_number):
        order = self._get_order(request, order_number)
        if order is None:
            return error_response("Order not found.", status_code=status.HTTP_404_NOT_FOUND)
        return success_response("Order retrieved successfully.", OrderSerializer(order).data)


class OrderCancelView(APIView):
    """
    POST /api/v1/orders/<order_number>/cancel/

    Customers can cancel their own pending/confirmed orders.
    Staff/Admin can cancel any cancellable order.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, order_number):
        try:
            order = Order.objects.get(order_number=order_number)
        except Order.DoesNotExist:
            return error_response("Order not found.", status_code=status.HTTP_404_NOT_FOUND)

        user = request.user
        # Customers may only cancel their own orders.
        if user.role == "customer" and order.customer != user:
            return error_response("Order not found.", status_code=status.HTTP_404_NOT_FOUND)

        try:
            updated_order = cancel_order(order, user)
        except OrderCreationError as exc:
            return error_response(str(exc), status_code=status.HTTP_400_BAD_REQUEST)

        return success_response("Order cancelled successfully.", OrderSerializer(updated_order).data)


class OrderStatusUpdateView(APIView):
    """
    PATCH /api/v1/orders/<order_number>/status/

    Staff/Admin only: update order status.
    Payment status changes are restricted to ADMIN role.
    """

    permission_classes = [IsStaffOrAdminRole]

    ALLOWED_STATUS_TRANSITIONS = {
        Order.Status.PENDING: {Order.Status.CONFIRMED, Order.Status.CANCELLED},
        Order.Status.CONFIRMED: {Order.Status.SHIPPED, Order.Status.CANCELLED},
        Order.Status.SHIPPED: {Order.Status.DELIVERED},
        Order.Status.DELIVERED: set(),
        Order.Status.CANCELLED: set(),
    }

    def patch(self, request, order_number):
        try:
            order = Order.objects.get(order_number=order_number)
        except Order.DoesNotExist:
            return error_response("Order not found.", status_code=status.HTTP_404_NOT_FOUND)

        new_status = request.data.get("status")
        new_payment_status = request.data.get("payment_status")
        updated_fields = []

        if new_status:
            allowed = self.ALLOWED_STATUS_TRANSITIONS.get(order.status, set())
            if new_status not in allowed:
                return error_response(
                    f"Cannot transition from '{order.status}' to '{new_status}'."
                )
            order.status = new_status
            updated_fields.append("status")

        if new_payment_status:
            if request.user.role != "admin":
                return error_response(
                    "Only admins can change payment status.",
                    status_code=status.HTTP_403_FORBIDDEN,
                )
            if new_payment_status not in Order.PaymentStatus.values:
                return error_response(f"Invalid payment status '{new_payment_status}'.")
            order.payment_status = new_payment_status
            updated_fields.append("payment_status")

        if not updated_fields:
            return error_response("No valid fields provided for update.")

        updated_fields.append("updated_at")
        order.save(update_fields=updated_fields)
        return success_response("Order updated successfully.", OrderSerializer(order).data)
