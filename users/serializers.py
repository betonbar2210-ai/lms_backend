from rest_framework import serializers

from users.models import Payments, User


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
            "date",
            "course",
            "lesson",
        ]

    def get_paid_item(self, obj):
        if obj.course:
            return obj.course.name
        if obj.lesson:
            return obj.lesson.name
        return "-"


class UsersSerializer(serializers.ModelSerializer):
    payments = PaymentSerializer(many=True, read_only=True)

    class Meta:
        model = User
        fields = ("id", "email", "phone", "city", "avatar", "payments")
