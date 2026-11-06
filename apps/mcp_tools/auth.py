"""
JWT → Django User resolution for MCP tool calls.
"""
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken

User = get_user_model()


class AuthError(Exception):
    pass


def resolve_user(authorization_header: str | None) -> User:
    """
    Validate a Bearer JWT and return the corresponding User.

    Raises AuthError if missing, malformed, expired or user not found.
    Never trusts a user_id supplied by the AI/tool arguments.
    """
    if not authorization_header:
        raise AuthError("Authentication required. No Authorization header provided.")

    parts = authorization_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise AuthError("Invalid Authorization header format. Expected 'Bearer <token>'.")

    raw_token = parts[1]
    try:
        token = AccessToken(raw_token)
        user_id = token["user_id"]
    except (TokenError, InvalidToken, KeyError) as exc:
        raise AuthError(f"Invalid or expired token: {exc}") from exc

    try:
        user = User.objects.get(pk=user_id, is_active=True)
    except User.DoesNotExist:
        raise AuthError("User account not found or inactive.")

    return user


def resolve_customer(authorization_header: str | None) -> User:
    """Like resolve_user but also enforces role == customer."""
    user = resolve_user(authorization_header)
    if user.role != "customer":
        raise AuthError("This action is only available to customers.")
    return user
