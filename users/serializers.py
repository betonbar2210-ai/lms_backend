from django.contrib.auth.password_validation import validate_password
from django.db import IntegrityError
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from materials.models import Course
from users.models import Payments, User


class UniqueEmailMixin:
    """Проверяет, что email ещё не занят (без учёта регистра)."""

    def validate_email(self, value):
        queryset = User.objects.filter(email__iexact=value)
        if self.instance is not None:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError(
                "Пользователь с таким email уже существует."
            )
        return value


class PaymentCreateRequestSerializer(serializers.Serializer):
    course_id = serializers.IntegerField(
        required=False, help_text="ID курса для оплаты"
    )
    lesson_id = serializers.IntegerField(
        required=False, help_text="ID урока для оплаты"
    )

    def validate(self, attrs):
        course_id = attrs.get("course_id")
        lesson_id = attrs.get("lesson_id")

        # Проверка: должен быть указан ИЛИ курс, ИЛИ урок (XOR)
        if not course_id and not lesson_id:
            raise serializers.ValidationError(
                "Необходимо указать либо course_id, либо lesson_id"
            )
        if course_id and lesson_id:
            raise serializers.ValidationError(
                "Укажите только course_id или lesson_id, а не оба сразу"
            )

        return attrs


class PaymentSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)
    paid_item = serializers.SerializerMethodField()

    class Meta:
        model = Payments
        fields = [
            "id",
            "user_email",
            "paid_item",
            "total",
            "method",
            "status",
            "date",
            "course",
            "lesson",
            "stripe_session_id",
            "stripe_product_id",
            "stripe_price_id",
            "stripe_payment_url",
        ]

    def get_paid_item(self, obj) -> str:
        if obj.course:
            return obj.course.name
        if obj.lesson:
            return obj.lesson.name
        return "-"


class UsersSerializer(UniqueEmailMixin, serializers.ModelSerializer):
    """Общая информация о пользователе: без истории платежей."""

    class Meta:
        model = User
        fields = ("id", "email", "phone", "city", "avatar")


class UserPrivateSerializer(UsersSerializer):
    """Полная информация, доступная только владельцу профиля."""

    payments = PaymentSerializer(many=True, read_only=True)

    class Meta(UsersSerializer.Meta):
        fields = UsersSerializer.Meta.fields + ("payments",)


class UserRegisterSerializer(UniqueEmailMixin, serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = User
        fields = ("id", "email", "password", "phone", "city", "avatar")

    def create(self, validated_data):
        try:
            return User.objects.create_user(**validated_data)
        except IntegrityError as error:
            raise serializers.ValidationError(
                {"email": "Пользователь с таким email уже существует."}
            ) from error


class SubscriptionToggleSerializer(serializers.Serializer):
    course_id = serializers.PrimaryKeyRelatedField(
        queryset=Course.objects.all(), source="course"
    )


class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = "email"

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["email"] = user.email

        return token
