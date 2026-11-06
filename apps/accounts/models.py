from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom user model with application-level role support.

    Django's is_staff / is_superuser flags control Django Admin access
    and remain separate from the application role field.
    """

    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        STAFF = "staff", "Staff"
        CUSTOMER = "customer", "Customer"

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.CUSTOMER,
    )

    email = models.EmailField(unique=True)

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
        ordering = ["-date_joined"]

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

    # ------------------------------------------------------------------
    # Convenience helpers — do not use these as the sole security check;
    # enforce permissions at the view/permission layer too.
    # ------------------------------------------------------------------

    @property
    def is_admin_role(self) -> bool:
        return self.role == self.Role.ADMIN

    @property
    def is_staff_role(self) -> bool:
        return self.role == self.Role.STAFF

    @property
    def is_customer_role(self) -> bool:
        return self.role == self.Role.CUSTOMER
