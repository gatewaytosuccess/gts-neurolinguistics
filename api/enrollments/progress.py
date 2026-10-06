"""Where a learner's progress through a course leaves them."""

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
    order = curriculum_order(course)
    if not order:
        return None
    rows = LessonProgress.objects.filter(user=user, lesson__module__course=course)
    latest = rows.order_by("-updated_at", "-pk").first()
    if latest is None:
        return order[0]
    if latest.status != ProgressStatus.COMPLETED:
        return latest.lesson_id
    all_complete = rows.filter(status=ProgressStatus.COMPLETED).count() == len(order)
    index = order.index(latest.lesson_id)
    if all_complete or index + 1 == len(order):
        return latest.lesson_id
    return order[index + 1]
