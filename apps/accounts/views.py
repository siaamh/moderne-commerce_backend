from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import RegisterSerializer, UserProfileSerializer

User = get_user_model()


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


class RegisterView(APIView):
    """
    POST /api/v1/accounts/register/

    Public endpoint. Always creates a CUSTOMER account.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("Registration failed.", serializer.errors)
        user = serializer.save()
        return success_response(
            "Account created successfully.",
            {"id": user.id, "username": user.username, "email": user.email},
            status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    """
    POST /api/v1/accounts/login/

    Returns a JWT access token and refresh token.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get("username", "").strip()
        password = request.data.get("password", "")

        if not username or not password:
            return error_response("Username and password are required.")

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return error_response("Invalid credentials.", status_code=status.HTTP_401_UNAUTHORIZED)

        if not user.check_password(password):
            return error_response("Invalid credentials.", status_code=status.HTTP_401_UNAUTHORIZED)

        if not user.is_active:
            return error_response("Account is disabled.", status_code=status.HTTP_403_FORBIDDEN)

        refresh = RefreshToken.for_user(user)
        return success_response(
            "Login successful.",
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "role": user.role,
                },
            },
        )


class LogoutView(APIView):
    """
    POST /api/v1/accounts/logout/

    Blacklisting is opt-in with SimpleJWT. Here we instruct the client
    to discard the tokens. A refresh token may be submitted to invalidate
    it server-side if BLACKLIST_AFTER_ROTATION is enabled.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get("refresh")
        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
            except Exception:
                # Token already expired or invalid — not a concern.
                pass
        return success_response("Logged out successfully.")


class MeView(APIView):
    """
    GET  /api/v1/accounts/me/   — retrieve own profile
    PATCH /api/v1/accounts/me/  — update own profile (role is read-only)
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserProfileSerializer(request.user, context={"request": request})
        return success_response("Profile retrieved successfully.", serializer.data)

    def patch(self, request):
        serializer = UserProfileSerializer(
            request.user,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        if not serializer.is_valid():
            return error_response("Profile update failed.", serializer.errors)
        serializer.save()
        return success_response("Profile updated successfully.", serializer.data)
