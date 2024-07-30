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

#Extract the required secrets to their respective ENV variables

POSTGRES_SECRET_FILE="/run/secrets/${DOCKER_SECRET_POSTGRES_PASS:?}"
export SQL_PASSWORD="$(cat ${POSTGRES_SECRET_FILE})"
SU_SECRET_FILE="/run/secrets/${DOCKER_SECRET_SU_PASS:?}"
export SU_PASSWORD="$(cat ${SU_SECRET_FILE})"

# Execute the migration scripts on the designated database
python manage.py migrate
