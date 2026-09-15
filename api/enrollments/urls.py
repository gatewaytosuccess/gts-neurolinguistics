from django.urls import path

from . import views

urlpatterns = [
    path(
        "users/me/enrollments/",
        views.MyEnrollmentListView.as_view(),
        name="user-me-enrollments",
    ),
]
