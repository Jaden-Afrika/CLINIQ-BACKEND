from django.shortcuts import render
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Profile
from .serializers import RegisterSerializer, ProfileSerializer
from rest_framework import generics
from .models import Doctor, Slot
from .serializers import DoctorSerializer, SlotSerializer
from django.db import transaction
from django.utils import timezone
from rest_framework.response import Response
from rest_framework import status
from .models import Appointment, Slot
from .serializers import BookAppointmentSerializer, AppointmentSerializer



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

class RegisterView(generics.CreateAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = RegisterSerializer


class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        profile = Profile.objects.get(user=request.user)
        return Response(ProfileSerializer(profile).data)

        
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