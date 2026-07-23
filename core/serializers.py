from rest_framework import serializers
from django.contrib.auth.models import User
from django.utils import timezone
from .models import Profile, Doctor, Slot, Appointment, Notification, ServiceRating


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    # Super-admin accounts are provisioned server-side only.
    role = serializers.ChoiceField(choices=['patient', 'staff', 'doctor'], default='patient')
    phone = serializers.CharField(required=False, allow_blank=True)
    doctor_name = serializers.CharField(required=False, max_length=255)
    specialty = serializers.CharField(required=False, allow_blank=True, max_length=255)

    class Meta:
        model = User
        fields = ('username', 'email', 'password', 'role', 'phone', 'doctor_name', 'specialty')

    def validate(self, attrs):
        if attrs.get('role') == 'doctor' and not attrs.get('doctor_name'):
            raise serializers.ValidationError({'doctor_name': 'This field is required for doctors.'})
        return attrs

    def create(self, validated_data):
        role = validated_data.pop('role', 'patient')
        phone = validated_data.pop('phone', '')
        doctor_name = validated_data.pop('doctor_name', '')
        specialty = validated_data.pop('specialty', '')
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password'],
        )
        is_approved = role == 'patient'
        Profile.objects.create(
            user=user,
            role=role,
            phone=phone,
            is_approved=is_approved,
            approval_status='approved' if is_approved else 'pending',
        )
        if role == 'doctor':
            Doctor.objects.create(user=user, name=doctor_name, specialty=specialty)
        return user


class ProfileSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='user.id', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.CharField(source='user.email', read_only=True)

    class Meta:
        model = Profile
        fields = ('id', 'username', 'email', 'role', 'phone', 'is_approved')


class AdminRequestSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='user.id', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    date_joined = serializers.DateTimeField(source='user.date_joined', read_only=True)

    class Meta:
        model = Profile
        fields = ('id', 'username', 'phone', 'date_joined')


class ReviewAdminRequestSerializer(serializers.Serializer):
    is_approved = serializers.BooleanField()


class NotificationSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    appointment_id = serializers.IntegerField(source='appointment.id', read_only=True)

    class Meta:
        model = Notification
        fields = ('id', 'user', 'appointment_id', 'message', 'created_at', 'is_read')


class DoctorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Doctor
        fields = ('id', 'name', 'specialty')


class SlotSerializer(serializers.ModelSerializer):
    doctor_name = serializers.CharField(source='doctor.name', read_only=True)

    class Meta:
        model = Slot
        fields = ('id', 'doctor', 'doctor_name', 'date', 'start_time', 'is_booked')


class BookAppointmentSerializer(serializers.Serializer):
    slot_id = serializers.IntegerField()

    def validate_slot_id(self, value):
        try:
            slot = Slot.objects.get(id=value)
        except Slot.DoesNotExist:
            raise serializers.ValidationError("Slot not found.")
        if slot.is_booked:
            raise serializers.ValidationError("This slot is already booked.")
        return value


class AppointmentSerializer(serializers.ModelSerializer):
    doctor_name = serializers.CharField(source='doctor.name', read_only=True)
    patient_username = serializers.CharField(source='patient.username', read_only=True)

    class Meta:
        model = Appointment
        fields = (
            'id', 'ticket_number', 'doctor', 'doctor_name',
            'patient', 'patient_username', 'date', 'status', 'source', 'created_at'
        )
        read_only_fields = ('id', 'ticket_number', 'patient', 'status', 'created_at')


class NowServingSerializer(serializers.Serializer):
    doctor_id = serializers.IntegerField()
    doctor_name = serializers.CharField()
    now_serving = serializers.IntegerField()


class MyTicketSerializer(serializers.ModelSerializer):
    doctor_name = serializers.CharField(source='doctor.name', read_only=True)
    now_serving = serializers.SerializerMethodField()

    class Meta:
        model = Appointment
        fields = ('id', 'ticket_number', 'doctor', 'doctor_name', 'date', 'status', 'now_serving')

    def get_now_serving(self, obj):
        served_count = Appointment.objects.filter(
            doctor=obj.doctor, date=obj.date, status__in=['completed', 'no_show']
        ).count()
        return served_count + 1


class AdminAppointmentSerializer(serializers.ModelSerializer):
    doctor_name = serializers.CharField(source='doctor.name', read_only=True)
    patient_username = serializers.CharField(source='patient.username', read_only=True)

    class Meta:
        model = Appointment
        fields = (
            'id', 'ticket_number', 'doctor', 'doctor_name',
            'patient', 'patient_username', 'date', 'status', 'source', 'created_at'
        )


class UpdateStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=['completed', 'no_show'])


class DiagnosisSerializer(serializers.Serializer):
    diagnosis = serializers.CharField(allow_blank=True)


class ServiceRatingSerializer(serializers.ModelSerializer):
    patient_username = serializers.CharField(source='patient.username', read_only=True)

    class Meta:
        model = ServiceRating
        fields = ('id', 'patient', 'patient_username', 'doctor', 'rating', 'comment', 'created_at')
        read_only_fields = ('id', 'patient', 'doctor', 'created_at')


class DoctorAppointmentSerializer(serializers.ModelSerializer):
    patient_username = serializers.CharField(source='patient.username', read_only=True)
    rating = ServiceRatingSerializer(source='service_rating', read_only=True)

    class Meta:
        model = Appointment
        fields = (
            'id', 'ticket_number', 'patient', 'patient_username', 'date', 'status',
            'source', 'diagnosis', 'created_at', 'rating',
        )
