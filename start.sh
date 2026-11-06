#!/bin/sh
set -e

python manage.py migrate --noinput

python manage.py shell < create_admin.py

exec gunicorn config.wsgi:application \
    --bind 0.0.0.0:${PORT:-8000} \
    --workers 1 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
