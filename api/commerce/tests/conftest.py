import itertools
from types import SimpleNamespace

import pytest

from commerce import stripe_api


class FakeStripe:
    """Stands in for ``commerce.stripe_api``. ``calls`` records each call as
    ``(name, args, kwargs)``; set ``fail`` to an exception to raise it from every call.
    """

    def __init__(self):
        self.calls = []
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

    def retrieve_payment_intent(self, payment_intent_id):
        self._record("retrieve_payment_intent", payment_intent_id)
        return SimpleNamespace(latest_charge=SimpleNamespace(receipt_url=self.receipt_url))


@pytest.fixture
def fake_stripe(monkeypatch):
    fake = FakeStripe()
    for name in (
        "create_customer",
        "update_customer_email",
        "create_checkout_session",
        "retrieve_payment_intent",
    ):
        monkeypatch.setattr(stripe_api, name, getattr(fake, name))
    return fake
