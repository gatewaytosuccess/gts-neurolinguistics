"""
Provisions an unknown Clerk user on first request: Clerk redirects a new user
into the app before the ``user.created`` webhook can land.

Provisioning needs an ``email`` claim. Add it under Clerk's "Customize session
token"; a named JWT template is not what ``getToken()`` returns.
"""

import logging

import jwt
from django.conf import settings
from rest_framework import authentication, exceptions

from .models import User, UserStatus
from .sync import MirrorConflict, mirror_user

logger = logging.getLogger(__name__)

_jwks_client = None


def get_jwks_client():
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
            try:
                user = mirror_user(
                    clerk_user_id=clerk_user_id,
                    email=email,
                    name=claims.get("name") or "",
                    avatar_url=claims.get("image_url") or "",
                )
            except MirrorConflict as exc:
                logger.warning("Refused to provision Clerk user %s: %s", clerk_user_id, exc)
                raise exceptions.AuthenticationFailed(
                    "This email is already linked to another account."
                )

        if user.status != UserStatus.ACTIVE:
            raise exceptions.AuthenticationFailed(f"Account is {user.status}.")
        return user

    def authenticate_header(self, request):
        return self.keyword
