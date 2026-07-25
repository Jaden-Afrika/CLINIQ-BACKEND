from django.contrib.auth.models import User
from core.models import Doctor, Profile


def _normalize_username(name):
    base = name.strip().lower()
    base = base.replace('.', '')
    base = base.replace(' ', '_')
    base = ''.join(ch for ch in base if ch.isalnum() or ch == '_')
    return base or 'doctor'

pools = {
    'Dentist': [
        'Dr. Alice Mwangi',
        'Dr. Brian Otieno',
        'Dr. Catherine Njoroge',
        'Dr. Daniel Kariuki',
    ],
    'Dentistry': [
        'Dr. Alice Mwangi',
        'Dr. Brian Otieno',
        'Dr. Catherine Njoroge',
        'Dr. Daniel Kariuki',
    ],
    'Pediatrics': [
        'Dr. Esther Kimani',
        'Dr. Frederick Omondi',
        'Dr. Grace Wanjiru',
        'Dr. Henry Kiplagat',
    ],
    'General Medicine': [
        'Dr. Irene Kilonzo',
        'Dr. John Mworia',
        'Dr. Kevin Ouma',
        'Dr. Linda Mutiso',
    ],
    'Physical Therapy': [
        'Dr. Mary Waweru',
        'Dr. Nicholas Karani',
        'Dr. Olivia Njeri',
        'Dr. Paul Mwende',
    ],
    'Cardiology': [
        'Dr. Quentin Njuguna',
        'Dr. Rebecca Otieno',
        'Dr. Samuel Karanja',
        'Dr. Teresa Naliaka',
    ],
    'Dermatology': [
        'Dr. Ursula Maina',
        'Dr. Victor Ouma',
        'Dr. Winnie Oketch',
        'Dr. Xavier Langat',
    ],
    'General Practice': [
        'Dr. Yvonne Achieng',
        'Dr. Zachary Mboya',
        'Dr. Angela Rotich',
        'Dr. Benson Cheruiyot',
    ],
    'Gynecology': [
        'Dr. Charity Njeri',
        'Dr. Dennis Ouma',
        'Dr. Eunice Anyango',
        'Dr. Francis Mwangi',
    ],
}

extras = list(Doctor.objects.filter(name__icontains='Extra').order_by('id'))
updated = []

for idx, doctor in enumerate(extras, start=1):
    pool = pools.get(doctor.specialty, [])
    if pool:
        new_name = pool.pop(0)
    else:
        new_name = f"Dr. {doctor.specialty} Name {idx}"

    old_user = doctor.user

    # Update doctor name
    doctor.name = new_name
    doctor.save(update_fields=['name'])

    # Normalize and ensure unique username
    base_username = _normalize_username(new_name)
    username = base_username
    counter = 1
    while True:
        qs = User.objects.filter(username=username)
        if old_user:
            conflict = qs.exclude(pk=old_user.pk).exists()
        else:
            conflict = qs.exists()
        if not conflict:
            break
        username = f"{base_username}_{counter}"
        counter += 1

    if old_user:
        old_user.username = username
        old_user.set_password('12345678')
        old_user.save()
        user = old_user
    else:
        user, created = User.objects.get_or_create(username=username)
        user.set_password('12345678')
        user.save()
        doctor.user = user
        doctor.save(update_fields=['user'])

    # Ensure profile
    if not Profile.objects.filter(user=user).exists():
        Profile.objects.create(user=user, role='doctor', phone='')

    updated.append((doctor.id, new_name, user.username))

print('Updated doctors:')
for did, name, uname in updated:
    print(f'{did}: {name} -> {uname}')

print('\nTotal updated:', len(updated))
