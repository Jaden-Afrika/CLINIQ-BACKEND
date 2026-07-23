from django.shortcuts import render
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import transaction
from django.utils import timezone
from .models import Profile, Doctor, Slot, Appointment, Notification
from .serializers import (
    RegisterSerializer, ProfileSerializer, DoctorSerializer, SlotSerializer,
    BookAppointmentSerializer, AppointmentSerializer, MyTicketSerializer, NowServingSerializer,
    AdminAppointmentSerializer, UpdateStatusSerializer
)


class IsStaffAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        try:
            return request.user.profile.role == 'staff'
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
            appointment=appointment,
            message=f"Your visit with {doctor.name} has been completed."
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
        appointment.status = new_status
        appointment.save()

        if new_status == 'completed':
            message = f"Your visit with {appointment.doctor.name} has been completed."
        else:
            message = f"You were marked as a no-show for your appointment with {appointment.doctor.name}."
        Notification.objects.create(appointment=appointment, message=message)

        return Response(AdminAppointmentSerializer(appointment).data)
