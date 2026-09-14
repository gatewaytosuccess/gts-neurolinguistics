import pytest

from users.models import Role, User, UserStatus


@pytest.fixture
def clerk_payload():
    """Builds the ``data`` object of a Clerk ``user.created`` / ``user.updated`` event."""

    def build(
        clerk_user_id="user_2abcDEF",
        email="ada@example.com",
        first_name="Ada",
        last_name="Lovelace",
        image_url="https://img.clerk.com/ada.png",
        extra_emails=(),
    ):
        addresses = [{"id": "idn_primary", "email_address": email}]
        addresses += [
            {"id": f"idn_extra_{i}", "email_address": extra} for i, extra in enumerate(extra_emails)
        ]
        return {
            "id": clerk_user_id,
            "primary_email_address_id": "idn_primary",
            "email_addresses": addresses,
            "first_name": first_name,
            "last_name": last_name,
            "image_url": image_url,
        }

    return build


@pytest.fixture
def make_user(db):
    def build(email="ada@example.com", **fields):
        fields.setdefault("role", Role.LEARNER)
        fields.setdefault("status", UserStatus.ACTIVE)
        return User.objects.create_user(email=email, **fields)

    return build
