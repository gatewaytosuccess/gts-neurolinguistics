import pytest

from courses.models import Lesson


@pytest.mark.parametrize(
    "parts, empty",
    [
        ({}, True),
        ({"video_key": "lessons/a.mp4"}, False),
        ({"slides_key": "lessons/a.pdf"}, False),
        ({"body": "Text"}, False),
    ],
)
def test_is_empty(parts, empty):
    assert Lesson(title="Lesson", position=0, **parts).is_empty is empty
