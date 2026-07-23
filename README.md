# CliniQ Backend

Django + DRF backend for CliniQ appointment/queue system.

## Staff approval

Public registration only accepts `patient` and `staff`. Patients are approved
immediately; staff registrations remain pending until a `super_admin` reviews
them. `super_admin` profiles must be created through Django admin or another
trusted server-side process, never through `/auth/register/`.

`PATCH /auth/admin-requests/<user_id>/` with `{"is_approved": false}` records
a durable `rejected` status. Rejected accounts are not returned by the pending
requests list and cannot access staff endpoints. A super admin can later approve
the same account with `{"is_approved": true}`.

Migration `0005_profile_approval` deliberately treats existing staff accounts
as pending/unapproved and existing patients as approved. This avoids granting
staff administration rights during the upgrade without an explicit review.

## Notifications

Appointment status actions create patient notifications. Authenticated patients
can list only their own notifications at `GET /api/notifications/`, fetch an
unread badge count at `GET /api/notifications/unread-count/`, and mark one as
read with `PATCH /api/notifications/<notification_id>/read/`. All endpoints
require a JWT access token.
