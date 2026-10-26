#!/bin/sh
set -e

python manage.py migrate --noinput
python manage.py seed_worldcup2022

if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
    if python manage.py shell -c "import os,sys; from django.contrib.auth import get_user_model; sys.exit(0 if get_user_model().objects.filter(username=os.environ['DJANGO_SUPERUSER_USERNAME']).exists() else 1)"; then
        echo "Superusuario '$DJANGO_SUPERUSER_USERNAME' ja existe; nada a fazer."
    else
        python manage.py createsuperuser --noinput
    fi
elif [ -n "$DJANGO_SUPERUSER_USERNAME" ] || [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
    echo "AVISO: defina DJANGO_SUPERUSER_USERNAME e DJANGO_SUPERUSER_PASSWORD juntos; superusuario nao criado."
fi

exec gunicorn setup.wsgi --bind 0.0.0.0:${PORT:-8000}
