from django.shortcuts import render
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import transaction
from django.utils import timezone
from .models import Profile, Doctor, Slot, Appointment
from .serializers import (
    RegisterSerializer, ProfileSerializer, DoctorSerializer, SlotSerializer,
    BookAppointmentSerializer, AppointmentSerializer, MyTicketSerializer, NowServingSerializer
)


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
