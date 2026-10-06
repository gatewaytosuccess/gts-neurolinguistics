"""Where a learner's progress through a course leaves them."""

from collections import defaultdict

from django.db.models import F

from courses.models import Lesson

from .models import LessonProgress, ProgressStatus


def curriculum_order(course):
    """The ids of the course's lessons in curriculum order, across modules."""
    return list(
        Lesson.objects.filter(module__course=course)
        .order_by("module__position", "position")
        .values_list("pk", flat=True)
    )


def continue_lesson_id(user, course):
    """The lesson the user's **Continue** goes to, or ``None`` for a course with no lessons.

    Reads the user's progress whether or not they're enrolled, so only call it
    for an enrolled learner.
    """
    return continue_lesson_ids(user, [course.pk])[course.pk]


def continue_lesson_ids(user, course_ids):
    """``continue_lesson_id`` for several courses at once, keyed by course id."""
    orders = defaultdict(list)
    lessons = (
        Lesson.objects.filter(module__course__in=course_ids)
        .order_by("module__position", "position")
        .values_list("module__course_id", "pk")
    )
    for course_id, lesson_id in lessons:
        orders[course_id].append(lesson_id)

    rows = defaultdict(list)
    progress = LessonProgress.objects.filter(
        user=user, lesson__module__course__in=course_ids
    ).values("pk", "lesson_id", "status", "updated_at", course_id=F("lesson__module__course_id"))
    for row in progress:
        rows[row["course_id"]].append(row)

    return {
        course_id: next_lesson_id(orders[course_id], rows[course_id]) for course_id in course_ids
    }


def next_lesson_id(order, rows):
    if not order:
        return None
    if not rows:
        return order[0]
    latest = max(rows, key=lambda row: (row["updated_at"], row["pk"]))
    if latest["status"] != ProgressStatus.COMPLETED:
        return latest["lesson_id"]
    all_complete = sum(row["status"] == ProgressStatus.COMPLETED for row in rows) == len(order)
    index = order.index(latest["lesson_id"])
    if all_complete or index + 1 == len(order):
        return latest["lesson_id"]
    return order[index + 1]
