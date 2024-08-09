#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset

python /app/manage.py collectstatic --noinput
/usr/local/bin/gunicorn -c /app/docker/dev/gunicorn.conf.py config.asgi:application
