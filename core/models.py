from django.db import models

# Create your models here.

from django.db import models
from django.contrib.auth.models import User


class Doctor(models.Model):
    name = models.CharField(max_length=255)
    specialty = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.name


class Slot(models.Model):
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='slots')
    date = models.DateField()
    start_time = models.TimeField()
    is_booked = models.BooleanField(default=False)

    class Meta:
        ordering = ['date', 'start_time']

    def __str__(self):
        return f"{self.doctor.name} - {self.date} {self.start_time}"