# CliniQ Backend

Django + DRF backend for CliniQ appointment/queue system.

## Setup
1. `python -m venv venv && source venv/bin/activate`
2. `pip install -r requirements.txt`
3. Create `.env` with `SECRET_KEY`, `DEBUG`, `DATABASE_URL`
4. `python manage.py migrate`
5. `python manage.py runserver`
