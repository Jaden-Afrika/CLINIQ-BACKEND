from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import (
    RegisterView, MeView, DoctorListView, SlotListView,
    BookAppointmentView, MyTicketView, NowServingView,
    AdminTodayQueueView, AdminNextView, AdminUpdateStatusView
)

urlpatterns = [
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/login/', TokenObtainPairView.as_view(), name='login'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/me/', MeView.as_view(), name='me'),
    path('doctors/', DoctorListView.as_view(), name='doctor-list'),
    path('slots/', SlotListView.as_view(), name='slot-list'),
    path('appointments/book/', BookAppointmentView.as_view(), name='book-appointment'),
    path('appointments/my-ticket/', MyTicketView.as_view(), name='my-ticket'),
    path('doctors/<int:doctor_id>/now-serving/', NowServingView.as_view(), name='now-serving'),
    path('admin/queue/', AdminTodayQueueView.as_view(), name='admin-queue'),
    path('admin/doctors/<int:doctor_id>/next/', AdminNextView.as_view(), name='admin-next'),
    path('admin/appointments/<int:appointment_id>/status/', AdminUpdateStatusView.as_view(), name='admin-update-status'),
]
