import logging
import uuid

import stripe
from django.db.models import Prefetch, Q
from django.shortcuts import get_object_or_404
from rest_framework import generics, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from courses.models import Course
from users.permissions import IsAdmin

from .checkout import AlreadyEnrolled, confirm, start_checkout
from .models import Order, OrderItem, OrderStatus
from .serializers import (
    AdminOrderFiltersSerializer,
    AdminOrderListSerializer,
    OrderReceiptSerializer,
    OrderSerializer,
)

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


def my_orders(user):
    """Pending and expired orders are never shown: nothing was bought."""
    return (
        Order.objects.filter(user=user, status__in=[OrderStatus.PAID, OrderStatus.REFUNDED])
        .prefetch_related("items__course")
        .order_by("-created_at")
    )


class MyOrderListView(generics.ListAPIView):
    """The requester's paid and refunded orders, newest first. Unpaginated."""

    serializer_class = OrderSerializer
    pagination_class = None

    def get_queryset(self):
        return my_orders(self.request.user)


class MyOrderDetailView(generics.RetrieveAPIView):
    """One of the requester's paid or refunded orders; 404 for any other order."""

    serializer_class = OrderReceiptSerializer

    def get_queryset(self):
        return my_orders(self.request.user)


class AdminOrderListView(generics.ListAPIView):
    """Every order, whatever its status, newest first.

    ``q`` matches the buyer's name or email case-insensitively, or an exact
    order id; blank means no filter. ``status`` takes one value; an unknown
    value is a 400. A page past the last is a 404.
    """

    serializer_class = AdminOrderListSerializer
    permission_classes = [IsAdmin]

    def get_queryset(self):
        filters = AdminOrderFiltersSerializer(data=self.request.query_params)
        filters.is_valid(raise_exception=True)

        orders = Order.objects.select_related("user").prefetch_related(
            Prefetch(
                "items",
                queryset=OrderItem.objects.select_related("course").order_by("course__title"),
            )
        )

        query = self.request.query_params.get("q", "").strip()
        if query:
            match = Q(user__name__icontains=query) | Q(user__email__icontains=query)
            try:
                match |= Q(pk=uuid.UUID(query))
            except ValueError:
                pass
            orders = orders.filter(match)

        if status_filter := filters.validated_data.get("status"):
            orders = orders.filter(status=status_filter)

        return orders.order_by("-created_at")
