#!/bin/bash

# Execute the migration scripts on the designated database
python manage.py migrate

# Collect all static Django resources into one place where nginx can access them
python manage.py collectstatic --no-input

# Run the commands passed in from elsewhere
exec "$@"
