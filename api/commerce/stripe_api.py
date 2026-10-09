"""The only code that calls the Stripe API. Tests replace these functions and
never reach Stripe.

Every function raises ``stripe.StripeError`` when Stripe refuses the call or
can't be reached.
"""

import functools

import stripe
from django.conf import settings


@functools.cache
def _client():
    return stripe.StripeClient(settings.STRIPE_SECRET_KEY)


def create_customer(*, email, name, user_id):
    """A new Customer's id. ``user_id`` goes in its metadata."""
    customer = _client().v1.customers.create(
        {"email": email, "name": name, "metadata": {"user_id": str(user_id)}}
    )
    return customer.id


def update_customer_email(customer_id, email):
    _client().v1.customers.update(customer_id, {"email": email})


def create_checkout_session(params):
    """``params`` are Stripe's ``checkout.sessions.create`` parameters, unchanged."""
    return _client().v1.checkout.sessions.create(params)


def retrieve_checkout_session(session_id):
    return _client().v1.checkout.sessions.retrieve(session_id)


def expire_checkout_session(session_id):
    """Fails if the session is already complete or expired."""
    return _client().v1.checkout.sessions.expire(session_id)


def retrieve_payment_intent(payment_intent_id):
    """The PaymentIntent with ``latest_charge`` expanded, for its ``receipt_url``."""
    return _client().v1.payment_intents.retrieve(payment_intent_id, {"expand": ["latest_charge"]})


def retrieve_payment_intent_metadata(payment_intent_id):
    """The PaymentIntent's metadata as a plain dict."""
    return _client().v1.payment_intents.retrieve(payment_intent_id).metadata.to_dict()


def create_refund(payment_intent_id, *, idempotency_key):
    """Refunds the PaymentIntent in full. A repeated ``idempotency_key`` returns
    the first refund instead of making another."""
    return _client().v1.refunds.create(
        {"payment_intent": payment_intent_id},
        {"idempotency_key": idempotency_key},
    )
