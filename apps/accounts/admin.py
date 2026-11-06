from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Custom UserAdmin that surfaces the application role field.

    - Role assignment is restricted to superusers or is_staff users
      with the appropriate Django permission (change_user).
    - Passwords are never displayed.
    """

    list_display = ("username", "email", "first_name", "last_name", "role", "is_active", "date_joined")
    list_filter = ("role", "is_active", "is_staff", "is_superuser")
    search_fields = ("username", "email", "first_name", "last_name")
    ordering = ("-date_joined",)

    # Fieldsets add the role to the standard UserAdmin layout.
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (_("Personal info"), {"fields": ("first_name", "last_name", "email")}),
        (
            _("Application role"),
            {
                "fields": ("role",),
                "description": (
                    "The application-level role controls what the user can do in the API. "
                    "Django Admin access is controlled separately by 'Staff status' below."
                ),
            },
        ),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "username",
                    "email",
                    "first_name",
                    "last_name",
                    "role",
                    "password1",
                    "password2",
                    "is_active",
                    "is_staff",
                ),
            },
        ),
    )

    def get_readonly_fields(self, request, obj=None):
        """
        Non-superusers cannot modify the role of superusers, preventing
        privilege escalation through the Admin panel.
        """
        readonly = list(super().get_readonly_fields(request, obj))
        if obj and obj.is_superuser and not request.user.is_superuser:
            readonly.extend(["role", "is_superuser", "is_staff"])
        return readonly
