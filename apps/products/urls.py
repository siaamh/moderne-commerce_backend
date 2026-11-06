from django.urls import path

from .views import (
    BrandDetailView,
    BrandListView,
    BrandManageDetailView,
    BrandManageView,
    BrandProductsView,
    CategoryDetailManageView,
    CategoryDetailView,
    CategoryListView,
    CategoryManageView,
    DiscountManageDetailView,
    DiscountManageView,
    FeaturedProductListView,
    OfferListView,
    ProductDetailView,
    ProductListView,
    ProductManageDetailView,
    ProductManageListView,
    UpcomingOfferListView,
)

# --------------------------------------------------------------------------
# Product URLs  →  mounted at /api/v1/products/
# --------------------------------------------------------------------------
urlpatterns = [
    # Public
    path("", ProductListView.as_view(), name="product-list"),
    path("featured/", FeaturedProductListView.as_view(), name="product-featured"),
    path("<slug:slug>/", ProductDetailView.as_view(), name="product-detail"),

    # Staff / Admin management
    path("manage/", ProductManageListView.as_view(), name="product-manage-list"),
    path("manage/<slug:slug>/", ProductManageDetailView.as_view(), name="product-manage-detail"),
]

# --------------------------------------------------------------------------
# Category URLs  →  mounted at /api/v1/categories/
# --------------------------------------------------------------------------
category_urlpatterns = [
    path("", CategoryListView.as_view(), name="category-list"),
    path("<slug:slug>/", CategoryDetailView.as_view(), name="category-detail"),

    # Admin management
    path("manage/", CategoryManageView.as_view(), name="category-manage-list"),
    path("manage/<slug:slug>/", CategoryDetailManageView.as_view(), name="category-manage-detail"),
]

# --------------------------------------------------------------------------
# Brand URLs  →  mounted at /api/v1/brands/
# --------------------------------------------------------------------------
brand_urlpatterns = [
    path("", BrandListView.as_view(), name="brand-list"),
    path("<slug:slug>/", BrandDetailView.as_view(), name="brand-detail"),
    path("<slug:slug>/products/", BrandProductsView.as_view(), name="brand-products"),

    # Admin management
    path("manage/", BrandManageView.as_view(), name="brand-manage-list"),
    path("manage/<slug:slug>/", BrandManageDetailView.as_view(), name="brand-manage-detail"),
]

# --------------------------------------------------------------------------
# Offer URLs  →  mounted at /api/v1/offers/
# --------------------------------------------------------------------------
offer_urlpatterns = [
    path("", OfferListView.as_view(), name="offer-list"),
    path("upcoming/", UpcomingOfferListView.as_view(), name="offer-upcoming"),
]

# --------------------------------------------------------------------------
# Discount management URLs  →  mounted at /api/v1/discounts/
# --------------------------------------------------------------------------
discount_urlpatterns = [
    path("", DiscountManageView.as_view(), name="discount-manage-list"),
    path("<int:pk>/", DiscountManageDetailView.as_view(), name="discount-manage-detail"),
]
