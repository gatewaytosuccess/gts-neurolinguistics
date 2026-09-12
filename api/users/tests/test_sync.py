"""The mirroring rules -- the ones that are easy to get quietly wrong."""

import pytest

from users.models import Role, User, UserStatus
from users.sync import MirrorConflict, forget_user, full_name, mirror_user, primary_email

pytestmark = pytest.mark.django_db


class TestPayloadReading:
    def test_reads_the_primary_address_not_the_first(self, clerk_payload):
        payload = clerk_payload(email="ada@example.com", extra_emails=["work@example.com"])
        payload["email_addresses"].reverse()
        assert primary_email(payload) == "ada@example.com"

    def test_falls_back_to_a_lone_address_when_none_is_flagged_primary(self, clerk_payload):
        payload = clerk_payload()
        payload["primary_email_address_id"] = None
        assert primary_email(payload) == "ada@example.com"

    def test_gives_up_when_several_addresses_and_no_primary(self, clerk_payload):
        payload = clerk_payload(extra_emails=["work@example.com"])
        payload["primary_email_address_id"] = None
        assert primary_email(payload) is None

    def test_joins_the_name_halves(self, clerk_payload):
        assert full_name(clerk_payload()) == "Ada Lovelace"

    def test_tolerates_a_missing_half(self, clerk_payload):
        assert full_name(clerk_payload(last_name=None)) == "Ada"
        assert full_name(clerk_payload(first_name=None, last_name=None)) == ""


class TestFirstMirror:
    def test_creates_an_active_learner(self):
        user = mirror_user(clerk_user_id="user_1", email="ada@example.com", name="Ada")
        assert user.role == Role.LEARNER
        assert user.status == UserStatus.ACTIVE
        assert user.clerk_user_id == "user_1"
        assert not user.has_usable_password()

    def test_refuses_without_an_email(self):
        with pytest.raises(MirrorConflict):
            mirror_user(clerk_user_id="user_1", email=None)

    def test_is_idempotent(self):
        first = mirror_user(clerk_user_id="user_1", email="ada@example.com")
        second = mirror_user(clerk_user_id="user_1", email="ada@example.com")
        assert first.pk == second.pk
        assert User.objects.count() == 1


class TestUpdates:
    def test_follows_an_email_change(self):
        mirror_user(clerk_user_id="user_1", email="ada@example.com")
        user = mirror_user(clerk_user_id="user_1", email="ada@new.example.com")
        assert user.email == "ada@new.example.com"
        assert User.objects.count() == 1

    def test_leaves_role_and_status_alone(self, make_user):
        make_user(email="ada@example.com", clerk_user_id="user_1", role=Role.INSTRUCTOR)
        user = mirror_user(clerk_user_id="user_1", email="ada@example.com", name="Ada")
        assert user.role == Role.INSTRUCTOR

    def test_refuses_to_take_an_email_another_account_holds(self, make_user):
        make_user(email="taken@example.com", clerk_user_id="user_2")
        mirror_user(clerk_user_id="user_1", email="ada@example.com")
        with pytest.raises(MirrorConflict):
            mirror_user(clerk_user_id="user_1", email="taken@example.com")


class TestLinkingToAnExistingRow:
    def test_adopts_a_row_that_has_no_clerk_id_yet(self, make_user):
        seeded = make_user(email="ada@example.com", name="Seeded")
        user = mirror_user(clerk_user_id="user_1", email="ada@example.com", name="Ada")
        assert user.pk == seeded.pk
        assert user.clerk_user_id == "user_1"
        assert user.name == "Ada"

    def test_never_steals_a_row_from_another_clerk_user(self, make_user):
        make_user(email="ada@example.com", clerk_user_id="user_other")
        with pytest.raises(MirrorConflict):
            mirror_user(clerk_user_id="user_1", email="ada@example.com")


class TestDeletedIsReversible:
    def test_signing_up_again_resurrects_the_account(self, make_user):
        gone = make_user(email="ada@example.com", status=UserStatus.DELETED)
        user = mirror_user(clerk_user_id="user_new", email="ada@example.com", name="Ada")
        assert user.pk == gone.pk, "the old row keeps its enrollments and order history"
        assert user.status == UserStatus.ACTIVE
        assert user.clerk_user_id == "user_new"


class TestBansAreNot:
    @pytest.mark.parametrize("status", [UserStatus.SUSPENDED, UserStatus.BANNED])
    def test_signing_up_again_cannot_clear_one(self, make_user, status):
        make_user(email="ada@example.com", status=status)
        with pytest.raises(MirrorConflict):
            mirror_user(clerk_user_id="user_new", email="ada@example.com")
        assert User.objects.get(email="ada@example.com").status == status


class TestForgetUser:
    def test_marks_an_active_account_deleted_and_releases_the_clerk_id(self, make_user):
        make_user(email="ada@example.com", clerk_user_id="user_1")
        user = forget_user("user_1")
        assert user.status == UserStatus.DELETED
        assert user.clerk_user_id is None

    def test_keeps_the_row_so_orders_survive(self, make_user):
        make_user(email="ada@example.com", clerk_user_id="user_1")
        forget_user("user_1")
        assert User.objects.filter(email="ada@example.com").exists()

    @pytest.mark.parametrize("status", [UserStatus.SUSPENDED, UserStatus.BANNED])
    def test_deleting_a_clerk_account_is_not_a_way_out_of_a_ban(self, make_user, status):
        make_user(email="ada@example.com", clerk_user_id="user_1", status=status)
        user = forget_user("user_1")
        assert user.status == status
        assert user.clerk_user_id is None

    def test_ignores_a_user_we_never_mirrored(self):
        assert forget_user("user_unknown") is None


class TestTheFullBanEvasionRoute:
    def test_ban_then_delete_then_sign_up_again_still_lands_on_banned(self, make_user):
        make_user(email="ada@example.com", clerk_user_id="user_1", status=UserStatus.BANNED)
        forget_user("user_1")
        with pytest.raises(MirrorConflict):
            mirror_user(clerk_user_id="user_2", email="ada@example.com")
        assert User.objects.get(email="ada@example.com").status == UserStatus.BANNED
