from django.contrib import admin
from .models import Doctor, Slot, Appointment


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'specialty')


@admin.register(Slot)
class SlotAdmin(admin.ModelAdmin):
    list_display = ('id', 'doctor', 'date', 'start_time', 'is_booked')
    list_filter = ('doctor', 'date', 'is_booked')


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'ticket_number', 'patient', 'doctor', 'date', 'status', 'source')
    list_filter = ('doctor', 'date', 'status', 'source')
