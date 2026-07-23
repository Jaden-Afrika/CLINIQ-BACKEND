from rest_framework import serializers
from django.contrib.auth.models import User
from django.utils import timezone
from .models import Profile, Doctor, Slot, Appointment


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    role = serializers.ChoiceField(choices=Profile.ROLE_CHOICES, default='patient')
    phone = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'password', 'role', 'phone')

    def create(self, validated_data):
        role = validated_data.pop('role', 'patient')
        phone = validated_data.pop('phone', '')
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password'],
        )
        Profile.objects.create(user=user, role=role, phone=phone)
        return user


class ProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.CharField(source='user.email', read_only=True)

    class Meta:
        model = Profile
        fields = ('username', 'email', 'role', 'phone')


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
