#!/bin/sh
set -e

python manage.py migrate --noinput



# Seed catalog (brands, categories, products) — idempotent, safe to run every deploy


exec gunicorn config.wsgi:application \
    --bind 0.0.0.0:${PORT:-8000} \
    --workers 1 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
