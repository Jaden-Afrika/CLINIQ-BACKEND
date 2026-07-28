#Import necessary modules from Django framework
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
    # Connects a Doctor to a Django User in a 1-to-1 relationship. 
    # Optional field (null=True, blank=True).
    #  If the User is deleted, user becomes NULL so doctor details aren't wiped.

    name = models.CharField(max_length=255)
    specialty = models.CharField(max_length=255, blank=True)
    bio = models.TextField(blank=True)
    photo_url = models.URLField(blank=True)

# The __str__ method returns the doctor's name when the object is printed or displayed in the admin interface.
    def __str__(self):
        return self.name


class Slot(models.Model):
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='slots')
    date = models.DateField()
    start_time = models.TimeField()
    is_booked = models.BooleanField(default=False)

 #doctor: Many Slot entries link to one Doctor.
 #  If the doctor is deleted, delete their slots (CASCADE).
 # Access all slots for a doctor using doctor.slots.all().
#date: Stores calendar date (YYYY-MM-DD).
#start_time: Stores specific time (HH:MM:SS).
#is_booked: Boolean flag tracking slot availability. Starts as False.

    class Meta:
        ordering = ['date', 'start_time']
        # Automatically sorts slot queries chronologically by date, then start time.

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
    #patient: Links appointment to a User record.
    #doctor: Links appointment to a Doctor record.
    #slot: Links to a Slot optional record. If slot is removed, setting it to NULL preserves historical appointment data.
    #date: Booking date.

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='booked')
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='online')
    diagnosis = models.TextField(blank=True)
    treatment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

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
    #Role and approval status choices for user profiles.

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='patient')
    phone = models.CharField(max_length=20, blank=True)
    notifications_enabled = models.BooleanField(default=True)
    is_approved = models.BooleanField(default=True)
    approval_status = models.CharField(
        max_length=20,
        choices=APPROVAL_STATUS_CHOICES,
        default='approved',
    )

#user: Extends Django's standard user model with custom app attributes.
#role: Classifies permissions (patient, staff, doctor, super admin).
#phone: Stores phone numbers.
#notifications_enabled: Boolean toggle for notification preferences.
#is_approved / approval_status: Tracks administrative approval status for account activation.

    def __str__(self):
        return f"{self.user.username} ({self.role})"
    #Renders strings like "johndoe (patient)"

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
