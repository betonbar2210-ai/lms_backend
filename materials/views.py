from rest_framework import generics, viewsets

from materials.models import Course, Material
from materials.serializers import (
    CourseDetailSerializer,
    CourseSerializer,
    MaterialSerializer,
)


class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer

    def get_serializer_class(self):
        if self.action == "retrieve":
            return CourseDetailSerializer
        return CourseSerializer


class MaterialCreateAPIView(generics.CreateAPIView):
    serializer_class = MaterialSerializer


class MaterialListAPIView(generics.ListAPIView):
    serializer_class = MaterialSerializer
    queryset = Material.objects.all()


class MaterialRetrieveAPIView(generics.RetrieveAPIView):
    serializer_class = MaterialSerializer
    queryset = Material.objects.all()


class MaterialUpdateAPIView(generics.UpdateAPIView):
    serializer_class = MaterialSerializer
    queryset = Material.objects.all()


class MaterialDestroyAPIView(generics.DestroyAPIView):
    queryset = Material.objects.all()
