import os
from django.contrib.auth import get_user_model

User = get_user_model()
login_field = User.USERNAME_FIELD  # 'username' for this model
login_value = os.environ["ADMIN_LOGIN"]
password = os.environ["ADMIN_PASSWORD"]

if User.objects.filter(**{login_field: login_value}).exists():
    print("Superuser already exists")
else:
    User.objects.create_superuser(
        **{login_field: login_value},
        password=password,
        email=os.environ.get("ADMIN_EMAIL", ""),
        role="admin",
    )
    
    print("Superuser created")
