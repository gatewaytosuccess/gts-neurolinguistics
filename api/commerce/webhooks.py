"""
Stripe retries any non-2xx for days. Return one only for a rejected request;
anything a retry can't fix is logged and answered 200.
"""

import json
import logging

import stripe
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

logger = logging.getLogger(__name__)


@csrf_exempt
@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def stripe_webhook(request):
    secret = settings.STRIPE_WEBHOOK_SECRET
    if not secret:
        logger.error("STRIPE_WEBHOOK_SECRET is not configured; rejecting webhook.")
        return Response({"detail": "Webhooks are not configured."}, status=503)

    signature = request.headers.get("Stripe-Signature", "")
    if not signature:
        return Response({"detail": "Missing Stripe-Signature header."}, status=400)

    try:
        stripe.WebhookSignature.verify_header(request.body, signature, secret, tolerance=300)
        event = json.loads(request.body)
    except stripe.SignatureVerificationError:
        logger.warning("Rejected a Stripe webhook with an invalid signature.")
        return Response({"detail": "Invalid signature."}, status=400)
    except ValueError:
        return Response({"detail": "Malformed payload."}, status=400)

    if not isinstance(event, dict):
        return Response({"detail": "Malformed payload."}, status=400)

    event_type = event.get("type")
    logger.debug("Ignoring unhandled Stripe event %s.", event_type)
    return Response({"status": "ignored", "type": event_type})
