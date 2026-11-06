from django.contrib import admin
from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = (
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
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "order_number",
        "customer",
        "full_name",
        "total_amount",
        "status",
        "payment_status",
        "created_at",
    )
    list_filter = ("status", "payment_status", "payment_method")
    search_fields = (
        "order_number",
        "customer__username",
        "customer__email",
        "full_name",
        "phone",
    )
    ordering = ("-created_at",)
    date_hierarchy = "created_at"
    inlines = [OrderItemInline]

    readonly_fields = (
        "order_number",
        "customer",
        "subtotal",
        "delivery_fee",
        "total_amount",
        "created_at",
        "updated_at",
    )

    fieldsets = (
        ("Order Info", {"fields": ("order_number", "customer", "created_at", "updated_at")}),
        ("Delivery", {"fields": ("full_name", "phone", "delivery_address")}),
        ("Financials", {"fields": ("subtotal", "delivery_fee", "total_amount")}),
        ("Status", {"fields": ("status", "payment_method", "payment_status")}),
    )

    def get_readonly_fields(self, request, obj=None):
        readonly = list(self.readonly_fields)
        if obj and not request.user.is_superuser and request.user.role != "admin":
            readonly.append("payment_status")
        return readonly

    def has_delete_permission(self, request, obj=None):
        if obj and obj.status in (Order.Status.DELIVERED, Order.Status.SHIPPED):
            return request.user.is_superuser
        return super().has_delete_permission(request, obj)
