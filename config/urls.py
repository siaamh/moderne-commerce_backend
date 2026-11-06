"""
Root URL configuration.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from apps.products.urls import (
    brand_urlpatterns,
    category_urlpatterns,
    discount_urlpatterns,
    offer_urlpatterns,
)

urlpatterns = [
    path("admin/", admin.site.urls),

    # Accounts & auth
    path("api/v1/accounts/", include("apps.accounts.urls")),

    # Products (public list/detail + staff manage)
    path("api/v1/products/", include("apps.products.urls")),

    # Categories (public + admin manage)
    path("api/v1/categories/", include(category_urlpatterns)),

    # Brands (public + admin manage)
    path("api/v1/brands/", include(brand_urlpatterns)),

    # Offers (public active + upcoming)
    path("api/v1/offers/", include(offer_urlpatterns)),

    # Discounts (admin manage)
    path("api/v1/discounts/", include(discount_urlpatterns)),

    # Cart & Orders
    path("api/v1/cart/", include("apps.cart.urls")),
    path("api/v1/orders/", include("apps.orders.urls")),

    # AI Chat / MCP tools
    path("api/v1/", include("apps.mcp_tools.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
