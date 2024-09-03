#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset

python /app/manage.py collectstatic --noinput
python /app/manage.py migrate --noinput
/usr/local/bin/gunicorn -c /app/docker/prod/gunicorn.py config.asgi:application
