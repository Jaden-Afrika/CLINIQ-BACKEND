from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import time
from core.models import Doctor, Slot, Profile


class Command(BaseCommand):
    help = "Seed demo doctors, slots, and a staff account for CliniQ"

    def handle(self, *args, **options):
        today = timezone.localdate()

        doctors_data = [
            {"name": "Dr. Amara Okafor", "specialty": "General Practice"},
            {"name": "Dr. Wanjiru Kamau", "specialty": "Pediatrics"},
            {"name": "Dr. Otieno Ochieng", "specialty": "Dentistry"},
        ]

        doctors = []
        for data in doctors_data:
            doctor, created = Doctor.objects.get_or_create(
                name=data["name"], defaults={"specialty": data["specialty"]}
            )
            doctors.append(doctor)
            if created:
                self.stdout.write(f"Created doctor: {doctor.name}")

        start_hour = 9
        for doctor in doctors:
            for i in range(6):
                slot_time = time(hour=start_hour + i)
                Slot.objects.get_or_create(
                    doctor=doctor, date=today, start_time=slot_time,
                    defaults={"is_booked": False}
                )
        self.stdout.write(f"Seeded slots for {len(doctors)} doctors on {today}")

        if not User.objects.filter(username="admin_staff").exists():
            staff_user = User.objects.create_user(
                username="admin_staff", password="staffpass123"
            )
            Profile.objects.create(user=staff_user, role="staff", phone="")
            self.stdout.write("Created staff account: admin_staff / staffpass123")
        else:
            self.stdout.write("Staff account admin_staff already exists")

        self.stdout.write(self.style.SUCCESS("Demo data seeded successfully."))