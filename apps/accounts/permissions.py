"""
Reusable DRF permission classes for role-based access control.

These classes are the single source of truth for permission logic.
Views should import from here rather than duplicating checks.
"""

from rest_framework.permissions import BasePermission, IsAuthenticated


class IsAdminRole(BasePermission):
    """Allows access only to users with the ADMIN application role."""

    message = "You must have admin role to perform this action."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == "admin"
        )


class IsStaffOrAdminRole(BasePermission):
    """Allows access to users with STAFF or ADMIN application role."""

    message = "You must have staff or admin role to perform this action."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role in ("staff", "admin")
        )


class IsCustomer(BasePermission):
    """Allows access only to authenticated users with CUSTOMER role."""

    message = "You must be an authenticated customer to perform this action."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == "customer"
        )


class IsOwnerOrAdminRole(BasePermission):
    """
    Object-level permission: allows access if the requesting user owns
    the object or has the ADMIN role.

    The object must expose a `user` or `customer` attribute pointing to
    the owning User instance.
    """

    message = "You do not have permission to access this resource."

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.role == "admin":
            return True
        # Support objects with either a `user` or a `customer` FK.
        owner = getattr(obj, "user", None) or getattr(obj, "customer", None)
        return owner == request.user
