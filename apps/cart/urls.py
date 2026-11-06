from django.urls import path
from .views import CartItemAddView, CartItemDetailView, CartView

urlpatterns = [
    path("", CartView.as_view(), name="cart-detail"),
    path("items/", CartItemAddView.as_view(), name="cart-item-add"),
    path("items/<int:pk>/", CartItemDetailView.as_view(), name="cart-item-detail"),
]
