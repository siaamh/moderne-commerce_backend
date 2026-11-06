from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html

from .models import Brand, Category, Discount, Product


# ---------------------------------------------------------------------------
# Category
# ---------------------------------------------------------------------------

class SubcategoryInline(admin.TabularInline):
    model = Category
    fk_name = "parent"
    extra = 0
    fields = ("name", "slug", "is_active", "order")
    prepopulated_fields = {"slug": ("name",)}
    show_change_link = True


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "parent", "slug", "is_active", "order", "created_at")
    list_filter = ("is_active", "parent")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("order", "name")
    inlines = [SubcategoryInline]
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        (None, {"fields": ("parent", "name", "slug", "description", "image")}),
        ("Display", {"fields": ("is_active", "order")}),
        ("Timestamps", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("parent")


# ---------------------------------------------------------------------------
# Brand
# ---------------------------------------------------------------------------

@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("name",)
    readonly_fields = ("created_at", "updated_at")


# ---------------------------------------------------------------------------
# Discount inline (shown inside Product admin)
# ---------------------------------------------------------------------------

class DiscountInline(admin.TabularInline):
    model = Discount
    extra = 0
    fields = (
        "title", "discount_type", "value", "starts_at", "ends_at",
        "is_active", "is_currently_active_display",
    )
    readonly_fields = ("is_currently_active_display",)
    show_change_link = True

    @admin.display(description="Active now?", boolean=True)
    def is_currently_active_display(self, obj):
        return obj.is_currently_active


# ---------------------------------------------------------------------------
# Product
# ---------------------------------------------------------------------------

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "name", "category", "brand", "price", "stock",
        "is_active", "is_featured", "featured_order",
        "has_active_discount", "created_at",
    )
    list_filter = ("category", "brand", "is_active", "is_featured")
    search_fields = ("name", "brand__name", "category__name")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("-created_at",)
    date_hierarchy = "created_at"
    readonly_fields = ("created_at", "updated_at")
    inlines = [DiscountInline]

    fieldsets = (
        (None, {"fields": ("name", "slug", "category", "brand", "description")}),
        ("Pricing & Stock", {"fields": ("price", "stock")}),
        ("Media", {"fields": ("image",)}),
        ("Featured", {"fields": ("is_featured", "featured_order")}),
        ("Status", {"fields": ("is_active",)}),
        ("Timestamps", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    def get_queryset(self, request):
        now = timezone.now()
        qs = super().get_queryset(request).select_related("category", "brand")
        # Annotate whether the product currently has a live discount.
        from django.db.models import Exists, OuterRef
        active_discount = Discount.objects.filter(
            product=OuterRef("pk"),
            is_active=True,
            starts_at__lte=now,
            ends_at__gt=now,
        )
        return qs.annotate(_has_active_discount=Exists(active_discount))

    @admin.display(description="Discounted?", boolean=True)
    def has_active_discount(self, obj):
        return getattr(obj, "_has_active_discount", False)


# ---------------------------------------------------------------------------
# Discount (standalone)
# ---------------------------------------------------------------------------

@admin.register(Discount)
class DiscountAdmin(admin.ModelAdmin):
    list_display = (
        "title", "product", "discount_type", "value",
        "starts_at", "ends_at", "is_active", "is_currently_active_display",
    )
    list_filter = ("is_active", "discount_type")
    search_fields = ("title", "product__name")
    ordering = ("-starts_at",)
    date_hierarchy = "starts_at"
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        (None, {"fields": ("product", "title", "description")}),
        ("Discount", {"fields": ("discount_type", "value")}),
        ("Validity", {"fields": ("starts_at", "ends_at", "is_active")}),
        ("Timestamps", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    @admin.display(description="Active now?", boolean=True)
    def is_currently_active_display(self, obj):
        return obj.is_currently_active
