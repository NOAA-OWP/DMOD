#!/bin/bash

export PYTHONUNBUFFERED=1
#export PYTHONASYNCIODEBUG=1

# check the database is ready before starting app
if [ "$DATABASE" = "postgres" ]
then
    echo "Waiting for postgres service..."
    while ! nc -z $SQL_HOST $SQL_PORT; do
        sleep 0.1
    done
fi
echo "Starting dmod app"

#########
# These lines will wipe and restablish the database tables
# Not good in production if you want to presist data!
# You can always run these adhoc to initialize the DB
# docker-compose exec app_server python manage.py flush --no-input
# or docker exec <stack>_app_server python manage.py flush --no-input
########
#python manage.py flush --no-input
#python manage.py migrate

# Execute the migration scripts on the designated database
#python manage.py migrate

#Extract the DB secrets into correct ENV variables
POSTGRES_SECRET_FILE="/run/secrets/${DOCKER_SECRET_POSTGRES_PASS:?}"
export SQL_PASSWORD="$(cat ${POSTGRES_SECRET_FILE})"

# Collect all static Django resources into one place where the web server can access them
python manage.py collectstatic --no-input

# Run the commands passed in from elsewhere
#exec "$@"
gunicorn maas_experiment.wsgi:application --bind 0.0.0.0:8000 --access-logfile '-' --error-logfile '-'
