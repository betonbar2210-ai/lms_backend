import stripe
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import generics, viewsets, status
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
    PaymentSerializer,
    SubscriptionToggleSerializer,
    UserPrivateSerializer,
    UserRegisterSerializer,
    UsersSerializer,
    PaymentCreateRequestSerializer,
)

stripe.api_key = settings.STRIPE_TEST_KEY


@extend_schema(
    summary="Создание платежа через Stripe",
    description="Создает продукт, цену и сессию оплаты в Stripe. Возвращает URL для перенаправления пользователя на страницу оплаты.",
    request=PaymentCreateRequestSerializer,  # <-- ЭТО заставит Swagger показать поля!
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
                },
            },
        ),
        400: OpenApiResponse(description="Ошибка валидации данных или ошибка Stripe"),
        404: OpenApiResponse(description="Курс или урок не найден"),
    },
)
class CreateStripePaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        course_id = request.data.get("course_id")
        lesson_id = request.data.get("lesson_id")

        if bool(course_id) == bool(lesson_id):
            return Response(
                {"error": "Укажите либо course_id, либо lesson_id (не оба сразу)"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Получаем объект (курс или урок)
        paid_object = None
        if course_id:
            try:
                paid_object = Course.objects.get(id=course_id)
            except Course.DoesNotExist:
                return Response(
                    {"error": "Курс не найден"}, status=status.HTTP_404_NOT_FOUND
                )
        elif lesson_id:
            try:
                paid_object = Material.objects.get(id=lesson_id)
            except Material.DoesNotExist:
                return Response(
                    {"error": "Урок не найден"}, status=status.HTTP_404_NOT_FOUND
                )

        try:
            # 1. Создание Продукта в Stripe
            product = stripe.Product.create(
                name=(
                    paid_object.name
                    if hasattr(paid_object, "name")
                    else paid_object.title
                ),
                description=f"Оплата за "
                            f"{'курс' if course_id else 'урок'}: {paid_object.name if hasattr(paid_object, 'name') else paid_object.title}",
            )

            # 2. Создание Цены (конвертируем Decimal в копейки/центы)
            amount_in_cents = int(
                paid_object.price * 100
            )  # Если price = Decimal('1500.50'), то 150050

            price = stripe.Price.create(
                product=product.id,
                unit_amount=amount_in_cents,
                currency="rub",
            )

            # 3. Создание Сессии оплаты
            from django.urls import reverse

            success_url = (
                request.build_absolute_uri(reverse("users:payment_success"))
                + "?session_id={CHECKOUT_SESSION_ID}"
            )
            cancel_url = request.build_absolute_uri(reverse("users:payment_cancel"))
            session = stripe.checkout.Session.create(
                line_items=[
                    {
                        "price": price.id,
                        "quantity": 1,
                    }
                ],
                mode="payment",
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={
                    "user_id": request.user.id,
                    "course_id": course_id or "",
                    "lesson_id": lesson_id or "",
                    "amount": amount_in_cents,
                },
            )

            # 4. Создаем запись в БД со статусом 'pending'
            Payments.objects.create(
                user=request.user,
                course=paid_object if course_id else None,
                lesson=paid_object if lesson_id else None,
                total=paid_object.price,
                method="stripe",
                status="pending",
                stripe_session_id=session.id,
            )

            # Возвращаем URL для редиректа на Stripe
            return Response(
                {"url": session.url, "session_id": session.id},
                status=status.HTTP_200_OK,
            )

        except stripe.error.StripeError as e:
            return Response(
                {"error": f"Ошибка Stripe: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PaymentSuccessView(APIView):
    """Обрабатывает перенаправление от Stripe после успешной оплаты"""

    def get(self, request):
        session_id = request.query_params.get("session_id")

        if not session_id:
            return Response(
                {"error": "Отсутствует session_id"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # 1. Проверяем статус сессии напрямую в Stripe (для надежности)
            session = stripe.checkout.Session.retrieve(session_id)

            # 2. Находим наш платеж в базе данных
            try:
                payment = Payments.objects.get(stripe_session_id=session_id)

                # 3. Если Stripe говорит, что оплачено, меняем статус у нас в БД
                if session.payment_status == "paid" and payment.status != "paid":
                    payment.status = "paid"
                    payment.save()
                    return Response(
                        {
                            "message": "Оплата прошла успешно! Курс доступен.",
                            "status": "paid",
                            "payment_id": payment.id,
                        },
                        status=status.HTTP_200_OK,
                    )
                elif session.payment_status == "unpaid":
                    return Response(
                        {
                            "message": "Оплата в обработке или не завершена.",
                            "status": "pending",
                        },
                        status=status.HTTP_200_OK,
                    )

            except Payments.DoesNotExist:
                return Response(
                    {"error": "Запись о платеже не найдена в базе данных"},
                    status=status.HTTP_404_NOT_FOUND,
                )

        except stripe.error.StripeError as e:
            return Response(
                {"error": f"Ошибка проверки в Stripe: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PaymentCancelView(APIView):
    """Обрабатывает перенаправление, если пользователь закрыл страницу оплаты"""

    def get(self, request):
        return Response(
            {
                "message": "Оплата была отменена. Вы можете попробовать снова.",
                "status": "canceled",
            },
            status=status.HTTP_200_OK,
        )


class UsersViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UsersSerializer

    def get_serializer_class(self):
        if self.action == "create":
            return UserRegisterSerializer
        if self.action == "retrieve" and self.get_object() == self.request.user:
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

    filter_backends = [DjangoFilterBackend, OrderingFilter]

    filterset_fields = ("course", "lesson", "method")

    ordering_fields = ("date",)
    ordering = ["-date"]

    def get_queryset(self):
        queryset = Payments.objects.select_related("user", "course", "lesson")
        if is_moderator(self.request.user) or self.request.user.is_staff:
            return queryset
        return queryset.filter(user=self.request.user)


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
