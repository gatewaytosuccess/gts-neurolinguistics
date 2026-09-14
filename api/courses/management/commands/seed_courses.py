"""Seeds a dev database with catalog data. Creates no enrollments."""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from courses.models import ContentType, Course, CourseStatus, Lesson, Module
from reviews.models import Review, ReviewStatus
from users.models import Role, User

# Titles, descriptions and prices match the landing page's course preview.
COURSES = [
    {
        "slug": "foundations-of-neurolinguistics",
        "title": "Foundations of Neurolinguistics",
        "description": "Where language sits in the brain, and how we found out.",
        "price_cents": 14900,
        "status": CourseStatus.PUBLISHED,
        "modules": [
            (
                "Mapping language",
                [
                    ("Broca, Wernicke and the lesion method", ContentType.VIDEO),
                    ("The classical language network", ContentType.SLIDES),
                    ("Reading: a short history of localization", ContentType.TEXT),
                ],
            ),
            (
                "Modern methods",
                [
                    ("What fMRI can and can't tell us", ContentType.VIDEO),
                    ("EEG and the N400", ContentType.SLIDES),
                ],
            ),
        ],
    },
    {
        "slug": "aphasia-and-the-damaged-brain",
        "title": "Aphasia and the Damaged Brain",
        "description": "What losing words after a stroke reveals about how we produce them.",
        "price_cents": 12900,
        "status": CourseStatus.PUBLISHED,
        "modules": [
            (
                "Kinds of aphasia",
                [
                    ("Fluent and non-fluent aphasia", ContentType.VIDEO),
                    ("Case notes: anomia", ContentType.TEXT),
                ],
            ),
            (
                "Recovery",
                [
                    ("Plasticity after stroke", ContentType.SLIDES),
                    ("Speech therapy approaches", ContentType.VIDEO),
                    ("Reading: living with aphasia", ContentType.TEXT),
                ],
            ),
        ],
    },
    {
        "slug": "the-bilingual-brain",
        "title": "The Bilingual Brain",
        "description": "How two languages share, compete for, and reshape the same neural space.",
        "price_cents": 12900,
        "status": CourseStatus.PUBLISHED,
        "modules": [
            (
                "Two languages, one brain",
                [
                    ("Shared and separate representations", ContentType.VIDEO),
                    ("Language control and switching", ContentType.SLIDES),
                ],
            ),
            (
                "Acquisition",
                [
                    ("Critical periods, revisited", ContentType.TEXT),
                    ("Learning a language as an adult", ContentType.VIDEO),
                ],
            ),
        ],
    },
    {
        "slug": "sign-language-and-the-brain",
        "title": "Sign Language and the Brain",
        "description": "What signed languages show about language beyond speech.",
        "price_cents": 12900,
        "status": CourseStatus.DRAFT,
        "modules": [
            (
                "Language without sound",
                [
                    ("Is sign language processed like speech?", ContentType.VIDEO),
                    ("Aphasia in signers", ContentType.TEXT),
                ],
            ),
            (
                "Space as grammar",
                [
                    ("Spatial syntax", ContentType.SLIDES),
                    ("Reading: home sign", ContentType.TEXT),
                ],
            ),
        ],
    },
]

LEARNERS = [
    ("seed-learner-1@example.com", "Ada Seed"),
    ("seed-learner-2@example.com", "Ben Seed"),
    ("seed-learner-3@example.com", "Cleo Seed"),
    ("seed-learner-4@example.com", "Dev Seed"),
]

# (learner email, course slug, rating, body, status). The Bilingual Brain gets
# none so the catalog has a course with no ratings.
REVIEWS = [
    (
        "seed-learner-1@example.com",
        "foundations-of-neurolinguistics",
        5,
        "Clear and careful.",
        ReviewStatus.PUBLISHED,
    ),
    (
        "seed-learner-2@example.com",
        "foundations-of-neurolinguistics",
        4,
        "Great overview, a little fast in module two.",
        ReviewStatus.PUBLISHED,
    ),
    # Would drag the average down if hidden reviews were counted.
    (
        "seed-learner-3@example.com",
        "foundations-of-neurolinguistics",
        1,
        "Spam spam spam.",
        ReviewStatus.HIDDEN,
    ),
    (
        "seed-learner-4@example.com",
        "aphasia-and-the-damaged-brain",
        5,
        "Moving and rigorous.",
        ReviewStatus.PUBLISHED,
    ),
]

TEXT_BODY = "Placeholder lesson text for local development."
VIDEO_SECONDS = 600


class Command(BaseCommand):
    help = "Fill a dev database with courses, lessons, learners and reviews. Safe to re-run."

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("seed_courses only runs with DEBUG on.")

        with transaction.atomic():
            courses = {spec["slug"]: self.seed_course(spec) for spec in COURSES}
            learners = {email: self.seed_learner(email, name) for email, name in LEARNERS}
            for email, slug, rating, body, status in REVIEWS:
                Review.objects.update_or_create(
                    user=learners[email],
                    course=courses[slug],
                    defaults={"rating": rating, "body": body, "status": status},
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {len(COURSES)} courses, {len(LEARNERS)} learners, {len(REVIEWS)} reviews."
            )
        )

    def seed_course(self, spec):
        course, _ = Course.objects.update_or_create(
            slug=spec["slug"],
            defaults={
                "title": spec["title"],
                "description": spec["description"],
                "price_cents": spec["price_cents"],
                "status": spec["status"],
            },
        )
        for module_position, (module_title, lessons) in enumerate(spec["modules"], start=1):
            module, _ = Module.objects.update_or_create(
                course=course, position=module_position, defaults={"title": module_title}
            )
            for lesson_position, (lesson_title, content_type) in enumerate(lessons, start=1):
                Lesson.objects.update_or_create(
                    module=module,
                    position=lesson_position,
                    defaults={
                        "title": lesson_title,
                        "content_type": content_type,
                        "content_body": TEXT_BODY if content_type == ContentType.TEXT else "",
                        "duration_seconds": (
                            VIDEO_SECONDS if content_type == ContentType.VIDEO else None
                        ),
                        "is_preview": module_position == 1 and lesson_position == 1,
                    },
                )
        return course

    def seed_learner(self, email, name):
        user = User.objects.filter(email=email).first()
        if user is None:
            user = User.objects.create_user(email=email, name=name, role=Role.LEARNER)
        return user
