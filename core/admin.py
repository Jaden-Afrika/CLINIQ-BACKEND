from django.contrib import admin

# Register your models here.

from django.contrib import admin
from .models import Doctor, Slot


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'specialty')


@admin.register(Slot)
class SlotAdmin(admin.ModelAdmin):
    list_display = ('id', 'doctor', 'date', 'start_time', 'is_booked')
    list_filter = ('doctor', 'date', 'is_booked')