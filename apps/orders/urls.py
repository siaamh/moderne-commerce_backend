from django.urls import path
from .views import OrderCancelView, OrderDetailView, OrderListCreateView, OrderStatusUpdateView

urlpatterns = [
    path("", OrderListCreateView.as_view(), name="order-list-create"),
    path("<str:order_number>/", OrderDetailView.as_view(), name="order-detail"),
    path("<str:order_number>/cancel/", OrderCancelView.as_view(), name="order-cancel"),
    path("<str:order_number>/status/", OrderStatusUpdateView.as_view(), name="order-status-update"),
]
