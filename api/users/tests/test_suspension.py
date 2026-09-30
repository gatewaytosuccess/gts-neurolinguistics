import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

from users.models import UserStatus


@pytest.mark.django_db
class TestSuspend:
    def test_records_when_and_why(self, make_user):
        user = make_user()

        user.suspend("Chargeback fraud")

        user.refresh_from_db()
        assert user.status == UserStatus.SUSPENDED
        assert user.suspended_at is not None
        assert user.suspension_reason == "Chargeback fraud"


@pytest.mark.django_db
class TestReinstate:
    def test_a_user_with_a_clerk_identity_becomes_active(self, make_user):
        user = make_user(clerk_user_id="user_1")
        user.suspend("Chargeback fraud")

        user.reinstate()

        user.refresh_from_db()
        assert user.status == UserStatus.ACTIVE
        assert user.suspended_at is None
        assert user.suspension_reason == ""

    def test_a_user_without_a_clerk_identity_goes_back_to_deleted(self, make_user):
        user = make_user(clerk_user_id=None)
        user.suspend("Chargeback fraud")

        user.reinstate()

        user.refresh_from_db()
        assert user.status == UserStatus.DELETED, "nobody could sign in to an active row"
        assert user.suspended_at is None
        assert user.suspension_reason == ""


@pytest.mark.django_db(transaction=True)
def test_the_migration_turns_banned_rows_into_suspended():
    before = [("users", "0002_alter_user_status")]
    after = [("users", "0003_merge_banned_into_suspended")]

    executor = MigrationExecutor(connection)
    executor.migrate(before)
    OldUser = executor.loader.project_state(before).apps.get_model("users", "User")
    OldUser.objects.create(email="banned@example.com", status="banned")
    OldUser.objects.create(email="active@example.com", status="active")

    executor = MigrationExecutor(connection)
    executor.migrate(after)

    NewUser = executor.loader.project_state(after).apps.get_model("users", "User")
    statuses = dict(NewUser.objects.values_list("email", "status"))
    assert statuses == {"banned@example.com": "suspended", "active@example.com": "active"}
