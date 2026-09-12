"""
``User`` mirrors a Clerk user. Only role and status belong to this app; Clerk
overwrites everything else.
"""

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone

from common.models import UUIDModel


class Role(models.TextChoices):
    LEARNER = "learner", "Learner"
    INSTRUCTOR = "instructor", "Instructor"
    ADMIN = "admin", "Admin"


class UserStatus(models.TextChoices):
    """``suspended`` and ``banned`` are cleared only by an admin.

    ``deleted`` means the user deleted their Clerk account; signing up again
    with the same email reactivates the row. ``users.sync`` enforces both.
    """

    ACTIVE = "active", "Active"
    SUSPENDED = "suspended", "Suspended"
    BANNED = "banned", "Banned"
    DELETED = "deleted", "Deleted"


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Users must have an email address.")
        user = self.model(email=self.normalize_email(email), **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", Role.ADMIN)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self.create_user(email, password, **extra_fields)


class User(UUIDModel, AbstractBaseUser, PermissionsMixin):
    clerk_user_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=255, blank=True)
    avatar_url = models.URLField(max_length=500, blank=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.LEARNER)
    status = models.CharField(
        max_length=20, choices=UserStatus.choices, default=UserStatus.ACTIVE
    )
    suspended_at = models.DateTimeField(null=True, blank=True)
    suspension_reason = models.CharField(max_length=500, blank=True)

    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        db_table = "users"
        ordering = ["-created_at"]

    def __str__(self):
        return self.email

    @property
    def is_active(self):
        """Any status but ``active`` blocks login, /admin/ included."""
        return self.status == UserStatus.ACTIVE

    @property
    def is_admin(self):
        return self.role == Role.ADMIN

    @property
    def is_instructor(self):
        return self.role in {Role.INSTRUCTOR, Role.ADMIN}

    def suspend(self, reason="", *, banned=False):
        self.status = UserStatus.BANNED if banned else UserStatus.SUSPENDED
        self.suspended_at = timezone.now()
        self.suspension_reason = reason
        self.save(update_fields=["status", "suspended_at", "suspension_reason", "updated_at"])

    @property
    def is_deleted(self):
        return self.status == UserStatus.DELETED

    def reinstate(self):
        self.status = UserStatus.ACTIVE
        self.suspended_at = None
        self.suspension_reason = ""
        self.save(update_fields=["status", "suspended_at", "suspension_reason", "updated_at"])
