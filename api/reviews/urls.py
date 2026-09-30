from django.urls import path

from . import views

urlpatterns = [
    path(
        "courses/<slug:slug>/reviews/",
        views.CourseReviewListView.as_view(),
        name="course-review-list",
    ),
]
