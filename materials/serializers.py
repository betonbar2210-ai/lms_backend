from rest_framework import serializers

from materials.models import Course, Material


class MaterialSerializer(serializers.ModelSerializer):
    class Meta:
        model = Material
        fields = "__all__"


class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = "__all__"


class CourseDetailSerializer(serializers.ModelSerializer):
    count_material = serializers.SerializerMethodField()
    material = MaterialSerializer(many=True, read_only=True)

    class Meta:
        model = Course
        fields = [
            "id",
            "name",
            "description",
            "count_material",
            "material",
        ]

    def get_count_material(self, obj):
        return obj.material.count()
