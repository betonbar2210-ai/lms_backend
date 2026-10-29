from rest_framework import serializers

from materials.models import Course, Material
from materials.validators import external_resources


class MaterialSerializer(serializers.ModelSerializer):
    class Meta:
        model = Material
        fields = "__all__"
        read_only_fields = ("owner",)
        extra_kwargs = {
            "video": {"validators": [external_resources]},
        }


class CourseSerializer(serializers.ModelSerializer):
    count_material = serializers.SerializerMethodField()
    is_subscribed = serializers.SerializerMethodField()

    def get_is_subscribed(self, obj):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False
        return obj.subscriptions.filter(user=user).exists()

    def get_count_material(self, obj):
        return obj.material.count()

    class Meta:
        model = Course
        fields = (
            "id",
            "name",
            "description",
            "owner",
            "count_material",
            "is_subscribed",
        )
        read_only_fields = ("owner",)


class CourseDetailSerializer(CourseSerializer):
    material = MaterialSerializer(many=True, read_only=True)

    class Meta(CourseSerializer.Meta):
        fields = CourseSerializer.Meta.fields + ("material",)
