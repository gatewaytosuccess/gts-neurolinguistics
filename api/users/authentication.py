"""
DRF authentication against Clerk session JWTs.

The Next.js frontend sends the Clerk session token as ``Authorization: Bearer
<jwt>``. We verify it against Clerk's JWKS (RS256, cached), then resolve the
local mirror of that Clerk user.

Local rows are created lazily the first time a Clerk user calls the API, which
requires ``email`` in the token claims -- add it to the session token via
Clerk's JWT template ("Customize session token"). A Clerk webhook that syncs
user.created / user.updated is the durable path and will replace this
lazy creation once it exists.
"""

import logging

import jwt
from django.conf import settings
from rest_framework import authentication, exceptions

from .models import User, UserStatus

logger = logging.getLogger(__name__)

_jwks_client = None


def get_jwks_client():
    """Cached PyJWKClient -- Clerk's signing keys rotate, so keys are refetched."""
    global _jwks_client
    if _jwks_client is None:
        if not settings.CLERK_JWKS_URL:
            raise exceptions.AuthenticationFailed("CLERK_JWKS_URL is not configured.")
        _jwks_client = jwt.PyJWKClient(
            settings.CLERK_JWKS_URL,
            cache_keys=True,
            lifespan=settings.CLERK_JWKS_CACHE_SECONDS,
        )
    return _jwks_client


class ClerkAuthentication(authentication.BaseAuthentication):
    keyword = "Bearer"

    def authenticate(self, request):
        header = authentication.get_authorization_header(request).split()
        if not header or header[0].lower() != self.keyword.lower().encode():
            return None
        if len(header) != 2:
            raise exceptions.AuthenticationFailed("Malformed Authorization header.")

        token = header[1].decode()
        claims = self.decode_token(token)
        return self.resolve_user(claims), claims

    def decode_token(self, token):
        try:
            signing_key = get_jwks_client().get_signing_key_from_jwt(token)
            claims = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                issuer=settings.CLERK_ISSUER or None,
                options={
                    "require": ["exp", "sub"],
                    "verify_aud": False,
                    "verify_iss": bool(settings.CLERK_ISSUER),
                },
            )
        except jwt.ExpiredSignatureError:
            raise exceptions.AuthenticationFailed("Session token has expired.")
        except (jwt.InvalidTokenError, jwt.PyJWKClientError) as exc:
            logger.warning("Clerk token rejected: %s", exc)
            raise exceptions.AuthenticationFailed("Invalid session token.")

        parties = settings.CLERK_AUTHORIZED_PARTIES
        if parties and claims.get("azp") and claims["azp"] not in parties:
            raise exceptions.AuthenticationFailed("Unauthorized party.")
        return claims

    def resolve_user(self, claims):
        clerk_user_id = claims["sub"]
        user = User.objects.filter(clerk_user_id=clerk_user_id).first()

        if user is None:
            email = claims.get("email")
            if not email:
                raise exceptions.AuthenticationFailed(
                    "Unknown Clerk user and no email claim to provision one with."
                )
            user, _ = User.objects.get_or_create(
                email=email,
                defaults={
                    "clerk_user_id": clerk_user_id,
                    "name": claims.get("name", "") or "",
                    "avatar_url": claims.get("image_url", "") or "",
                },
            )
            if not user.clerk_user_id:
                user.clerk_user_id = clerk_user_id
                user.save(update_fields=["clerk_user_id", "updated_at"])
            elif user.clerk_user_id != clerk_user_id:
                raise exceptions.AuthenticationFailed("Email is already linked to another account.")

        if user.status != UserStatus.ACTIVE:
            raise exceptions.AuthenticationFailed(f"Account is {user.status}.")
        return user

    def authenticate_header(self, request):
        return self.keyword
