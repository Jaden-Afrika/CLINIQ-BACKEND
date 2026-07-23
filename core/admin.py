from django.contrib import admin
from .models import Doctor, Slot, Appointment
from .models import Doctor, Slot, Appointment, Profile, Notification

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

from .models import Doctor, Slot, Appointment, Profile

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'role', 'phone', 'is_approved', 'approval_status')
    list_filter = ('role', 'is_approved', 'approval_status')
    search_fields = ('user__username', 'phone')

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'appointment', 'message', 'created_at', 'is_read')
    list_filter = ('is_read',)
