"""Curriculum edits. Each keeps positions numbered from 1 with no gaps.

Every edit locks the course row first, so concurrent edits to one curriculum
run one after another instead of colliding on a position. An edit that leaves a
published course with publish problems raises ``Unpublishable`` and rolls back.
"""

from .models import Lesson, Module
from .publishing import keeping_publishable


def _renumber(items):
    """Writes ``items``' positions as 1…n in list order, skipping rows already in place."""
    changed = []
    for position, item in enumerate(items, start=1):
        if item.position != position:
            item.position = position
            changed.append(item)
    if changed:
        type(changed[0]).objects.bulk_update(changed, ["position"])


def _move_within(items, item, position):
    """Moves ``item`` to ``position`` in ``items``; out-of-range positions are clamped."""
    items.remove(item)
    index = min(max(position, 1), len(items) + 1) - 1
    items.insert(index, item)


def add_module(course, title):
    with keeping_publishable(course.pk):
        return Module.objects.create(
            course=course, title=title, position=Module.objects.filter(course=course).count() + 1
        )


def move_module(module, position):
    """Returns the moved module with its new position."""
    with keeping_publishable(module.course_id):
        siblings = list(Module.objects.filter(course_id=module.course_id).order_by("position"))
        moved = next(sibling for sibling in siblings if sibling.pk == module.pk)
        _move_within(siblings, moved, position)
        _renumber(siblings)
        return moved


def delete_module(module):
    """Deletes its lessons and their progress too."""
    with keeping_publishable(module.course_id):
        module.delete()
        _renumber(list(Module.objects.filter(course_id=module.course_id).order_by("position")))


def add_lesson(module, title):
    with keeping_publishable(module.course_id):
        return Lesson.objects.create(
            module=module, title=title, position=Lesson.objects.filter(module=module).count() + 1
        )


def move_lesson(lesson, position=None, module=None):
    """Returns the moved lesson with its new module and position.

    ``module`` must belong to the lesson's course; it defaults to the lesson's own.
    ``position`` defaults to last.
    """
    source_id = lesson.module_id
    target_id = module.pk if module else source_id

    with keeping_publishable(lesson.module.course_id):
        source = list(Lesson.objects.filter(module_id=source_id).order_by("position"))
        moved = next(sibling for sibling in source if sibling.pk == lesson.pk)

        if target_id == source_id:
            target = source
        else:
            source.remove(moved)
            _renumber(source)
            target = list(Lesson.objects.filter(module_id=target_id).order_by("position"))
            target.append(moved)
            moved.module_id = target_id
            moved.save(update_fields=["module", "updated_at"])

        _move_within(target, moved, len(target) if position is None else position)
        _renumber(target)
        return moved


def delete_lesson(lesson):
    """Deletes its progress too."""
    with keeping_publishable(lesson.module.course_id):
        lesson.delete()
        _renumber(list(Lesson.objects.filter(module_id=lesson.module_id).order_by("position")))
