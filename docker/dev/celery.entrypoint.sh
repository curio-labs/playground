#!/bin/bash
set -e

# Start Celery worker
celery -A config worker --loglevel=info