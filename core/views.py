from django.shortcuts import render
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils import timezone
from .models import Profile, Doctor, Slot, Appointment, Notification, ServiceRating
from .serializers import (
    RegisterSerializer, ProfileSerializer, DoctorSerializer, SlotSerializer,
    BookAppointmentSerializer, AppointmentSerializer, MyTicketSerializer, NowServingSerializer,
    AdminAppointmentSerializer, UpdateStatusSerializer, AdminRequestSerializer,
    ReviewAdminRequestSerializer, NotificationSerializer,
    DiagnosisSerializer, DoctorAppointmentSerializer, ServiceRatingSerializer,
)


class IsStaffAdmin(permissions.BasePermission):
    """Allow approved staff and super admins to use operational admin tools."""
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        try:
            profile = request.user.profile
            return (
                profile.role == 'super_admin'
                or (profile.role == 'staff' and profile.is_approved)
            )
        except Profile.DoesNotExist:
            return False


class IsSuperAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        try:
            return request.user.profile.role == 'super_admin'
        except Profile.DoesNotExist:
            return False


class IsDoctor(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        try:
            return request.user.profile.role == 'doctor' and request.user.profile.is_approved
        except Profile.DoesNotExist:
            return False


class RegisterView(generics.CreateAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = RegisterSerializer


class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        profile = Profile.objects.get(user=request.user)
        return Response(ProfileSerializer(profile).data)


class NotificationListView(generics.ListAPIView):
    """List notifications created for the authenticated patient's appointments."""
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).select_related(
            'appointment'
        ).order_by('-created_at')


class NotificationUnreadCountView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        count = Notification.objects.filter(
            user=request.user,
            is_read=False,
        ).count()
        return Response({'unread_count': count})


class NotificationMarkReadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, notification_id):
        notification = get_object_or_404(
            Notification.objects.select_related('appointment'),
            id=notification_id,
            user=request.user,
        )
        if not notification.is_read:
            notification.is_read = True
            notification.save(update_fields=['is_read'])
        return Response(NotificationSerializer(notification).data)


class AdminRequestListView(generics.ListAPIView):
    """Super-admin-only list of staff accounts awaiting a review decision."""
    serializer_class = AdminRequestSerializer
    permission_classes = [IsSuperAdmin]

    def get_queryset(self):
        return Profile.objects.filter(
            role__in=['staff', 'doctor'], is_approved=False, approval_status='pending'
        ).select_related('user').order_by('user__date_joined')


class AdminRequestDetailView(APIView):
    """Approve or durably reject a staff account request."""
    permission_classes = [IsSuperAdmin]

    def patch(self, request, user_id):
        serializer = ReviewAdminRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile = get_object_or_404(Profile, user_id=user_id, role__in=['staff', 'doctor'])

        is_approved = serializer.validated_data['is_approved']
        profile.is_approved = is_approved
        profile.approval_status = 'approved' if is_approved else 'rejected'
        profile.save(update_fields=['is_approved', 'approval_status'])

        return Response({
            'id': profile.user_id,
            'username': profile.user.username,
            'phone': profile.phone,
            'is_approved': profile.is_approved,
            'approval_status': profile.approval_status,
        })


class DoctorListView(generics.ListAPIView):
    queryset = Doctor.objects.all()
    serializer_class = DoctorSerializer
    permission_classes = [permissions.IsAuthenticated]


class SlotListView(generics.ListAPIView):
    serializer_class = SlotSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = Slot.objects.filter(is_booked=False)
        doctor_id = self.request.query_params.get('doctor')
        if doctor_id:
            queryset = queryset.filter(doctor_id=doctor_id)
        return queryset


class BookAppointmentView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = BookAppointmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        slot_id = serializer.validated_data['slot_id']

        with transaction.atomic():
            slot = Slot.objects.select_for_update().get(id=slot_id)
            if slot.is_booked:
                return Response(
                    {"detail": "This slot is already booked."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            today_count = Appointment.objects.filter(
                doctor=slot.doctor, date=slot.date
            ).count()
            ticket_number = today_count + 1

            appointment = Appointment.objects.create(
                patient=request.user,
                doctor=slot.doctor,
                slot=slot,
                date=slot.date,
                ticket_number=ticket_number,
                status='booked',
                source='online',
            )

            slot.is_booked = True
            slot.save()

            if slot.doctor.user_id:
                Notification.objects.create(
                    user=slot.doctor.user,
                    appointment=appointment,
                    message=(
                        f"A patient booked your appointment on {slot.date} at "
                        f"{slot.start_time.strftime('%H:%M')}."
                    ),
                )

        return Response(AppointmentSerializer(appointment).data, status=status.HTTP_201_CREATED)


class MyTicketView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        today = timezone.localdate()
        appointment = Appointment.objects.filter(
            patient=request.user, date=today, status='booked'
        ).order_by('-created_at').first()

        if not appointment:
            return Response({"detail": "No active ticket for today."}, status=status.HTTP_404_NOT_FOUND)

        return Response(MyTicketSerializer(appointment).data)


class DoctorScheduledAppointmentsView(generics.ListAPIView):
    """List the authenticated doctor's upcoming booked appointments."""
    serializer_class = DoctorAppointmentSerializer
    permission_classes = [IsDoctor]

    def get_queryset(self):
        return Appointment.objects.filter(
            doctor__user=self.request.user,
            date__gte=timezone.localdate(),
            status='booked',
        ).select_related('patient').order_by('date', 'ticket_number')


class DoctorFreeSlotsView(generics.ListAPIView):
    serializer_class = SlotSerializer
    permission_classes = [IsDoctor]

    def get_queryset(self):
        return Slot.objects.filter(
            doctor__user=self.request.user,
            is_booked=False,
            date__gte=timezone.localdate(),
        ).order_by('date', 'start_time')


class DoctorDashboardView(generics.ListAPIView):
    """List completed treatments and recorded diagnoses for the logged-in doctor."""
    serializer_class = DoctorAppointmentSerializer
    permission_classes = [IsDoctor]

    def get_queryset(self):
        return Appointment.objects.filter(
            doctor__user=self.request.user,
            status='completed',
        ).select_related('patient', 'service_rating').order_by('-date', '-ticket_number')


class DoctorDiagnosisView(APIView):
    permission_classes = [IsDoctor]

    def patch(self, request, appointment_id):
        serializer = DiagnosisSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        appointment = get_object_or_404(
            Appointment,
            id=appointment_id,
            doctor__user=request.user,
            status='completed',
        )
        appointment.diagnosis = serializer.validated_data['diagnosis']
        appointment.save(update_fields=['diagnosis'])
        return Response(DoctorAppointmentSerializer(appointment).data)


class PatientServiceRatingView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, appointment_id):
        appointment = get_object_or_404(
            Appointment,
            id=appointment_id,
            patient=request.user,
            status='completed',
        )
        if hasattr(appointment, 'service_rating'):
            return Response(
                {'detail': 'You have already rated this appointment.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ServiceRatingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        rating = ServiceRating.objects.create(
            appointment=appointment,
            patient=request.user,
            doctor=appointment.doctor,
            rating=serializer.validated_data['rating'],
            comment=serializer.validated_data.get('comment', ''),
        )
        return Response(ServiceRatingSerializer(rating).data, status=status.HTTP_201_CREATED)


class NowServingView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, doctor_id):
        today = timezone.localdate()
        try:
            doctor = Doctor.objects.get(id=doctor_id)
        except Doctor.DoesNotExist:
            return Response({"detail": "Doctor not found."}, status=status.HTTP_404_NOT_FOUND)

        served_count = Appointment.objects.filter(
            doctor=doctor, date=today, status__in=['completed', 'no_show']
        ).count()

        data = {
            "doctor_id": doctor.id,
            "doctor_name": doctor.name,
            "now_serving": served_count + 1,
        }
        return Response(NowServingSerializer(data).data)


class AdminTodayQueueView(generics.ListAPIView):
    """Staff-only: list today's appointments for a doctor, ordered by ticket number."""
    serializer_class = AdminAppointmentSerializer
    permission_classes = [IsStaffAdmin]

    def get_queryset(self):
        today = timezone.localdate()
        queryset = Appointment.objects.filter(date=today)
        doctor_id = self.request.query_params.get('doctor')
        if doctor_id:
            queryset = queryset.filter(doctor_id=doctor_id)
        return queryset.order_by('ticket_number')


class AdminNextView(APIView):
    """Staff-only: advance the queue by marking the current 'now serving' ticket completed."""
    permission_classes = [IsStaffAdmin]

    def post(self, request, doctor_id):
        today = timezone.localdate()
        try:
            doctor = Doctor.objects.get(id=doctor_id)
        except Doctor.DoesNotExist:
            return Response({"detail": "Doctor not found."}, status=status.HTTP_404_NOT_FOUND)

        served_count = Appointment.objects.filter(
            doctor=doctor, date=today, status__in=['completed', 'no_show']
        ).count()
        current_ticket_number = served_count + 1

        appointment = Appointment.objects.filter(
            doctor=doctor, date=today, ticket_number=current_ticket_number, status='booked'
        ).first()

        if not appointment:
            return Response(
                {"detail": "No booked appointment at the current ticket number."},
                status=status.HTTP_404_NOT_FOUND
            )

        appointment.status = 'completed'
        appointment.save()

        Notification.objects.create(
            user=appointment.patient,
            appointment=appointment,
            message=f"Your visit with Dr {doctor.name} has been completed.",
        )

        return Response(AdminAppointmentSerializer(appointment).data)


class AdminUpdateStatusView(APIView):
    """Staff-only: mark a specific appointment completed or no_show directly."""
    permission_classes = [IsStaffAdmin]

    def patch(self, request, appointment_id):
        serializer = UpdateStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            appointment = Appointment.objects.get(id=appointment_id)
        except Appointment.DoesNotExist:
            return Response({"detail": "Appointment not found."}, status=status.HTTP_404_NOT_FOUND)

        new_status = serializer.validated_data['status']
        if appointment.status == new_status:
            return Response(AdminAppointmentSerializer(appointment).data)

        appointment.status = new_status
        appointment.save()

        if new_status == 'completed':
            message = f"Your visit with Dr {appointment.doctor.name} has been completed."
        else:
            message = (
                f"You missed your visit with Dr {appointment.doctor.name}. "
                "Please book another appointment if needed."
            )
        Notification.objects.create(
            user=appointment.patient,
            appointment=appointment,
            message=message,
        )

        return Response(AdminAppointmentSerializer(appointment).data)
