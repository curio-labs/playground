#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset


python /app/manage.py collectstatic --noinput
python /app/manage.py migrate
# note: the auto-reloading on runserver_plus isn't as good - the container crashes after an error
python /app/manage.py runserver 0.0.0.0:8000
