#!/bin/sh
set -e

python manage.py migrate --noinput

python manage.py shell < create_admin.py

# Seed catalog (brands, categories, products) — idempotent, safe to run every deploy
python manage.py seed_catalog

exec gunicorn config.wsgi:application \
    --bind 0.0.0.0:${PORT:-8000} \
    --workers 1 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
