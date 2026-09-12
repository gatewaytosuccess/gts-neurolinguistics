from rest_framework.decorators import api_view
from rest_framework.response import Response

from .serializers import UserSerializer


@api_view(["GET"])
def me(request):
    """The signed-in user's local mirror row.

    ``ClerkAuthentication`` has already verified the session token and, if the
    ``user.created`` webhook has not landed yet, provisioned the row -- so this
    is also what the frontend calls right after sign-up to be sure the account
    exists before it renders anything that depends on it.
    """
    return Response(UserSerializer(request.user).data)
