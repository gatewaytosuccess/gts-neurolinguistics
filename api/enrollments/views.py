from rest_framework import generics

from .models import Enrollment, EnrollmentStatus
from .serializers import EnrollmentSerializer


class MyEnrollmentListView(generics.ListAPIView):
    """The requester's active enrollments, drafts included.

    Unpaginated: the catalog matches every card against the full list.
    """

    serializer_class = EnrollmentSerializer
    pagination_class = None

    def get_queryset(self):
        return Enrollment.objects.filter(
            user=self.request.user, status=EnrollmentStatus.ACTIVE
        ).select_related("course")
