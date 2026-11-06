from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import LoginView, LogoutView, MeView, RegisterView

urlpatterns = [
    # Registration / profile
    path("register/", RegisterView.as_view(), name="accounts-register"),
    path("login/", LoginView.as_view(), name="accounts-login"),
    path("logout/", LogoutView.as_view(), name="accounts-logout"),
    path("me/", MeView.as_view(), name="accounts-me"),
    # JWT token endpoints (SimpleJWT standard views)
    path("token/", TokenObtainPairView.as_view(), name="token-obtain-pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
]
