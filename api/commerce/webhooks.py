"""
Stripe retries any non-2xx for days. Return one only for a rejected request or
a Stripe call that failed; anything a retry can't fix is logged and answered 200.
"""

import json
import logging
import uuid

import stripe
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from . import stripe_api
from .checkout import expire, fulfil, record_refund
from .models import Order

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
    handler = {
        "checkout.session.completed": _handle_session_completed,
        "checkout.session.expired": _handle_session_expired,
        "charge.refunded": _handle_charge_refunded,
        "charge.dispute.created": _handle_dispute_created,
    }.get(event_type)
    if handler is None:
        logger.debug("Ignoring unhandled Stripe event %s.", event_type)
        return Response({"status": "ignored", "type": event_type})

    return handler((event.get("data") or {}).get("object") or {})


def _handle_session_completed(session):
    order = _session_order(session)
    if order is None:
        return Response({"status": "unknown"})

    try:
        order = fulfil(order, session)
    except stripe.StripeError:
        logger.exception("Could not fulfil order %s; asking Stripe to retry.", order.pk)
        return Response({"detail": "Stripe is unavailable."}, status=503)
    return Response({"status": "ok", "order_status": order.status})


def _handle_session_expired(session):
    order = _session_order(session)
    if order is None:
        return Response({"status": "unknown"})

    order = expire(order, session)
    return Response({"status": "ok", "order_status": order.status})


def _handle_charge_refunded(charge):
    try:
        order = _payment_intent_order(charge.get("payment_intent"))
    except stripe.StripeError:
        logger.exception(
            "Could not look up refunded charge %s; asking Stripe to retry.", charge.get("id")
        )
        return Response({"detail": "Stripe is unavailable."}, status=503)
    if order is None:
        logger.error("Refunded charge %s names no known order.", charge.get("id"))
        return Response({"status": "unknown"})

    order = record_refund(order, charge)
    return Response({"status": "ok", "order_status": order.status})


def _handle_dispute_created(dispute):
    try:
        order = _payment_intent_order(dispute.get("payment_intent"))
    except stripe.StripeError:
        logger.exception("Could not look up the order for dispute %s.", dispute.get("id"))
        order = None
    logger.error(
        "Dispute %s opened on charge %s (order %s): %s %s, reason %s.",
        dispute.get("id"),
        dispute.get("charge"),
        order.pk if order else "unknown",
        dispute.get("amount"),
        dispute.get("currency"),
        dispute.get("reason"),
    )
    return Response({"status": "ok"})


def _session_order(session):
    order = _order(session.get("metadata"))
    if order is None:
        logger.error("Checkout session %s names no known order.", session.get("id"))
    return order


def _payment_intent_order(payment_intent_id):
    """``None`` when there's no PaymentIntent or Stripe doesn't know it. Raises
    ``stripe.StripeError`` for any other failed lookup."""
    if not payment_intent_id:
        return None
    try:
        metadata = stripe_api.retrieve_payment_intent_metadata(payment_intent_id)
    except stripe.InvalidRequestError:
        logger.warning("Stripe has no PaymentIntent %s.", payment_intent_id, exc_info=True)
        return None
    return _order(metadata)


def _order(metadata):
    order_id = (metadata or {}).get("order_id")
    return Order.objects.filter(pk=order_id).first() if _is_uuid(order_id) else None


def _is_uuid(value):
    try:
        uuid.UUID(str(value))
    except ValueError:
        return False
    return True
