#!/bin/sh
set -e

python manage.py migrate --noinput
python manage.py seed_worldcup2022

if [ -n "$DJANGO_SUPERUSER_USERNAME" ]; then
    python manage.py createsuperuser --noinput || echo "Superusuario ja existe ou nao pode ser criado; seguindo."
fi

exec gunicorn setup.wsgi --bind 0.0.0.0:${PORT:-8000}
