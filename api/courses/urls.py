from django.urls import path

from . import views

urlpatterns = [
    path("courses/", views.CourseListView.as_view(), name="course-list"),
    path("courses/<slug:slug>/", views.CourseDetailView.as_view(), name="course-detail"),
    path("admin/courses/", views.AdminCourseListView.as_view(), name="admin-course-list"),
    path(
        "admin/courses/<uuid:pk>/",
        views.AdminCourseDetailView.as_view(),
        name="admin-course-detail",
    ),
    path(
        "admin/courses/<uuid:pk>/publish/",
        views.AdminCoursePublishView.as_view(),
        name="admin-course-publish",
    ),
    path(
        "admin/courses/<uuid:pk>/unpublish/",
        views.AdminCourseUnpublishView.as_view(),
        name="admin-course-unpublish",
    ),
    path(
        "admin/courses/<uuid:pk>/thumbnail/upload/",
        views.AdminThumbnailUploadView.as_view(),
        name="admin-course-thumbnail-upload",
    ),
    path(
        "admin/courses/<uuid:pk>/curriculum/",
        views.AdminCurriculumView.as_view(),
        name="admin-course-curriculum",
    ),
    path(
        "admin/courses/<uuid:pk>/modules/",
        views.AdminModuleCreateView.as_view(),
        name="admin-module-create",
    ),
    path("admin/modules/<uuid:pk>/", views.AdminModuleDetailView.as_view(), name="admin-module"),
    path(
        "admin/modules/<uuid:pk>/move/",
        views.AdminModuleMoveView.as_view(),
        name="admin-module-move",
    ),
    path(
        "admin/modules/<uuid:pk>/lessons/",
        views.AdminLessonCreateView.as_view(),
        name="admin-lesson-create",
    ),
    path("admin/lessons/<uuid:pk>/", views.AdminLessonDetailView.as_view(), name="admin-lesson"),
    path(
        "admin/lessons/<uuid:pk>/move/",
        views.AdminLessonMoveView.as_view(),
        name="admin-lesson-move",
    ),
]
