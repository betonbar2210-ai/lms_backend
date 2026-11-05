import logging

import stripe
from django.urls import reverse
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import generics, status, viewsets
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from config import settings
from materials.models import Course, Material
from users.models import Payments, Subscriptions, User
from users.permissions import IsSelfOrReadOnly, is_moderator
from users.serializers import (
    MyTokenObtainPairSerializer,
    PaymentCreateRequestSerializer,
    PaymentSerializer,
    SubscriptionToggleSerializer,
    UserPrivateSerializer,
    UserRegisterSerializer,
    UsersSerializer,
)

logger = logging.getLogger(__name__)

stripe.api_key = settings.STRIPE_TEST_KEY


@extend_schema(
    summary="Создание платежа через Stripe",
    description=(
        "Создает продукт, цену и сессию оплаты в Stripe. "
        "Сохраняет все идентификаторы и ссылку на оплату в базе. "
        "Возвращает URL для перенаправления пользователя на страницу оплаты."
    ),
    request=PaymentCreateRequestSerializer,
    responses={
        200: OpenApiResponse(
            description="Успешное создание сессии",
            response={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "format": "uri",
                        "example": "https://checkout.stripe.com/...",
                    },
                    "session_id": {"type": "string", "example": "cs_test_..."},
                    "payment_id": {"type": "integer", "example": 1},
                },
            },
        ),
        400: OpenApiResponse(
            description="Ошибка валидации данных, нулевая цена или ошибка Stripe"
        ),
        404: OpenApiResponse(description="Курс или урок не найден"),
    },
)
class CreateStripePaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PaymentCreateRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        course_id = serializer.validated_data.get("course_id")
        lesson_id = serializer.validated_data.get("lesson_id")

        # Получаем объект (курс или урок)
        if course_id:
            try:
                paid_object = Course.objects.get(id=course_id)
            except Course.DoesNotExist:
                return Response(
                    {"error": "Курс не найден"}, status=status.HTTP_404_NOT_FOUND
                )
            item_type = "курс"
        else:
            try:
                paid_object = Material.objects.get(id=lesson_id)
            except Material.DoesNotExist:
                return Response(
                    {"error": "Урок не найден"}, status=status.HTTP_404_NOT_FOUND
                )
            item_type = "урок"

        if paid_object.price <= 0:
            return Response(
                {"error": "Стоимость курса или урока должна быть больше нуля"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # 1. Создание продукта в Stripe
            product = stripe.Product.create(
                name=paid_object.name,
                description=f"Оплата за {item_type}: {paid_object.name}",
            )

            # 2. Создание цены (переводим рубли в копейки)
            amount_in_cents = int(paid_object.price * 100)
            price = stripe.Price.create(
                product=product.id,
                unit_amount=amount_in_cents,
                currency=settings.STRIPE_CURRENCY,
            )

            # 3. Создание сессии оплаты
            success_url = (
                request.build_absolute_uri(reverse("users:payment_success"))
                + "?session_id={CHECKOUT_SESSION_ID}"
            )
            cancel_url = (
                request.build_absolute_uri(reverse("users:payment_cancel"))
                + "?session_id={CHECKOUT_SESSION_ID}"
            )
            session = stripe.checkout.Session.create(
                line_items=[{"price": price.id, "quantity": 1}],
                mode="payment",
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={
                    "user_id": str(request.user.id),
                    "course_id": str(course_id or ""),
                    "lesson_id": str(lesson_id or ""),
                    "amount": str(amount_in_cents),
                },
            )

            # 4. Сохраняем платеж со всеми данными Stripe
            payment = Payments.objects.create(
                user=request.user,
                course=paid_object if course_id else None,
                lesson=paid_object if lesson_id else None,
                total=paid_object.price,
                method="stripe",
                status="pending",
                stripe_product_id=product.id,
                stripe_price_id=price.id,
                stripe_session_id=session.id,
                stripe_payment_url=session.url,
            )

            return Response(
                {
                    "url": session.url,
                    "session_id": session.id,
                    "payment_id": payment.id,
                },
                status=status.HTTP_200_OK,
            )

        except stripe.error.StripeError:
            logger.exception("Ошибка Stripe при создании платежа")
            return Response(
                {"error": "Не удалось создать платеж в Stripe. Попробуйте позже."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception:
            logger.exception("Неожиданная ошибка при создании платежа")
            return Response(
                {"error": "Внутренняя ошибка сервера"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


@extend_schema(
    summary="Успешное завершение оплаты",
    description=(
        "Вызывается редиректом Stripe после оплаты. Проверяет статус сессии "
        "в Stripe и синхронизирует статус платежа в базе."
    ),
    parameters=[
        OpenApiParameter(
            name="session_id",
            type=str,
            location=OpenApiParameter.QUERY,
            required=True,
            description="ID сессии Stripe",
        )
    ],
    responses={
        200: OpenApiResponse(
            description="Статус платежа",
            response={
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                    "status": {
                        "type": "string",
                        "enum": ["paid", "pending", "canceled", "failed"],
                    },
                    "payment_id": {"type": "integer"},
                },
            },
        ),
        400: OpenApiResponse(description="Отсутствует session_id или ошибка Stripe"),
        404: OpenApiResponse(description="Платеж не найден"),
    },
    auth=[],
)
class PaymentSuccessView(APIView):
    """Обрабатывает перенаправление от Stripe после успешной оплаты"""

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        session_id = request.query_params.get("session_id")

        if not session_id:
            return Response(
                {"error": "Отсутствует session_id"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            session = stripe.checkout.Session.retrieve(session_id)
        except stripe.error.StripeError:
            logger.exception("Ошибка Stripe при проверке сессии %s", session_id)
            return Response(
                {"error": "Не удалось проверить статус оплаты в Stripe"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            payment = Payments.objects.get(stripe_session_id=session_id)
        except Payments.DoesNotExist:
            return Response(
                {"error": "Запись о платеже не найдена в базе данных"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Проверяем, что сессия Stripe относится именно к этому платежу
        raw_metadata = getattr(session, "metadata", None)
        if hasattr(raw_metadata, "to_dict"):
            raw_metadata = raw_metadata.to_dict()
        metadata_user_id = (raw_metadata or {}).get("user_id")
        if metadata_user_id and str(metadata_user_id) != str(payment.user_id):
            logger.warning(
                "Сессия %s не принадлежит платежу %s", session_id, payment.id
            )
            return Response(
                {"error": "Сессия не принадлежит текущему платежу"},
                status=status.HTTP_403_FORBIDDEN,
            )

        payment_status = session.payment_status

        if payment_status in ("paid", "no_payment_required"):
            if payment.status != "paid":
                payment.status = "paid"
                payment.save(update_fields=["status"])
            return Response(
                {
                    "message": "Оплата прошла успешно! Материал доступен.",
                    "status": "paid",
                    "payment_id": payment.id,
                },
                status=status.HTTP_200_OK,
            )

        if payment_status == "unpaid":
            return Response(
                {
                    "message": "Оплата в обработке или не завершена.",
                    "status": "pending",
                    "payment_id": payment.id,
                },
                status=status.HTTP_200_OK,
            )

        # Любой другой статус Stripe — отдаем текущее состояние платежа
        return Response(
            {
                "message": "Статус оплаты уточняется.",
                "status": payment.status,
                "payment_id": payment.id,
            },
            status=status.HTTP_200_OK,
        )


@extend_schema(
    summary="Отмена оплаты",
    description=(
        "Вызывается редиректом Stripe, если пользователь отказался от оплаты. "
        "Переводит платеж в статус canceled, если он еще не оплачен."
    ),
    parameters=[
        OpenApiParameter(
            name="session_id",
            type=str,
            location=OpenApiParameter.QUERY,
            required=False,
            description="ID сессии Stripe",
        )
    ],
    responses={
        200: OpenApiResponse(
            description="Платеж отменен или уже был оплачен",
            response={
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                    "status": {"type": "string"},
                    "payment_id": {"type": "integer"},
                },
            },
        ),
    },
    auth=[],
)
class PaymentCancelView(APIView):
    """Обрабатывает перенаправление, если пользователь закрыл страницу оплаты"""

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        session_id = request.query_params.get("session_id")
        payment = None

        if session_id:
            payment = Payments.objects.filter(stripe_session_id=session_id).first()
            # Не откатываем уже оплаченный платеж обратно в canceled
            if payment and payment.status not in ("paid", "canceled"):
                payment.status = "canceled"
                payment.save(update_fields=["status"])

        response_data = {
            "message": "Оплата была отменена. Вы можете попробовать снова.",
            "status": payment.status if payment else "canceled",
        }
        if payment:
            response_data["payment_id"] = payment.id

        return Response(response_data, status=status.HTTP_200_OK)


class UsersViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UsersSerializer

    def get_serializer_class(self):
        if self.action == "create":
            return UserRegisterSerializer
        if self.action == "retrieve" and not getattr(self, "swagger_fake_view", False):
            if self.get_object() == self.request.user:
                return UserPrivateSerializer
        return UsersSerializer

    def get_permissions(self):
        # Создавать пользователей может любой авторизованный,
        # просматривать — любой, изменять — только свой профиль.
        if self.action == "create":
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsSelfOrReadOnly()]

    def get_queryset(self):
        queryset = User.objects.all()
        if self.action == "retrieve":
            queryset = queryset.prefetch_related("payments")
        return queryset


class UserRegisterAPIView(generics.CreateAPIView):
    serializer_class = UserRegisterSerializer
    permission_classes = [AllowAny]


class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PaymentSerializer
    queryset = Payments.objects.none()

    filter_backends = [DjangoFilterBackend, OrderingFilter]

    filterset_fields = ("course", "lesson", "method")

    ordering_fields = ("date",)
    ordering = ["-date"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Payments.objects.none()
        queryset = Payments.objects.select_related("user", "course", "lesson")
        if is_moderator(self.request.user) or self.request.user.is_staff:
            return queryset
        return queryset.filter(user=self.request.user)


@extend_schema(
    summary="Подписка на курс",
    description=(
        "Создает подписку на курс, если ее нет, или удаляет существующую. "
        "Повторный вызов переключает состояние подписки."
    ),
    request=SubscriptionToggleSerializer,
    responses={
        200: OpenApiResponse(
            description="Результат переключения подписки",
            response={
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "enum": ["подписка добавлена", "подписка удалена"],
                    }
                },
            },
        ),
    },
)
class SubscriptionsToggleAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = SubscriptionToggleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        course = serializer.validated_data["course"]

        subscription, created = Subscriptions.objects.get_or_create(
            user=request.user,
            course=course,
        )

        if created:
            message = "подписка добавлена"
        else:
            subscription.delete()
            message = "подписка удалена"

        return Response({"message": message})


class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer
    permission_classes = [AllowAny]
