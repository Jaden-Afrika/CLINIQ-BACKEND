from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import (
    RegisterView, MeView, DoctorListView, SlotListView,
    BookAppointmentView, MyTicketView, NowServingView,
    AdminTodayQueueView, AdminNextView, AdminUpdateStatusView,
    AdminRequestListView, AdminRequestDetailView,
    NotificationListView, NotificationUnreadCountView, NotificationMarkReadView,
    DoctorScheduledAppointmentsView, DoctorFreeSlotsView, DoctorDashboardView,
    DoctorDiagnosisView, PatientServiceRatingView,
)

urlpatterns = [
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/login/', TokenObtainPairView.as_view(), name='login'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/me/', MeView.as_view(), name='me'),
    path('notifications/', NotificationListView.as_view(), name='notification-list'),
    path('notifications/unread-count/', NotificationUnreadCountView.as_view(), name='notification-unread-count'),
    path('notifications/<int:notification_id>/read/', NotificationMarkReadView.as_view(), name='notification-mark-read'),
    path('auth/admin-requests/', AdminRequestListView.as_view(), name='admin-request-list'),
    path('auth/admin-requests/<int:user_id>/', AdminRequestDetailView.as_view(), name='admin-request-detail'),
    path('doctors/', DoctorListView.as_view(), name='doctor-list'),
    path('slots/', SlotListView.as_view(), name='slot-list'),
    path('appointments/book/', BookAppointmentView.as_view(), name='book-appointment'),
    path('appointments/my-ticket/', MyTicketView.as_view(), name='my-ticket'),
    path('appointments/<int:appointment_id>/rating/', PatientServiceRatingView.as_view(), name='appointment-rating'),
    path('doctors/<int:doctor_id>/now-serving/', NowServingView.as_view(), name='now-serving'),
    path('doctor/appointments/', DoctorScheduledAppointmentsView.as_view(), name='doctor-scheduled-appointments'),
    path('doctor/free-slots/', DoctorFreeSlotsView.as_view(), name='doctor-free-slots'),
    path('doctor/dashboard/', DoctorDashboardView.as_view(), name='doctor-dashboard'),
    path('doctor/appointments/<int:appointment_id>/diagnosis/', DoctorDiagnosisView.as_view(), name='doctor-diagnosis'),
    path('admin/queue/', AdminTodayQueueView.as_view(), name='admin-queue'),
    path('admin/doctors/<int:doctor_id>/next/', AdminNextView.as_view(), name='admin-next'),
    path('admin/appointments/<int:appointment_id>/status/', AdminUpdateStatusView.as_view(), name='admin-update-status'),
]
