import pytest
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory
from rest_framework.views import APIView

from users.authentication import ClerkAuthentication
from users.models import Role, UserStatus
from users.permissions import IsAdmin

pytestmark = pytest.mark.django_db


class AdminOnlyView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        return Response({})


@pytest.fixture
def signed_in(monkeypatch):
    """Stubs only token verification; the status check runs for real."""
    monkeypatch.setattr(
        ClerkAuthentication, "decode_token", lambda self, token: {"sub": "user_2abcDEF"}
    )


def call(**headers):
    request = APIRequestFactory().get("/", headers=headers)
    return AdminOnlyView.as_view()(request)


def call_signed_in():
    return call(Authorization="Bearer stub")


def test_allows_an_admin(make_user, signed_in):
    make_user(clerk_user_id="user_2abcDEF", role=Role.ADMIN)
    assert call_signed_in().status_code == 200


@pytest.mark.parametrize("role", [Role.LEARNER, Role.INSTRUCTOR])
def test_forbids_every_other_role(make_user, signed_in, role):
    make_user(clerk_user_id="user_2abcDEF", role=role)
    assert call_signed_in().status_code == 403


@pytest.mark.parametrize("status", [UserStatus.SUSPENDED, UserStatus.BANNED])
def test_rejects_a_suspended_admin_as_unauthenticated(make_user, signed_in, status):
    make_user(clerk_user_id="user_2abcDEF", role=Role.ADMIN, status=status)
    assert call_signed_in().status_code == 401


def test_rejects_a_request_with_no_credentials():
    assert call().status_code == 401
