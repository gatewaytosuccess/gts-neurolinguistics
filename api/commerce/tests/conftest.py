import itertools
from types import SimpleNamespace

import pytest
import stripe

from commerce import stripe_api


class FakeStripe:
    """Stands in for ``commerce.stripe_api``. ``calls`` records each call as
    ``(name, args, kwargs)``; set ``fail`` to an exception to raise it from every call.
    ``sessions`` maps a session id to what retrieving it returns, as a dict, and
    ``payment_intents`` a PaymentIntent id to its metadata.
    Expiring a session in ``unexpirable`` fails as Stripe does for a completed
    one, and every refund fails while ``refuse_refunds`` is set.
    """

    def __init__(self):
        self.calls = []
        self.sessions = {}
        self.payment_intents = {}
        self.unexpirable = set()
        self.refuse_refunds = False
        self.fail = None
        self.receipt_url = "https://pay.stripe.com/receipts/test"
        self._ids = itertools.count(1)

    def _record(self, call, *args, **kwargs):
        if self.fail is not None:
            raise self.fail
        self.calls.append((call, args, kwargs))

    def named(self, name):
        return [call for call in self.calls if call[0] == name]

    def create_customer(self, *, email, name, user_id):
        self._record("create_customer", email=email, name=name, user_id=user_id)
        return f"cus_{next(self._ids)}"

    def update_customer_email(self, customer_id, email):
        self._record("update_customer_email", customer_id, email)

    def create_checkout_session(self, params):
        self._record("create_checkout_session", params)
        session_id = f"cs_test_{next(self._ids)}"
        return SimpleNamespace(id=session_id, url=f"https://checkout.stripe.com/c/pay/{session_id}")

    def retrieve_checkout_session(self, session_id):
        self._record("retrieve_checkout_session", session_id)
        if session_id not in self.sessions:
            raise stripe.InvalidRequestError(f"No such checkout.session: '{session_id}'", "id")
        return SimpleNamespace(to_dict=lambda: dict(self.sessions[session_id]))

    def expire_checkout_session(self, session_id):
        self._record("expire_checkout_session", session_id)
        if session_id in self.unexpirable:
            raise stripe.InvalidRequestError(
                'Only Checkout Sessions with a status in ["open"] can be expired.', None
            )
        return SimpleNamespace(id=session_id, status="expired")

    def create_refund(self, payment_intent_id, *, idempotency_key):
        self._record("create_refund", payment_intent_id, idempotency_key=idempotency_key)
        if self.refuse_refunds:
            raise stripe.APIConnectionError("Stripe is unreachable")
        return SimpleNamespace(id=f"re_{next(self._ids)}", status="succeeded")

    def retrieve_payment_intent(self, payment_intent_id):
        self._record("retrieve_payment_intent", payment_intent_id)
        return SimpleNamespace(latest_charge=SimpleNamespace(receipt_url=self.receipt_url))

    def retrieve_payment_intent_metadata(self, payment_intent_id):
        self._record("retrieve_payment_intent_metadata", payment_intent_id)
        if payment_intent_id not in self.payment_intents:
            raise stripe.InvalidRequestError(f"No such payment_intent: '{payment_intent_id}'", "id")
        return dict(self.payment_intents[payment_intent_id])


@pytest.fixture
def fake_stripe(monkeypatch):
    fake = FakeStripe()
    for name in (
        "create_customer",
        "update_customer_email",
        "create_checkout_session",
        "retrieve_checkout_session",
        "expire_checkout_session",
        "create_refund",
        "retrieve_payment_intent",
        "retrieve_payment_intent_metadata",
    ):
        monkeypatch.setattr(stripe_api, name, getattr(fake, name))
    return fake
