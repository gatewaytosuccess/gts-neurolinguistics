"""
Mirroring Clerk users into the local ``users`` table.

Clerk owns identity; this table is a read-only mirror of it (see
``docs/adr/0001-clerk-owns-identity.md``). The webhook and the just-in-time
fallback in ``users.authentication`` both write to that mirror, and both go
through here so they cannot drift apart on who may be linked to whom.
"""

import logging

from django.db import transaction

from .models import Role, User, UserStatus

logger = logging.getLogger(__name__)


class MirrorConflict(Exception):
    """The Clerk user cannot be mirrored onto the local row it collides with.

    Always a dead end for the event that raised it: retrying changes nothing,
    so callers log it and move on rather than failing the request.
    """


def primary_email(payload):
    """The Clerk user's primary email address, or ``None``.

    Clerk users can hold several addresses; only the primary one is mirrored,
    so a secondary address added or removed never moves the local row.
    """
    primary_id = payload.get("primary_email_address_id")
    addresses = payload.get("email_addresses") or []
    for address in addresses:
        if address.get("id") == primary_id:
            return (address.get("email_address") or "").strip() or None
    # A partially-built Clerk user can have no primary flagged yet; one
    # unambiguous address is still safe to mirror.
    if len(addresses) == 1:
        return (addresses[0].get("email_address") or "").strip() or None
    return None


def full_name(payload):
    """``first_name`` and ``last_name`` joined into SCHEMA.md's single ``name``."""
    parts = [payload.get("first_name") or "", payload.get("last_name") or ""]
    return " ".join(part for part in parts if part.strip()).strip()


def mirror_user(*, clerk_user_id, email, name="", avatar_url=""):
    """Create or update the local mirror of a Clerk user. Returns the ``User``.

    Raises ``MirrorConflict`` when the email belongs to a row that must not be
    linked to this Clerk user.
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

        return _link_existing(existing, clerk_user_id, email=email, name=name, avatar_url=avatar_url)


def _link_existing(user, clerk_user_id, *, email, name, avatar_url):
    """Attach a Clerk id to a row that already holds this email."""
    if user.clerk_user_id and user.clerk_user_id != clerk_user_id:
        raise MirrorConflict(
            f"Email {email} is already linked to Clerk user {user.clerk_user_id}; "
            f"refusing to relink it to {clerk_user_id}."
        )

    if user.status in {UserStatus.SUSPENDED, UserStatus.BANNED}:
        # The whole point of a ban is that the user cannot undo it themselves.
        raise MirrorConflict(
            f"Email {email} belongs to a {user.status} account; refusing to link "
            f"Clerk user {clerk_user_id} to it."
        )

    if user.status == UserStatus.DELETED:
        logger.info("Resurrecting deleted account %s for Clerk user %s.", user.id, clerk_user_id)
        user.status = UserStatus.ACTIVE
    elif user.role != Role.LEARNER:
        # Adoption, not escalation: the row already held this role and this
        # email, and Clerk has verified the address. Still worth a shout.
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
    """Write the fields Clerk owns, leaving role, status and history alone."""
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
    """Handle ``user.deleted``: the Clerk account is gone, the row stays.

    The row is the foreign key target for enrollments, orders and reviews, so
    deleting it would take a paying customer's purchase history with it.
    Instead the Clerk id is released and an otherwise-active account is marked
    ``deleted``. A suspended or banned account keeps that status -- deleting
    your Clerk account is not a way out of a ban.

    Returns the ``User``, or ``None`` if we never mirrored them.
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
