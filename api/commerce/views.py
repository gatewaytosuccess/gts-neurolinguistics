import logging

import stripe
from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from courses.models import Course

from .checkout import AlreadyEnrolled, confirm, start_checkout
from .models import Order
from .serializers import OrderSerializer

logger = logging.getLogger(__name__)


class CheckoutInputSerializer(serializers.Serializer):
    course = serializers.SlugField()


class CheckoutView(APIView):
    """Starts a checkout for one course and answers ``{url}``, the Stripe page to send the user to.

    404 for an unknown or draft course, 409 with ``code: "already_enrolled"``
    while the user holds an active enrollment in it, 502 if Stripe refuses.
    """

    def post(self, request):
        serializer = CheckoutInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        course = get_object_or_404(
            Course.objects.published(), slug=serializer.validated_data["course"]
        )

        try:
            _, url = start_checkout(request.user, [course])
        except AlreadyEnrolled:
            return Response(
                {"detail": "You are already enrolled in this course.", "code": "already_enrolled"},
                status=status.HTTP_409_CONFLICT,
            )
        except stripe.StripeError:
            logger.exception("Stripe refused a checkout for user %s.", request.user.pk)
            return Response(
                {"detail": "Payment is unavailable right now."},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        return Response({"url": url}, status=status.HTTP_201_CREATED)


class CheckoutSessionView(APIView):
    """The order a Checkout Session paid for, fulfilled first if Stripe reports it paid.

    404 unless the session is one of the requesting user's orders. While Stripe
    hasn't reported payment, or can't be reached, the order comes back ``pending``.
    """

    def get(self, request, session_id):
        order = confirm(get_object_or_404(Order, user=request.user, payment_ref=session_id))
        order = Order.objects.prefetch_related("items__course").get(pk=order.pk)
        return Response(OrderSerializer(order).data)
