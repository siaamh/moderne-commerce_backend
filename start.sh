#!/bin/sh
set -e

python manage.py migrate --noinput

# Creates the admin on first run; does nothing if it already exists
python manage.py createsuperuser --noinput || true

exec gunicorn config.wsgi:application \
    --bind 0.0.0.0:${PORT:-8000} \
    --workers 1 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
