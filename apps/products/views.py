from django.utils import timezone
from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAdminRole, IsStaffOrAdminRole
from .filters import ProductFilter
from .models import Brand, Category, Discount, Product
from .serializers import (
    BrandSerializer,
    BrandWriteSerializer,
    CategorySerializer,
    CategoryWriteSerializer,
    DiscountSerializer,
    OfferSerializer,
    ProductSerializer,
    ProductWriteSerializer,
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


def _product_qs_public():
    """Standard public queryset: active only, with all relations prefetched."""
    return (
        Product.objects.filter(is_active=True)
        .select_related("category", "category__parent", "brand")
        .prefetch_related("discounts")
    )


def _product_qs_all():
    """Full queryset for staff/admin: all products."""
    return (
        Product.objects.all()
        .select_related("category", "category__parent", "brand")
        .prefetch_related("discounts")
    )


# ---------------------------------------------------------------------------
# Category views
# ---------------------------------------------------------------------------

class CategoryListView(generics.ListAPIView):
    """
    GET /api/v1/categories/
    Public list of active root categories with their active subcategories.
    """

    permission_classes = [AllowAny]
    serializer_class = CategorySerializer

    def get_queryset(self):
        return (
            Category.objects.filter(is_active=True, parent__isnull=True)
            .prefetch_related("children")
            .order_by("order", "name")
        )


class CategoryDetailView(generics.RetrieveAPIView):
    """GET /api/v1/categories/<slug>/ — public category detail with children."""

    permission_classes = [AllowAny]
    serializer_class = CategorySerializer
    lookup_field = "slug"

    def get_queryset(self):
        return Category.objects.filter(is_active=True).prefetch_related("children")


class CategoryManageView(generics.ListCreateAPIView):
    """Admin: list all categories (including inactive) and create new ones."""

    permission_classes = [IsAdminRole]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return CategoryWriteSerializer
        return CategorySerializer

    def get_queryset(self):
        return Category.objects.all().prefetch_related("children").order_by("order", "name")

    def create(self, request, *args, **kwargs):
        serializer = CategoryWriteSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("Validation failed.", serializer.errors)
        category = serializer.save()
        return Response(
            {"success": True, "message": "Category created.", "data": CategorySerializer(category).data},
            status=status.HTTP_201_CREATED,
        )


class CategoryDetailManageView(generics.RetrieveUpdateDestroyAPIView):
    """Admin: retrieve, update, or delete a single category."""

    permission_classes = [IsAdminRole]
    lookup_field = "slug"

    def get_serializer_class(self):
        if self.request.method in ("PUT", "PATCH"):
            return CategoryWriteSerializer
        return CategorySerializer

    def get_queryset(self):
        return Category.objects.all().prefetch_related("children")


# ---------------------------------------------------------------------------
# Brand views
# ---------------------------------------------------------------------------

class BrandListView(generics.ListAPIView):
    """GET /api/v1/brands/ — public list of active brands."""

    permission_classes = [AllowAny]
    serializer_class = BrandSerializer
    search_fields = ["name", "description"]
    ordering_fields = ["name", "created_at"]
    ordering = ["name"]

    def get_queryset(self):
        return Brand.objects.filter(is_active=True)


class BrandDetailView(generics.RetrieveAPIView):
    """GET /api/v1/brands/<slug>/ — public brand detail."""

    permission_classes = [AllowAny]
    serializer_class = BrandSerializer
    lookup_field = "slug"

    def get_queryset(self):
        return Brand.objects.filter(is_active=True)


class BrandProductsView(generics.ListAPIView):
    """GET /api/v1/brands/<slug>/products/ — active products for a brand."""

    permission_classes = [AllowAny]
    serializer_class = ProductSerializer
    search_fields = ["name", "description"]
    ordering_fields = ["price", "created_at", "name"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return (
            _product_qs_public()
            .filter(brand__slug=self.kwargs["slug"])
        )


class BrandManageView(generics.ListCreateAPIView):
    """Admin: list all brands and create new ones."""

    permission_classes = [IsAdminRole]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return BrandWriteSerializer
        return BrandSerializer

    def get_queryset(self):
        return Brand.objects.all()

    def create(self, request, *args, **kwargs):
        serializer = BrandWriteSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("Validation failed.", serializer.errors)
        brand = serializer.save()
        return Response(
            {"success": True, "message": "Brand created.", "data": BrandSerializer(brand).data},
            status=status.HTTP_201_CREATED,
        )


class BrandManageDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Admin: retrieve, update, or delete a brand."""

    permission_classes = [IsAdminRole]
    lookup_field = "slug"

    def get_serializer_class(self):
        if self.request.method in ("PUT", "PATCH"):
            return BrandWriteSerializer
        return BrandSerializer

    def get_queryset(self):
        return Brand.objects.all()


# ---------------------------------------------------------------------------
# Product views
# ---------------------------------------------------------------------------

class ProductListView(generics.ListAPIView):
    """
    GET /api/v1/products/
    Public, paginated, filterable product list (active products only).
    """

    permission_classes = [AllowAny]
    serializer_class = ProductSerializer
    filterset_class = ProductFilter
    search_fields = ["name", "description", "brand__name", "category__name"]
    ordering_fields = ["price", "created_at", "name", "featured_order"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return _product_qs_public()


class ProductDetailView(generics.RetrieveAPIView):
    """GET /api/v1/products/<slug>/ — public product detail."""

    permission_classes = [AllowAny]
    serializer_class = ProductSerializer
    lookup_field = "slug"

    def get_queryset(self):
        return _product_qs_public()


class FeaturedProductListView(generics.ListAPIView):
    """
    GET /api/v1/products/featured/
    Active, in-stock featured products ordered by featured_order.
    """

    permission_classes = [AllowAny]
    serializer_class = ProductSerializer
    ordering = ["featured_order", "-created_at"]

    def get_queryset(self):
        return (
            _product_qs_public()
            .filter(is_featured=True, stock__gt=0)
            .order_by("featured_order", "-created_at")
        )


class ProductManageListView(generics.ListCreateAPIView):
    """Staff/Admin: list all products (including inactive) and create new ones."""

    permission_classes = [IsStaffOrAdminRole]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return ProductWriteSerializer
        return ProductSerializer

    def get_queryset(self):
        return _product_qs_all()

    def create(self, request, *args, **kwargs):
        serializer = ProductWriteSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"success": False, "message": "Validation failed.", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        product = serializer.save()
        out_qs = _product_qs_all().filter(pk=product.pk).first()
        return Response(
            {
                "success": True,
                "message": "Product created successfully.",
                "data": ProductSerializer(out_qs, context={"request": request}).data,
            },
            status=status.HTTP_201_CREATED,
        )


class ProductManageDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Staff/Admin: retrieve, update, or delete any product."""

    permission_classes = [IsStaffOrAdminRole]
    lookup_field = "slug"

    def get_serializer_class(self):
        if self.request.method in ("PUT", "PATCH"):
            return ProductWriteSerializer
        return ProductSerializer

    def get_queryset(self):
        return _product_qs_all()


# ---------------------------------------------------------------------------
# Discount management (Admin only)
# ---------------------------------------------------------------------------

class DiscountManageView(generics.ListCreateAPIView):
    """Admin: list all discounts and create new ones."""

    permission_classes = [IsAdminRole]
    serializer_class = DiscountSerializer

    def get_queryset(self):
        return Discount.objects.select_related("product").order_by("-starts_at")

    def create(self, request, *args, **kwargs):
        serializer = DiscountSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("Validation failed.", serializer.errors)
        discount = serializer.save()
        return Response(
            {"success": True, "message": "Discount created.", "data": DiscountSerializer(discount).data},
            status=status.HTTP_201_CREATED,
        )


class DiscountManageDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Admin: retrieve, update, or delete a discount."""

    permission_classes = [IsAdminRole]
    serializer_class = DiscountSerializer

    def get_queryset(self):
        return Discount.objects.select_related("product")


# ---------------------------------------------------------------------------
# Offers (public) — reuses Discount model
# ---------------------------------------------------------------------------

class OfferListView(generics.ListAPIView):
    """
    GET /api/v1/offers/
    Currently active limited-time offers (window includes now).
    """

    permission_classes = [AllowAny]
    serializer_class = OfferSerializer

    def get_queryset(self):
        now = timezone.now()
        return (
            Discount.objects.filter(
                is_active=True,
                starts_at__lte=now,
                ends_at__gt=now,
            )
            .select_related("product")
            .order_by("ends_at")  # soonest-expiring first
        )


class UpcomingOfferListView(generics.ListAPIView):
    """
    GET /api/v1/offers/upcoming/
    Offers that are active (flag) but have not started yet.
    """

    permission_classes = [AllowAny]
    serializer_class = OfferSerializer

    def get_queryset(self):
        now = timezone.now()
        return (
            Discount.objects.filter(
                is_active=True,
                starts_at__gt=now,
            )
            .select_related("product")
            .order_by("starts_at")
        )
