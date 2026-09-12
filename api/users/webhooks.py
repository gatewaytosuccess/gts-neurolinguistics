"""
Clerk webhook receiver.

Clerk delivers ``user.*`` events here through Svix. This is the durable half of
the mirror: a session token only ever describes the person presenting it, so
deletions and edits made elsewhere arrive only as events.

Retries are the reason almost everything below returns 200. Svix retries any
non-2xx for days, so a response code is only useful for the failures a retry
could actually fix (a signature that didn't verify, a body that isn't JSON).
A collision between two accounts is not one of those: it will still collide on
the tenth delivery, so it is logged loudly and acknowledged.
"""

import json
import logging

from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from svix.webhooks import Webhook, WebhookVerificationError

from .sync import MirrorConflict, forget_user, full_name, mirror_user, primary_email

logger = logging.getLogger(__name__)

SVIX_HEADERS = ("svix-id", "svix-timestamp", "svix-signature")


@csrf_exempt
@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def clerk_webhook(request):
    """Receive ``user.created`` / ``user.updated`` / ``user.deleted`` from Clerk."""
    secret = settings.CLERK_WEBHOOK_SIGNING_SECRET
    if not secret:
        logger.error("CLERK_WEBHOOK_SIGNING_SECRET is not configured; rejecting webhook.")
        return Response({"detail": "Webhooks are not configured."}, status=503)

    headers = {name: request.headers.get(name, "") for name in SVIX_HEADERS}
    if not all(headers.values()):
        return Response({"detail": "Missing Svix signature headers."}, status=400)

    try:
        event = Webhook(secret).verify(request.body, headers)
    except WebhookVerificationError:
        logger.warning("Rejected a Clerk webhook with an invalid signature.")
        return Response({"detail": "Invalid signature."}, status=400)
    except (json.JSONDecodeError, ValueError):
        return Response({"detail": "Malformed payload."}, status=400)

    event_type = event.get("type")
    data = event.get("data") or {}

    handler = {
        "user.created": _handle_user_upserted,
        "user.updated": _handle_user_upserted,
        "user.deleted": _handle_user_deleted,
    }.get(event_type)

    if handler is None:
        # Clerk sends whatever the endpoint is subscribed to; anything we did
        # not ask for is still a successful delivery.
        logger.debug("Ignoring unhandled Clerk event %s.", event_type)
        return Response({"status": "ignored", "type": event_type})

    return handler(data, event_type)


def _handle_user_upserted(data, event_type):
    clerk_user_id = data.get("id")
    try:
        user = mirror_user(
            clerk_user_id=clerk_user_id,
            email=primary_email(data),
            name=full_name(data),
            avatar_url=data.get("image_url") or "",
        )
    except MirrorConflict as exc:
        logger.error("Could not mirror %s for Clerk user %s: %s", event_type, clerk_user_id, exc)
        return Response({"status": "conflict"})

    return Response({"status": "ok", "user_id": str(user.id)})


def _handle_user_deleted(data, event_type):
    user = forget_user(data.get("id"))
    if user is None:
        return Response({"status": "unknown"})
    return Response({"status": "ok", "user_id": str(user.id)})
