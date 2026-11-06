"""
Management command: seed_admins

Creates a small set of default admin/staff accounts for development
and initial deployment. Existing accounts are skipped (idempotent).

Usage:
    python manage.py seed_admins

WARNING: These accounts use weak passwords intentionally for local
development. Change all passwords immediately in any shared or
production environment.
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

User = get_user_model()

# ---------------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------------
SEED_USERS = [
    {
        "username": "admin",
        "email": "admin@example.com",
        "password": "admin",
        "first_name": "Super",
        "last_name": "Admin",
        "role": User.Role.ADMIN,
        "is_staff": True,
        "is_superuser": True,
    },
    {
        "username": "staff",
        "email": "staff@example.com",
        "password": "123456",
        "first_name": "Staff",
        "last_name": "User",
        "role": User.Role.STAFF,
        "is_staff": True,
        "is_superuser": False,
    },
]


class Command(BaseCommand):
    help = (
        "Seed default admin and staff accounts for development. "
        "Existing usernames are skipped. "
        "CHANGE PASSWORDS BEFORE GOING TO PRODUCTION."
    )

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("⚠  Seeding admin accounts with weak passwords."))
        self.stdout.write(self.style.WARNING("   Change passwords before deploying to production.\n"))

        for data in SEED_USERS:
            username = data["username"]
            if User.objects.filter(username=username).exists():
                self.stdout.write(f"  SKIP  '{username}' already exists.")
                continue

            User.objects.create_user(
                username=username,
                email=data["email"],
                password=data["password"],
                first_name=data["first_name"],
                last_name=data["last_name"],
                role=data["role"],
                is_staff=data["is_staff"],
                is_superuser=data["is_superuser"],
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"  CREATE '{username}'  role={data['role']}  password={data['password']}"
                )
            )

        self.stdout.write("\nDone.")
