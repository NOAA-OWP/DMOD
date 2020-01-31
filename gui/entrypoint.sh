#!/bin/bash

export PYTHONUNBUFFERED=1
# Execute the migration scripts on the designated database
python manage.py migrate

# Collect all static Django resources into one place where the web server can access them
python manage.py collectstatic --no-input

# Run the commands passed in from elsewhere
#exec "$@"
gunicorn maas_experiment.wsgi:application --bind 0.0.0.0:8000 --access-logfile '-' --error-logfile '-'
