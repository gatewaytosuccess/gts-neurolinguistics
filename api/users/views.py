from rest_framework.decorators import api_view
from rest_framework.response import Response

from .serializers import UserSerializer


@api_view(["GET"])
def me(request):
    """Safe to call right after sign-up: authentication provisions a missing row."""
    return Response(UserSerializer(request.user).data)
