from django.db import models

# Create your models here.
class Course(models.Model):
    name = models.CharField(max_length=100 , default="Без названия")
    description = models.TextField(blank=True, null=True)
    preview = models.ImageField(upload_to='courses/', blank=True, null=True)

    class Meta:
        verbose_name = 'Course'
        verbose_name_plural = 'Courses'

    def __str__(self):
        return self.name


class Material(models.Model):
    name = models.CharField(max_length=100, default="Без названия")
    description = models.TextField(blank=True, null=True)
    preview = models.ImageField(upload_to='materials/', blank=True, null=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, blank=True, null=False)
    video = models.FileField(upload_to='videos/', blank=True, null=True)

    class Meta:
        verbose_name = 'Material'
        verbose_name_plural = 'Materials'

    def __str__(self):
        return f'{self.name} - {self.course.name}'
