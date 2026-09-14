"""
Every write of Clerk data into ``users`` goes through here, from both the
webhook and ``users.authentication``. See ADR-0001.
"""

import logging

from django.db import transaction

from .models import Role, User, UserStatus

logger = logging.getLogger(__name__)


class MirrorConflict(Exception):
    """The Clerk user collides with a local row it must not be linked to.

    Retrying the same input never succeeds.
    """


def primary_email(payload):
    """The primary address, or ``None``. Secondary addresses are never mirrored."""
    primary_id = payload.get("primary_email_address_id")
    addresses = payload.get("email_addresses") or []
    for address in addresses:
        if address.get("id") == primary_id:
            return (address.get("email_address") or "").strip() or None
    # A partially-built Clerk user may have no primary flagged yet.
    if len(addresses) == 1:
        return (addresses[0].get("email_address") or "").strip() or None
    return None


def full_name(payload):
    parts = [payload.get("first_name") or "", payload.get("last_name") or ""]
    return " ".join(part for part in parts if part.strip()).strip()


def mirror_user(*, clerk_user_id, email, name="", avatar_url=""):
    """Create or update the local mirror of a Clerk user.

    Raises ``MirrorConflict`` if the id or email is missing, or the email
    belongs to a row that must not be linked to this Clerk user.
    """
    if not clerk_user_id:
        raise MirrorConflict("Clerk user id is required to mirror a user.")
    if not email:
        raise MirrorConflict(f"No primary email address for Clerk user {clerk_user_id}.")

    email = User.objects.normalize_email(email)

    with transaction.atomic():
        user = User.objects.select_for_update().filter(clerk_user_id=clerk_user_id).first()
        if user is not None:
            return _update_mirrored_fields(user, email=email, name=name, avatar_url=avatar_url)

        existing = User.objects.select_for_update().filter(email__iexact=email).first()
        if existing is None:
            user = User.objects.create_user(
                email=email,
                clerk_user_id=clerk_user_id,
                name=name,
                avatar_url=avatar_url,
                role=Role.LEARNER,
                status=UserStatus.ACTIVE,
            )
            logger.info("Mirrored new Clerk user %s as %s.", clerk_user_id, user.id)
            return user

        return _link_existing(
            existing, clerk_user_id, email=email, name=name, avatar_url=avatar_url
        )


def _link_existing(user, clerk_user_id, *, email, name, avatar_url):
    if user.clerk_user_id and user.clerk_user_id != clerk_user_id:
        raise MirrorConflict(
            f"Email {email} is already linked to Clerk user {user.clerk_user_id}; "
            f"refusing to relink it to {clerk_user_id}."
        )

    if user.status in {UserStatus.SUSPENDED, UserStatus.BANNED}:
        # Signing up again must not clear a suspension or ban.
        raise MirrorConflict(
            f"Email {email} belongs to a {user.status} account; refusing to link "
            f"Clerk user {clerk_user_id} to it."
        )

    if user.status == UserStatus.DELETED:
        logger.info("Resurrecting deleted account %s for Clerk user %s.", user.id, clerk_user_id)
        user.status = UserStatus.ACTIVE
    elif user.role != Role.LEARNER:
        # Not an escalation: the row already had this role, and Clerk verified the email.
        logger.warning(
            "Linking Clerk user %s to pre-existing %s account %s (%s).",
            clerk_user_id,
            user.role,
            user.id,
            email,
        )

    user.clerk_user_id = clerk_user_id
    return _update_mirrored_fields(user, email=email, name=name, avatar_url=avatar_url, force=True)


def _update_mirrored_fields(user, *, email, name, avatar_url, force=False):
    """Save email, name and avatar.

    ``force`` skips the email-collision check and also saves ``clerk_user_id``
    and ``status``.
    """
    if not force and User.objects.filter(email__iexact=email).exclude(pk=user.pk).exists():
        raise MirrorConflict(
            f"Cannot move {user.id} to email {email}: another account already holds it."
        )

    changed = ["clerk_user_id", "status"] if force else []
    for field, value in (("email", email), ("name", name), ("avatar_url", avatar_url)):
        if getattr(user, field) != value:
            setattr(user, field, value)
            changed.append(field)

    if changed:
        user.save(update_fields=sorted({*changed, "updated_at"}))
    return user


def forget_user(clerk_user_id):
    """Release the Clerk id and mark an active row ``deleted``. Never deletes the row.

    Orders, enrollments and reviews reference it. A suspended or banned row
    keeps its status. Returns ``None`` if the Clerk user was never mirrored.
    """
    with transaction.atomic():
        user = User.objects.select_for_update().filter(clerk_user_id=clerk_user_id).first()
        if user is None:
            logger.info("Ignoring user.deleted for unmirrored Clerk user %s.", clerk_user_id)
            return None

        user.clerk_user_id = None
        if user.status == UserStatus.ACTIVE:
            user.status = UserStatus.DELETED
        else:
            logger.info(
                "Clerk user %s deleted while %s; leaving local status untouched.",
                clerk_user_id,
                user.status,
            )
        user.save(update_fields=["clerk_user_id", "status", "updated_at"])
        return user
