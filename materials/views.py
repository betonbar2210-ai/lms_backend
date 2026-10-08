from django.shortcuts import render

from materials.models import Course, Material
from materials.serializers import CourseSerializer, MaterialSerializer
from rest_framework import viewsets, generics


# Create your views here.
class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer


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





