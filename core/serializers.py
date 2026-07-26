from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from .models import Profile, Doctor, Slot, Appointment, Notification, ServiceRating


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    username = serializers.CharField(required=False, allow_blank=True, max_length=150)
    # Super-admin accounts are provisioned server-side only.
    role = serializers.ChoiceField(choices=['patient', 'staff', 'doctor'], default='patient')
    phone = serializers.CharField(required=False, allow_blank=True)
    doctor_name = serializers.CharField(required=False, max_length=255)
    specialty = serializers.CharField(required=False, allow_blank=True, max_length=255)
    full_name = serializers.CharField(required=False, allow_blank=True, max_length=255)

    class Meta:
        model = User
        fields = ('username', 'email', 'password', 'role', 'phone', 'doctor_name', 'specialty', 'full_name')

    def validate(self, attrs):
        if attrs.get('role') == 'doctor' and not attrs.get('doctor_name'):
            raise serializers.ValidationError({'doctor_name': 'This field is required for doctors.'})
        try:
            validate_password(attrs.get('password'))
        except DjangoValidationError as exc:
            raise serializers.ValidationError({'password': list(exc.messages)})
        return attrs

    def _make_username(self, full_name, email, role):
        if role == 'patient' and full_name:
            base = full_name.strip().lower().replace('.', '').replace(' ', '_')
            base = ''.join(ch for ch in base if ch.isalnum() or ch == '_') or 'patient'
            username = base
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f'{base}_{counter}'
                counter += 1
            return username
        if email:
            return email.split('@', 1)[0].lower().replace('.', '_').replace('-', '_')
        return 'patient'

    def create(self, validated_data):
        role = validated_data.pop('role', 'patient')
        phone = validated_data.pop('phone', '')
        doctor_name = validated_data.pop('doctor_name', '')
        specialty = validated_data.pop('specialty', '')
        full_name = validated_data.pop('full_name', '')
        email = validated_data.get('email', '')
        username = validated_data.get('username') or self._make_username(full_name, email, role)
        user = User.objects.create_user(
            username=username,
            email=email,
            password=validated_data['password'],
            first_name=full_name or validated_data.get('username', ''),
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

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        profile = getattr(instance, 'profile', None)
        if profile is not None:
            ret['role'] = profile.role
        ret['full_name'] = instance.get_full_name() or instance.username
        return ret


class ProfileSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='user.id', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.CharField(source='user.email', read_only=True)
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = ('id', 'username', 'email', 'full_name', 'role', 'phone', 'is_approved')

    def get_full_name(self, obj):
        return obj.user.get_full_name() or obj.user.username


class AccountSettingsSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', required=False, allow_blank=True)
    current_password = serializers.CharField(write_only=True, required=False)
    new_password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = Profile
        fields = ('username', 'email', 'phone', 'notifications_enabled', 'current_password', 'new_password')

    def validate(self, attrs):
        current_password = attrs.get('current_password')
        new_password = attrs.get('new_password')
        if bool(current_password) != bool(new_password):
            raise serializers.ValidationError('Provide both current_password and new_password to change your password.')
        if new_password:
            if not self.instance.user.check_password(current_password):
                raise serializers.ValidationError({'current_password': 'Current password is incorrect.'})
            try:
                validate_password(new_password, self.instance.user)
            except DjangoValidationError as exc:
                raise serializers.ValidationError({'new_password': list(exc.messages)})
        return attrs

    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', {})
        validated_data.pop('current_password', None)
        new_password = validated_data.pop('new_password', None)
        instance.phone = validated_data.get('phone', instance.phone)
        instance.notifications_enabled = validated_data.get('notifications_enabled', instance.notifications_enabled)
        instance.save(update_fields=['phone', 'notifications_enabled'])
        if 'email' in user_data:
            instance.user.email = user_data['email']
        if new_password:
            instance.user.set_password(new_password)
        if user_data or new_password:
            instance.user.save()
        return instance


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
    available_slots = serializers.IntegerField(read_only=True)
    class Meta:
        model = Doctor
        fields = ('id', 'name', 'specialty', 'bio', 'photo_url', 'available_slots')


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
    scheduled_time = serializers.TimeField(source='slot.start_time', read_only=True, allow_null=True)

    class Meta:
        model = Appointment
        fields = (
            'id', 'ticket_number', 'doctor', 'doctor_name',
            'patient', 'patient_username', 'date', 'scheduled_time', 'status', 'source',
            'diagnosis', 'treatment', 'created_at', 'completed_at',
        )


class UpdateStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=['completed', 'no_show'])


class DiagnosisSerializer(serializers.Serializer):
    diagnosis = serializers.CharField(allow_blank=True)


class TreatmentSerializer(serializers.Serializer):
    treatment = serializers.CharField(allow_blank=False)
    diagnosis = serializers.CharField(required=False, allow_blank=True)


class WalkInAppointmentSerializer(serializers.Serializer):
    username = serializers.CharField(write_only=True)
    password = serializers.CharField(required=False, write_only=True)
    phone = serializers.CharField(required=False, allow_blank=True)

    doctor_id = serializers.PrimaryKeyRelatedField(
        queryset=Doctor.objects.all(), source='doctor'
    )
    date = serializers.DateField(required=False)

    def validate(self, attrs):
        username = attrs.pop('username')
        password = attrs.pop('password', None) or '12345678'
        phone = attrs.pop('phone', '')

        try:
            user = User.objects.get(username=username)
            try:
                if user.profile.role != 'patient':
                    raise serializers.ValidationError({'username': 'Existing account is not a patient.'})
            except Profile.DoesNotExist:
                raise serializers.ValidationError({'username': 'Existing account has no profile.'})
        except User.DoesNotExist:
            user = User.objects.create_user(username=username, password=password)
            Profile.objects.create(user=user, role='patient', phone=phone)

        attrs['patient'] = user
        return attrs


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
            'source', 'diagnosis', 'treatment', 'created_at', 'completed_at', 'rating',
        )
