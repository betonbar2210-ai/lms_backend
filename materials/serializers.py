from rest_framework import serializers

from materials.models import Course, Material


class MaterialSerializer(serializers.ModelSerializer):
    class Meta:
        model = Material
        fields = "__all__"
        read_only_fields = ("owner",)


class CourseSerializer(serializers.ModelSerializer):
    count_material = serializers.SerializerMethodField()

    def get_count_material(self, obj):
        return obj.material.count()

    class Meta:
        model = Course
        fields = ("id", "name", "description", "owner", "count_material")
        read_only_fields = ("owner",)


class CourseDetailSerializer(serializers.ModelSerializer):
    count_material = serializers.SerializerMethodField()
    material = MaterialSerializer(many=True, read_only=True)

    def get_count_material(self, obj):
        return obj.material.count()

    class Meta:
        model = Course
        fields = [
            "id",
            "name",
            "description",
            "owner",
            "count_material",
            "material",
        ]
        read_only_fields = ("owner",)
