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


class Appointment(models.Model):
    STATUS_CHOICES = [
        ('booked', 'Booked'),
        ('completed', 'Completed'),
        ('no_show', 'No Show'),
    ]

    SOURCE_CHOICES = [
        ('online', 'Online Booking'),
        ('walk_in', 'Walk-In'),
    ]

    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='appointments')
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='appointments')
    slot = models.ForeignKey(Slot, on_delete=models.SET_NULL, null=True, blank=True, related_name='appointment')
    date = models.DateField()
    ticket_number = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='booked')
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='online')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['date', 'ticket_number']

    def __str__(self):
        return f"Ticket #{self.ticket_number} - {self.patient.username} with {self.doctor.name} ({self.date})"

class Profile(models.Model):
    ROLE_CHOICES = [
        ('patient', 'Patient'),
        ('staff', 'Staff Admin'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='patient')
    phone = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return f"{self.user.username} ({self.role})"

class Notification(models.Model):
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, related_name='notifications')
    message = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Notification for {self.appointment.patient.username}: {self.message}"