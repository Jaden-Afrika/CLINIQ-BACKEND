from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Appointment, Doctor, Notification, Profile, ServiceRating, Slot


class SeedDemoCommandTests(TestCase):
    def test_seed_demo_creates_five_dentistry_and_five_other_doctors(self):
        out = StringIO()

        call_command('seed_demo', stdout=out)

        dentistry_doctors = Doctor.objects.filter(specialty='Dentistry')
        other_doctors = Doctor.objects.exclude(specialty='Dentistry')

        self.assertGreaterEqual(dentistry_doctors.count(), 5)
        self.assertGreaterEqual(other_doctors.count(), 5)
        self.assertTrue(all(doctor.user is not None for doctor in Doctor.objects.all()))


class StaffApprovalTests(APITestCase):
    api_prefix = '/api'

    def register(self, username, role):
        return self.client.post(
            f'{self.api_prefix}/auth/register/',
            {'username': username, 'password': 'strong-password', 'role': role, 'phone': '0700000000'},
            format='json',
        )

    def create_profile(self, username, role, is_approved=True, approval_status='approved'):
        user = User.objects.create_user(username=username, password='strong-password')
        profile = Profile.objects.create(
            user=user,
            role=role,
            is_approved=is_approved,
            approval_status=approval_status,
        )
        return user, profile

    def test_new_staff_starts_unapproved(self):
        response = self.register('pending-staff', 'staff')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        profile = Profile.objects.get(user__username='pending-staff')
        self.assertFalse(profile.is_approved)
        self.assertEqual(profile.approval_status, 'pending')

    def test_new_patient_starts_approved(self):
        response = self.register('patient', 'patient')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        profile = Profile.objects.get(user__username='patient')
        self.assertTrue(profile.is_approved)
        self.assertEqual(profile.approval_status, 'approved')

    def test_public_registration_rejects_super_admin(self):
        response = self.register('not-a-super-admin', 'super_admin')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_pending_staff_can_log_in_and_me_includes_approval_state(self):
        self.register('pending-staff', 'staff')
        login_response = self.client.post(
            f'{self.api_prefix}/auth/login/',
            {'username': 'pending-staff', 'password': 'strong-password'},
            format='json',
        )

        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        self.assertIn('access', login_response.data)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}")
        me_response = self.client.get(f'{self.api_prefix}/auth/me/')

        self.assertEqual(me_response.status_code, status.HTTP_200_OK)
        self.assertEqual(me_response.data['username'], 'pending-staff')
        self.assertEqual(me_response.data['role'], 'staff')
        self.assertFalse(me_response.data['is_approved'])

    def test_pending_staff_cannot_use_admin_endpoints(self):
        user, _ = self.create_profile('pending-staff', 'staff', False, 'pending')
        self.client.force_authenticate(user=user)

        response = self.client.get(f'{self.api_prefix}/admin/queue/')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_approved_staff_can_use_admin_endpoints(self):
        user, _ = self.create_profile('approved-staff', 'staff')
        self.client.force_authenticate(user=user)

        response = self.client.get(f'{self.api_prefix}/admin/queue/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_super_admin_can_use_admin_endpoints(self):
        user, _ = self.create_profile('super-admin', 'super_admin')
        self.client.force_authenticate(user=user)

        response = self.client.get(f'{self.api_prefix}/admin/queue/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_super_admin_can_log_in_and_retrieve_their_profile(self):
        self.create_profile('super-admin', 'super_admin')

        login_response = self.client.post(
            f'{self.api_prefix}/auth/login/',
            {'username': 'super-admin', 'password': 'strong-password'},
            format='json',
        )

        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}")
        me_response = self.client.get(f'{self.api_prefix}/auth/me/')

        self.assertEqual(me_response.status_code, status.HTTP_200_OK)
        self.assertEqual(me_response.data['role'], 'super_admin')

    def test_non_super_admin_cannot_review_requests(self):
        user, _ = self.create_profile('staff', 'staff')
        self.client.force_authenticate(user=user)

        response = self.client.get(f'{self.api_prefix}/auth/admin-requests/')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_super_admin_can_list_and_approve_pending_staff(self):
        super_admin, _ = self.create_profile('super-admin', 'super_admin')
        pending_user, _ = self.create_profile('pending-staff', 'staff', False, 'pending')
        self.client.force_authenticate(user=super_admin)

        list_response = self.client.get(f'{self.api_prefix}/auth/admin-requests/')
        approve_response = self.client.patch(
            f'{self.api_prefix}/auth/admin-requests/{pending_user.id}/',
            {'is_approved': True},
            format='json',
        )

        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(list_response.data[0]['id'], pending_user.id)
        self.assertEqual(approve_response.status_code, status.HTTP_200_OK)
        pending_user.profile.refresh_from_db()
        self.assertTrue(pending_user.profile.is_approved)
        self.assertEqual(pending_user.profile.approval_status, 'approved')


class NotificationApiTests(APITestCase):
    api_prefix = '/api'

    def create_notification(self, username, message='Your appointment was completed.'):
        user = User.objects.create_user(username=username, password='strong-password')
        Profile.objects.create(user=user, role='patient')
        doctor = Doctor.objects.create(name=f'Dr {username}', specialty='General')
        appointment = Appointment.objects.create(
            patient=user,
            doctor=doctor,
            date=timezone.localdate(),
            ticket_number=1,
        )
        return user, Notification.objects.create(
            user=user,
            appointment=appointment,
            message=message,
        )

    def test_patient_can_list_only_their_notifications_and_unread_count(self):
        user, own_notification = self.create_notification('patient-one')
        self.create_notification('patient-two', 'Other patient notification')
        self.client.force_authenticate(user=user)

        list_response = self.client.get(f'{self.api_prefix}/notifications/')
        count_response = self.client.get(f'{self.api_prefix}/notifications/unread-count/')

        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual([item['id'] for item in list_response.data], [own_notification.id])
        self.assertEqual(count_response.data, {'unread_count': 1})

    def test_patient_can_mark_own_notification_as_read_but_not_another_patients(self):
        user, own_notification = self.create_notification('patient-one')
        _, other_notification = self.create_notification('patient-two')
        self.client.force_authenticate(user=user)

        read_response = self.client.patch(
            f'{self.api_prefix}/notifications/{own_notification.id}/read/',
            format='json',
        )
        forbidden_notification_response = self.client.patch(
            f'{self.api_prefix}/notifications/{other_notification.id}/read/',
            format='json',
        )

        self.assertEqual(read_response.status_code, status.HTTP_200_OK)
        self.assertTrue(read_response.data['is_read'])
        self.assertEqual(forbidden_notification_response.status_code, status.HTTP_404_NOT_FOUND)


class AppointmentStatusNotificationTests(APITestCase):
    api_prefix = '/api'

    def setUp(self):
        self.staff = User.objects.create_user(username='staff', password='strong-password')
        Profile.objects.create(user=self.staff, role='staff', is_approved=True)
        self.patient = User.objects.create_user(username='patient', password='strong-password')
        Profile.objects.create(user=self.patient, role='patient')
        self.doctor = Doctor.objects.create(name='Ada Lovelace', specialty='General')

    def create_appointment(self, ticket_number=1):
        return Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            date=timezone.localdate(),
            ticket_number=ticket_number,
        )

    def test_completed_status_creates_one_notification_for_the_patient(self):
        appointment = self.create_appointment()
        self.client.force_authenticate(user=self.staff)

        response = self.client.patch(
            f'{self.api_prefix}/admin/appointments/{appointment.id}/status/',
            {'status': 'completed'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        notification = Notification.objects.get(appointment=appointment)
        self.assertEqual(notification.user, self.patient)
        self.assertEqual(
            notification.message,
            'Your visit with Dr Ada Lovelace has been completed.',
        )
        self.assertFalse(notification.is_read)

        self.client.patch(
            f'{self.api_prefix}/admin/appointments/{appointment.id}/status/',
            {'status': 'completed'},
            format='json',
        )
        self.assertEqual(Notification.objects.filter(appointment=appointment).count(), 1)

    def test_no_show_status_creates_the_requested_message(self):
        appointment = self.create_appointment()
        self.client.force_authenticate(user=self.staff)

        response = self.client.patch(
            f'{self.api_prefix}/admin/appointments/{appointment.id}/status/',
            {'status': 'no_show'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        notification = Notification.objects.get(appointment=appointment)
        self.assertEqual(
            notification.message,
            'You missed your visit with Dr Ada Lovelace. '
            'Please book another appointment if needed.',
        )


class DoctorPortalTests(APITestCase):
    api_prefix = '/api'

    def setUp(self):
        self.doctor_user = User.objects.create_user(username='doctor', password='strong-password')
        Profile.objects.create(user=self.doctor_user, role='doctor', is_approved=True)
        self.doctor = Doctor.objects.create(
            user=self.doctor_user,
            name='Ada Lovelace',
            specialty='General',
        )
        self.patient = User.objects.create_user(username='patient', password='strong-password')
        Profile.objects.create(user=self.patient, role='patient')
        self.slot = Slot.objects.create(
            doctor=self.doctor,
            date=timezone.localdate(),
            start_time='10:00',
        )

    def test_doctor_can_see_bookings_free_slots_and_completed_dashboard(self):
        self.client.force_authenticate(user=self.patient)
        booking_response = self.client.post(
            f'{self.api_prefix}/appointments/book/',
            {'slot_id': self.slot.id},
            format='json',
        )
        self.assertEqual(booking_response.status_code, status.HTTP_201_CREATED)
        appointment = Appointment.objects.get(id=booking_response.data['id'])
        doctor_notification = Notification.objects.get(appointment=appointment, user=self.doctor_user)
        self.assertIn('A patient booked your appointment', doctor_notification.message)

        free_slot = Slot.objects.create(
            doctor=self.doctor,
            date=timezone.localdate(),
            start_time='11:00',
        )
        self.client.force_authenticate(user=self.doctor_user)
        scheduled_response = self.client.get(f'{self.api_prefix}/doctor/appointments/')
        free_slots_response = self.client.get(f'{self.api_prefix}/doctor/free-slots/')
        self.assertEqual([item['id'] for item in scheduled_response.data], [appointment.id])
        self.assertEqual([item['id'] for item in free_slots_response.data], [free_slot.id])

        appointment.status = 'completed'
        appointment.save(update_fields=['status'])
        diagnosis_response = self.client.patch(
            f'{self.api_prefix}/doctor/appointments/{appointment.id}/diagnosis/',
            {'diagnosis': 'Routine follow-up complete.'},
            format='json',
        )
        dashboard_response = self.client.get(f'{self.api_prefix}/doctor/dashboard/')
        self.assertEqual(diagnosis_response.status_code, status.HTTP_200_OK)
        self.assertEqual(dashboard_response.data[0]['diagnosis'], 'Routine follow-up complete.')

    def test_patient_can_rate_only_their_completed_appointment_once(self):
        appointment = Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            date=timezone.localdate(),
            ticket_number=1,
            status='completed',
        )
        self.client.force_authenticate(user=self.patient)

        response = self.client.post(
            f'{self.api_prefix}/appointments/{appointment.id}/rating/',
            {'rating': 5, 'comment': 'Excellent care.'},
            format='json',
        )
        duplicate_response = self.client.post(
            f'{self.api_prefix}/appointments/{appointment.id}/rating/',
            {'rating': 4},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ServiceRating.objects.get(appointment=appointment).rating, 5)
        self.assertEqual(duplicate_response.status_code, status.HTTP_400_BAD_REQUEST)


class WalkInAndTreatmentTests(APITestCase):
    api_prefix = '/api'

    def setUp(self):
        self.staff = User.objects.create_user(username='staff', password='strong-password')
        Profile.objects.create(user=self.staff, role='staff', is_approved=True)
        self.doctor_user = User.objects.create_user(username='doctor', password='strong-password')
        Profile.objects.create(user=self.doctor_user, role='doctor', is_approved=True)
        self.doctor = Doctor.objects.create(
            user=self.doctor_user,
            name='Grace Hopper',
            specialty='General',
        )
        self.patient = User.objects.create_user(username='walk-in-patient', password='strong-password')
        Profile.objects.create(user=self.patient, role='patient')

    def test_staff_can_check_in_a_walk_in_and_doctor_can_record_treatment(self):
        self.client.force_authenticate(user=self.staff)
        check_in_response = self.client.post(
            f'{self.api_prefix}/admin/walk-ins/',
            {'username': self.patient.username, 'doctor_id': self.doctor.id},
            format='json',
        )

        self.assertEqual(check_in_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(check_in_response.data['source'], 'walk_in')
        self.assertEqual(check_in_response.data['ticket_number'], 1)

        appointment_id = check_in_response.data['id']
        self.client.force_authenticate(user=self.doctor_user)
        treatment_response = self.client.patch(
            f'{self.api_prefix}/doctor/appointments/{appointment_id}/treatment/',
            {'diagnosis': 'Seasonal allergy', 'treatment': 'Prescribed antihistamine.'},
            format='json',
        )

        self.assertEqual(treatment_response.status_code, status.HTTP_200_OK)
        self.assertEqual(treatment_response.data['status'], 'completed')
        self.assertEqual(treatment_response.data['treatment'], 'Prescribed antihistamine.')
        self.assertIsNotNone(treatment_response.data['completed_at'])

        self.client.force_authenticate(user=self.staff)
        records_response = self.client.get(
            f'{self.api_prefix}/admin/appointments/?source=walk_in'
        )
        self.assertEqual(records_response.status_code, status.HTTP_200_OK)
        self.assertEqual(records_response.data[0]['id'], appointment_id)
        self.assertEqual(records_response.data[0]['treatment'], 'Prescribed antihistamine.')

    def test_staff_can_check_in_existing_patient_by_username(self):
        self.client.force_authenticate(user=self.staff)
        response = self.client.post(
            f'{self.api_prefix}/admin/walk-ins/',
            {'username': self.patient.username, 'doctor_id': self.doctor.id},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['source'], 'walk_in')
        self.assertEqual(response.data['patient'], self.patient.id)

    def test_staff_can_create_new_patient_for_walk_in_by_username(self):
        self.client.force_authenticate(user=self.staff)
        response = self.client.post(
            f'{self.api_prefix}/admin/walk-ins/',
            {'username': 'new_walk_in', 'doctor_id': self.doctor.id, 'phone': '0700123456'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['source'], 'walk_in')
        self.assertEqual(response.data['doctor'], self.doctor.id)

        # New user should be created as patient
        new_user = User.objects.get(username='new_walk_in')
        self.assertEqual(new_user.profile.role, 'patient')
        self.assertEqual(new_user.profile.phone, '0700123456')


class DoctorSpecialtyTests(APITestCase):
    api_prefix = '/api'

    def setUp(self):
        self.patient = User.objects.create_user(username='patient', password='strong-password')
        Profile.objects.create(user=self.patient, role='patient')
        self.dentist = Doctor.objects.create(name='Dentist', specialty='Dentistry')
        self.general = Doctor.objects.create(name='General Doctor', specialty='General Practice')
        Slot.objects.create(doctor=self.dentist, date=timezone.localdate(), start_time='09:00')
        Slot.objects.create(doctor=self.general, date=timezone.localdate(), start_time='10:00')

    def test_patient_can_list_specialties_and_filter_doctors_by_specialty(self):
        self.client.force_authenticate(user=self.patient)

        specialties_response = self.client.get(f'{self.api_prefix}/doctors/specialties/')
        doctors_response = self.client.get(
            f'{self.api_prefix}/doctors/?specialty=Dentistry'
        )

        self.assertEqual(specialties_response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [item['specialty'] for item in specialties_response.data],
            ['Dentistry', 'General Practice'],
        )
        self.assertEqual(doctors_response.status_code, status.HTTP_200_OK)
        self.assertEqual([item['name'] for item in doctors_response.data], ['Dentist'])
