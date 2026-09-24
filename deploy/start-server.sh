#!/usr/bin/env bash

# Create log directory if LOG_DIR is set
if [ -n "$LOG_DIR" ]; then
    mkdir -p "$LOG_DIR"
    chown www-data:www-data "$LOG_DIR"
fi

if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ] ; then
    (python /usr/src/backend/manage.py createsuperuser --no-input)
fi

yes yes|python /usr/src/backend/manage.py collectstatic

cp -r /usr/src/backend/staticfiles/* /srv/data/static/ 2>/dev/null || true

python /usr/src/backend/manage.py migrate

# Start Django backend
gunicorn config.wsgi --pythonpath /usr/src/backend --user www-data --bind 0.0.0.0:8010 --workers 3 --timeout 240 &

# Start TanStack Start SSR server
cd /usr/src/frontend && node .output/server/index.mjs & 

nginx -g "daemon off;"

