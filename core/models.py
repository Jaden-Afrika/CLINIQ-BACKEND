from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator


class Doctor(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='doctor_profile',
    )
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
    diagnosis = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['date', 'ticket_number']

    def __str__(self):
        return f"Ticket #{self.ticket_number} - {self.patient.username} with {self.doctor.name} ({self.date})"

class Profile(models.Model):
    ROLE_CHOICES = [
        ('patient', 'Patient'),
        ('staff', 'Staff Admin'),
        ('doctor', 'Doctor'),
        ('super_admin', 'Super Admin'),
    ]

    APPROVAL_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='patient')
    phone = models.CharField(max_length=20, blank=True)
    is_approved = models.BooleanField(default=True)
    approval_status = models.CharField(
        max_length=20,
        choices=APPROVAL_STATUS_CHOICES,
        default='approved',
    )

    def __str__(self):
        return f"{self.user.username} ({self.role})"

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, related_name='notifications')
    message = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Notification for {self.user.username}: {self.message}"


class ServiceRating(models.Model):
    appointment = models.OneToOneField(
        Appointment,
        on_delete=models.CASCADE,
        related_name='service_rating',
    )
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='service_ratings')
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='service_ratings')
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.rating}/5 for Dr {self.doctor.name}"
