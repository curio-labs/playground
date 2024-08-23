#!/bin/bash
set -e

celery -A config worker --loglevel=info
celery -A config beat --loglevel=info